"""
app/api/routes_ingest.py — Document ingestion and listing endpoints.

Layer: api
Imports allowed: ingestion/, storage/, retrieval/, config
"""
from __future__ import annotations

from typing import List, Optional

import structlog
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.config import get_settings
from app.exceptions import DocumentLoadError, StorageError, UnsupportedFileTypeError
from app.ingestion.chunker import TextChunker
from app.ingestion.loader import DocumentLoader
from app.ingestion.metadata import DocumentMetadata, MetadataBuilder
from app.ingestion.normalizer import TextNormalizer
from app.storage.sqlite_store import SQLiteStore

logger = structlog.get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class IngestResponse(BaseModel):
    """Response returned after a successful document ingest."""
    doc_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    chunk_count: int
    trust_score: float
    trust_status: str
    source_label: str
    message: str


class DocumentSummary(BaseModel):
    """Summary of an ingested document record."""
    doc_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    chunk_count: int
    trust_score: Optional[float]
    trust_status: str
    source_label: str
    ingested_at: str


class DocumentListResponse(BaseModel):
    """List of ingested documents."""
    documents: List[DocumentSummary]
    total: int


class AuditEvent(BaseModel):
    """Single security scan audit event."""
    timestamp: float
    event_type: str
    doc_id: str
    filename: str
    trust_score: float
    flags: List[str]
    details: List[str]
    action_taken: str


class AuditLogResponse(BaseModel):
    """List of recent audit events."""
    events: List[AuditEvent]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_summary(record) -> DocumentSummary:
    """Convert a SQLAlchemy DocumentRecord to a DocumentSummary."""
    return DocumentSummary(
        doc_id=record.doc_id,
        filename=record.filename,
        file_type=record.file_type,
        file_size_bytes=record.file_size_bytes,
        chunk_count=record.chunk_count,
        trust_score=record.trust_score,
        trust_status=record.trust_status,
        source_label=record.source_label,
        ingested_at=str(record.ingested_at),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/ingest", response_model=IngestResponse, summary="Ingest a document")
async def ingest_document(
    file: UploadFile = File(..., description="Document file (PDF, MD, or TXT)"),
    source_label: Optional[str] = Query(default=None, description="Optional label for this document"),
) -> IngestResponse:
    """
    Upload and process a document through the ingestion pipeline.

    Pipeline: load → normalize → chunk → save metadata (SQLite).
    Embeddings are added in Phase 2 when Ollama is available.
    Trust score defaults to 1.0 (pending Phase 3 security scanner).
    """
    settings = get_settings()

    # --- Step 1: Load ---
    try:
        content = await file.read()
        loader = DocumentLoader()
        doc = loader.load_from_bytes(content, file.filename or "upload", source_label or "upload")
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=400, detail={"error": "unsupported_file_type", "message": str(exc)})
    except DocumentLoadError as exc:
        raise HTTPException(status_code=422, detail={"error": "document_load_failed", "message": str(exc)})

    # --- Step 2: Normalize ---
    normalizer = TextNormalizer()
    normalized_text = normalizer.normalize(doc.content)

    # --- Step 3: Build initial metadata ---
    metadata = MetadataBuilder.build(
        filename=doc.filename,
        file_type=doc.file_type,
        file_size_bytes=doc.file_size_bytes,
        source_label=doc.source_label,
        page_count=doc.page_count,
    )

    # --- Step 4: Chunk ---
    chunker = TextChunker()
    chunks = chunker.chunk(normalized_text, doc.filename)
    metadata = MetadataBuilder.update_after_chunking(metadata, len(chunks))

    # --- Step 4.5: Phase 3 — Security Scan ---
    from app.security.scanner import SecurityScanner
    from app.security.audit import AuditLogger
    
    scanner = SecurityScanner()
    scan_results = scanner.scan_chunks([c.content for c in chunks])
    
    # Calculate overall trust score (minimum is safest)
    min_score = min([res.trust_score for res in scan_results]) if scan_results else 1.0
    all_flags = list(set(flag for res in scan_results for flag in res.flags))
    all_details = [detail for res in scan_results for detail in res.details]
    
    trust_status = "trusted" if min_score >= settings.trust_threshold else "quarantine"
    metadata.trust_score = min_score
    metadata.trust_status = trust_status

    # Log to JSONL Audit Log
    AuditLogger().log_scan_event(
        doc_id=metadata.doc_id,
        filename=metadata.filename,
        trust_score=min_score,
        flags=all_flags,
        details=all_details,
        action_taken=trust_status
    )

    # --- Step 5: Phase 2 — embed + store in ChromaDB (if Ollama available) ---
    _try_embed_and_store(metadata, chunks, settings)

    # --- Step 6: Persist metadata to SQLite ---
    try:
        store = SQLiteStore()
        store.save_document(metadata)
        store.log_event(
            event_type="ingest_complete",
            details=f"doc_id={metadata.doc_id} chunks={metadata.chunk_count} status={metadata.trust_status}",
        )
    except Exception as exc:
        logger.error("sqlite_save_failed", doc_id=metadata.doc_id, error=str(exc))
        raise HTTPException(status_code=500, detail={"error": "storage_failed", "message": str(exc)})

    logger.info(
        "document_ingested",
        doc_id=metadata.doc_id,
        filename=metadata.filename,
        chunks=metadata.chunk_count,
        trust_status=metadata.trust_status,
    )

    return IngestResponse(
        doc_id=metadata.doc_id,
        filename=metadata.filename,
        file_type=metadata.file_type,
        file_size_bytes=metadata.file_size_bytes,
        chunk_count=metadata.chunk_count,
        trust_score=metadata.trust_score or 1.0,
        trust_status=metadata.trust_status,
        source_label=metadata.source_label,
        message="Document ingested successfully.",
    )


