"""
app/api/routes_query.py — RAG query endpoint.

Layer: api
Imports allowed: retrieval/, generation/, security/, config
"""
from __future__ import annotations

from typing import List, Optional

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Request schema for asking a question."""
    question: str = Field(..., min_length=3, max_length=1000, description="The question to ask")
    top_k: Optional[int] = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    include_quarantine: bool = Field(default=False, description="Include quarantine results (red-team testing only)")


class CitationSource(BaseModel):
    """A single citation source returned in a RAG response."""
    document: str
    chunk_id: str
    relevance_score: float
    trust_level: str


class QueryResponse(BaseModel):
    """Response schema for a RAG query."""
    answer: str
    citations: List[CitationSource]
    security_flags: List[str]
    model_used: str
    context_chunks_used: int


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/ask", response_model=QueryResponse, summary="Ask a question")
async def ask_question(request: QueryRequest) -> QueryResponse:
    """
    Ask a question using the full RAG pipeline.

    Flow: retrieve → prompt → LLM → citations → return.
    Output firewall is added in Phase 5.
    """
    settings = get_settings()

    # --- Step 1: Retrieve relevant chunks ---
    try:
        from app.retrieval.retriever import Retriever
        retriever = Retriever()
        chunks = retriever.retrieve(
            query=request.question,
            top_k=request.top_k,
            include_quarantine=request.include_quarantine,
        )
    except Exception as exc:
        logger.error("retrieval_failed", question_len=len(request.question), error=str(exc))
        raise HTTPException(
            status_code=503,
            detail={"error": "retrieval_failed", "message": str(exc)},
        )

    # --- Step 2 & 3: Build prompt (with or without context) ---
    try:
        from app.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        if not chunks:
            prompt = builder.build_without_context(request.question)
        else:
            prompt = builder.build(request.question, chunks)
    except Exception as exc:
        logger.error("prompt_build_failed", error=str(exc))
        raise HTTPException(status_code=500, detail={"error": "prompt_failed", "message": str(exc)})

    # --- Step 4: Call Ollama ---
    try:
        from app.generation.ollama_client import OllamaClient
        answer = OllamaClient().generate(prompt)
    except Exception as exc:
        logger.error("llm_failed", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail={"error": "llm_unavailable", "message": "Ollama is not responding. Is the container running?"},
        )

    # --- Step 5: Build citations ---
    from app.generation.citations import CitationBuilder
    raw_citations = CitationBuilder().build_citations(answer, chunks)

    citations = [
        CitationSource(
            document=c.source_document,
            chunk_id=c.chunk_id,
            relevance_score=round(c.relevance_score, 4),
            trust_level=c.trust_level,
        )
        for c in raw_citations
    ]

    logger.info(
        "query_answered",
        chunks_used=len(chunks),
        citations=len(citations),
        model=settings.llm_model,
    )

    return QueryResponse(
        answer=answer,
        citations=citations,
        security_flags=[],          # Phase 5: output firewall flags
        model_used=settings.llm_model,
        context_chunks_used=len(chunks),
    )
