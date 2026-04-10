"""
Secure RAG MVP — Query API Routes
Handles question answering with retrieval-augmented generation.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, List

router = APIRouter()


class QueryRequest(BaseModel):
    """Request schema for asking a question."""
    question: str = Field(..., min_length=3, max_length=1000, description="The question to ask")
    top_k: Optional[int] = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    include_quarantine: bool = Field(default=False, description="Include quarantine results (for testing)")


class CitationSource(BaseModel):
    """A single citation source."""
    document: str
    chunk_id: str
    relevance_score: float
    trust_level: str  # "trusted" or "quarantine"


class QueryResponse(BaseModel):
    """Response schema for a RAG query."""
    answer: str
    citations: List[CitationSource]
    security_flags: List[str]
    model_used: str
    context_chunks_used: int


@router.post("/ask", response_model=QueryResponse, summary="Ask a question")
async def ask_question(request: QueryRequest):
    """
    Ask a question using the RAG pipeline:
    1. Validate & sanitize query
    2. Generate query embedding
    3. Retrieve top-k chunks (trusted collection only by default)
    4. Apply trust & risk filters
    5. Build prompt with strict template
    6. Call Ollama LLM
    7. Build citations
    8. Run output firewall
    9. Return sanitized answer with citations
    """
    # TODO: Phase 2 — Wire up full RAG pipeline

    return QueryResponse(
        answer="RAG pipeline not yet connected. Coming in Phase 2.",
        citations=[],
        security_flags=[],
        model_used="llama3.2:3b",
        context_chunks_used=0,
    )