def _try_embed_and_store(metadata: DocumentMetadata, chunks: list, settings) -> None:
    """
    Attempt to embed chunks and store in ChromaDB (Phase 2 step).
    Gracefully skips if Ollama is unavailable — doc stays in SQLite only.
    """
    if not chunks:
        return
    try:
        from app.retrieval.embeddings import EmbeddingGenerator
        from app.storage.chroma_trusted import TrustedStore

        embedder = EmbeddingGenerator()
        texts = [c.content for c in chunks]
        embeddings = embedder.embed_batch(texts)

        ids = [c.chunk_id for c in chunks]
        metadatas = [
            {
                "doc_id": metadata.doc_id,
                "source_document": metadata.filename,
                "chunk_index": c.index,
                "trust_score": metadata.trust_score or 1.0,
            }
            for c in chunks
        ]

        # If quarantined, we skip adding to the TrustedStore for now
        # Phase 4 will implement the QuarantineStore.
        if metadata.trust_status == "trusted":
            trusted_store = TrustedStore()
            trusted_store.add_chunks(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            logger.info("chunks_embedded_trusted", doc_id=metadata.doc_id, count=len(chunks))
        else:
            logger.info("chunks_quarantined_skip_trusted", doc_id=metadata.doc_id, count=len(chunks))

    except Exception as exc:
        # Ollama not running — graceful degradation
        if metadata.trust_status == "trusted":
            metadata.trust_status = "pending"
        logger.warning("embedding_skipped", doc_id=metadata.doc_id, reason=str(exc))


@router.get("/documents", response_model=DocumentListResponse, summary="List ingested documents")
async def list_documents(
    trust_status: Optional[str] = Query(default=None, description="Filter: trusted | quarantine | pending"),
) -> DocumentListResponse:
    """List all ingested documents with their metadata and trust status."""
    try:
        store = SQLiteStore()
        records = store.list_documents(trust_status=trust_status)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "storage_failed", "message": str(exc)})

    summaries = [_build_summary(r) for r in records]
    return DocumentListResponse(documents=summaries, total=len(summaries))


@router.get("/documents/{doc_id}", response_model=DocumentSummary, summary="Get a document by ID")
async def get_document(doc_id: str) -> DocumentSummary:
    """Retrieve a single document record by its ID."""
    try:
        store = SQLiteStore()
        record = store.get_document(doc_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "storage_failed", "message": str(exc)})

    if record is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "doc_id": doc_id})

    return _build_summary(record)


@router.get("/audit-logs", response_model=AuditLogResponse, summary="Get security scan audit logs")
async def get_audit_logs(limit: int = Query(50, description="Max number of logs to return")) -> AuditLogResponse:
    """Retrieve the most recent security scan audit logs."""
    import json
    import os
    from app.config import get_settings
    
    settings = get_settings()
    log_file = os.path.join(settings.log_dir, "scan_audit.jsonl")
    
    events = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                # Read all lines, but we only want the most recent `limit` lines
                lines = f.readlines()
                for line in reversed(lines):
                    if not line.strip():
                        continue
                    if len(events) >= limit:
                        break
                    try:
                        data = json.loads(line)
                        events.append(AuditEvent(**data))
                    except Exception:
                        pass
        except Exception as exc:
            raise HTTPException(status_code=500, detail={"error": "log_read_failed", "message": str(exc)})
            
    return AuditLogResponse(events=events, total=len(events))
