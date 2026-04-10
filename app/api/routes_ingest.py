"""
Secure RAG MVP — Ingestion API Routes
Handles document upload, processing, and storage.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional

router = APIRouter()


@router.post("/ingest", summary="Ingest a document")
async def ingest_document(
    file: UploadFile = File(..., description="Document file (PDF, MD, TXT)"),
    source_label: Optional[str] = None,
):
    """
    Upload and process a document through the ingestion pipeline:
    1. Load & validate file type
    2. Normalize text
    3. Security scan (prompt injection detection)
    4. Chunk into segments
    5. Generate embeddings
    6. Route to trusted or quarantine collection based on trust score
    """
    # Validate file type
    allowed_types = {".pdf", ".md", ".txt"}
    file_ext = ""
    if file.filename:
        file_ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: '{file_ext}'. Allowed: {allowed_types}",
        )

    # TODO: Phase 1 — Wire up full ingestion pipeline
    # 1. loader.load(file)
    # 2. normalizer.normalize(raw_text)
    # 3. scanner.scan(normalized_text)
    # 4. chunker.chunk(normalized_text)
    # 5. embeddings.embed(chunks)
    # 6. Route to trusted/quarantine based on scan results

    content = await file.read()
    file_size = len(content)

    return {
        "status": "accepted",
        "filename": file.filename,
        "file_size_bytes": file_size,
        "file_type": file_ext,
        "source_label": source_label or "unknown",
        "message": "Document accepted. Full pipeline coming in Phase 1.",
    }


@router.get("/documents", summary="List ingested documents")
async def list_documents():
    """List all ingested documents with their metadata and trust status."""
    # TODO: Phase 1 — Query SQLite for document records
    return {
        "documents": [],
        "total": 0,
        "message": "Document listing coming in Phase 1.",
    }
