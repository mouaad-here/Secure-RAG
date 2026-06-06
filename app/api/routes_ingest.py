"""
app/api/routes_ingest.py — Document ingestion and listing endpoints.

Layer: api
Imports allowed: ingestion/, storage/, retrieval/, config
"""
from __future__ import annotations

from typing import List, Optional

import structlog
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, Path
from pydantic import BaseModel

from app.config import get_settings
from app.exceptions import DocumentLoadError, UnsupportedFileTypeError
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

@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest a document into the secure RAG system",
    description=(
        "Upload a document (PDF, Markdown, or Plain Text) for ingestion into the system. "
        "The pipeline will parse the text, normalize it, chunk it into appropriate segments, "
        "and pass each chunk through the `SecurityScanner`.\n\n"
        "**Security Rules:**\n"
        "- Documents are scored from `0.0` (malicious) to `1.0` (clean).\n"
        "- If the `trust_score` meets the threshold (default `0.7`), the document is marked as `trusted` and embedded into the primary collection.\n"
        "- If the `trust_score` falls below the threshold, the document is marked as `quarantine` and stored in a separate collection. It will **never** be used for query generation."
    ),
    responses={
        200: {"description": "Document ingested successfully and routed based on trust score."},
        400: {"description": "Unsupported file type."},
        422: {"description": "Document parsing or loading failed."},
        500: {"description": "Storage or database error."},
    }
)
async def ingest_document(
    file: UploadFile = File(..., description="Document file (must be PDF, MD, or TXT)"),
    source_label: Optional[str] = Query(default=None, description="Optional organizational label for this document"),
    naive: bool = Query(default=False, description="Whether to bypass security scanning and DLP (Naive Mode)"),
) -> IngestResponse:
    """
    Upload and process a document through the ingestion pipeline.
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

    if naive:
        # --- Naive Mode Bypass ---
        # Modify source label to indicate naive mode
        metadata.source_label = "naive" if not source_label else f"naive-{source_label}"
        metadata.trust_score = 1.0
        metadata.trust_status = "trusted"
        metadata.scan_flags = ["NAIVE_MODE_BYPASS"]

        # Log bypass in Audit log
        from app.security.audit import AuditLogger
        AuditLogger().log_scan_event(
            doc_id=metadata.doc_id,
            filename=metadata.filename,
            trust_score=1.0,
            flags=["NAIVE_MODE_BYPASS"],
            details=["Document ingested in Naive Mode. Security Scanner and DLP bypassed."],
            action_taken="trusted"
        )
    else:
        # --- Step 4.2: Data Loss Prevention (DLP) Redaction ---
        from app.security.dlp_scanner import PIIScanner
        pii_scanner = PIIScanner()
        
        dlp_flags = set()
        for chunk in chunks:
            dlp_result = pii_scanner.redact(chunk.content)
            if dlp_result.is_sensitive:
                chunk.content = dlp_result.redacted_text
                dlp_flags.update(dlp_result.flags)

        # --- Step 4.5: Phase 3 — Security Scan ---
        from app.security.scanner import SecurityScanner
        from app.security.audit import AuditLogger
        
        scanner = SecurityScanner(enable_ai=True)
        scan_results = scanner.scan_chunks([c.content for c in chunks])
        
        # Calculate overall trust score (minimum is safest)
        min_score = min([res.trust_score for res in scan_results]) if scan_results else 1.0
        all_flags = list(set(flag for res in scan_results for flag in res.flags))
        all_details = [detail for res in scan_results for detail in res.details]
        
        # Add DLP flags
        if dlp_flags:
            all_flags.extend(list(dlp_flags))
            all_details.append(f"DLP: Redacted sensitive patterns: {list(dlp_flags)}")
            
        trust_status = "trusted" if min_score >= settings.trust_threshold else "quarantine"
        metadata.trust_score = min_score
        metadata.trust_status = trust_status
        metadata.scan_flags = all_flags

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
    _try_embed_and_store(metadata, chunks, settings, naive=naive)

    # --- Step 6: Persist metadata to SQLite ---
    try:
        store = SQLiteStore()
        store.save_document(metadata)
        store.log_event(
            event_type="ingest_complete",
            details=f"doc_id={metadata.doc_id} chunks={metadata.chunk_count} status={metadata.trust_status} naive={naive}",
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
        naive=naive,
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


def _try_embed_and_store(metadata: DocumentMetadata, chunks: list, settings, naive: bool = False) -> None:
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
                "mode": "naive" if naive else "secure",
            }
            for c in chunks
        ]

        # Route to appropriate store based on trust status
        if metadata.trust_status == "trusted":
            trusted_store = TrustedStore()
            trusted_store.add_chunks(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            logger.info("chunks_embedded_trusted", doc_id=metadata.doc_id, count=len(chunks), mode="naive" if naive else "secure")
        else:
            from app.storage.chroma_quarantine import QuarantineStore
            quarantine_store = QuarantineStore()
            quarantine_store.add_chunks(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            logger.info("chunks_embedded_quarantine", doc_id=metadata.doc_id, count=len(chunks))

    except Exception as exc:
        # Ollama not running — graceful degradation
        if metadata.trust_status == "trusted":
            metadata.trust_status = "pending"
        logger.warning("embedding_skipped", doc_id=metadata.doc_id, reason=str(exc))


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List all ingested documents",
    description=(
        "Retrieve a summary list of all documents that have been ingested into the system. "
        "You can filter the list by `trust_status` to view only `trusted` or `quarantine` documents."
    ),
    responses={
        200: {"description": "List of documents returned successfully."},
        500: {"description": "Database query failed."},
    }
)
async def list_documents(
    trust_status: Optional[str] = Query(default=None, description="Filter documents by status: `trusted`, `quarantine`, or `pending`"),
) -> DocumentListResponse:
    """List all ingested documents with their metadata and trust status."""
    try:
        store = SQLiteStore()
        records = store.list_documents(trust_status=trust_status)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "storage_failed", "message": str(exc)})

    summaries = [_build_summary(r) for r in records]
    return DocumentListResponse(documents=summaries, total=len(summaries))


@router.get(
    "/documents/{doc_id}",
    response_model=DocumentSummary,
    summary="Get document details by ID",
    description="Retrieve the detailed metadata for a specific document by its unique UUID.",
    responses={
        200: {"description": "Document details returned successfully."},
        404: {"description": "Document ID not found."},
        500: {"description": "Database query failed."},
    }
)
async def get_document(
    doc_id: str = Path(..., description="The UUID of the document to retrieve")
) -> DocumentSummary:
    """Retrieve a single document record by its ID."""
    try:
        store = SQLiteStore()
        record = store.get_document(doc_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "storage_failed", "message": str(exc)})

    if record is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "doc_id": doc_id})

    return _build_summary(record)


@router.get(
    "/audit-logs",
    response_model=AuditLogResponse,
    summary="Get security scan audit logs",
    description=(
        "Retrieve the most recent security scan audit logs. "
        "These logs include details on trust scores, flagged patterns, and the actions taken "
        "by the Security Scanner during the ingestion pipeline."
    ),
    responses={
        200: {"description": "Audit logs returned successfully."},
        500: {"description": "Failed to read the log file on disk."},
    }
)
async def get_audit_logs(
    limit: int = Query(50, description="Maximum number of recent logs to return (max 1000)"),
) -> AuditLogResponse:
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
