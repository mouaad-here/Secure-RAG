"""
app/api/routes_query.py — RAG query endpoint with full security pipeline.

Layer: api
Imports allowed: retrieval/, generation/, security/, config

Security pipeline (Phase 5):
  1. Input scan — SecurityScanner checks user question for injection attacks
  2. Retrieval — top-k chunks from trusted collection
  3. Prompt build + LLM call
  4. Output firewall — OutputFirewall scans LLM response
  5. Policy engine — PolicyEngine makes final ALLOW/WARN/SANITIZE/BLOCK decision
"""
from __future__ import annotations

import hashlib
from typing import List, Optional

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.security.scanner import SecurityScanner
from app.security.output_firewall import OutputFirewall
from app.security.policy import PolicyEngine, PolicyAction
from app.retrieval.retriever import Retriever
from app.generation.prompt_builder import PromptBuilder
from app.generation.ollama_client import OllamaClient
from app.generation.citations import CitationBuilder

logger = structlog.get_logger(__name__)
router = APIRouter()

# Generic refusal message — never leak why a query was blocked
_BLOCKED_RESPONSE = (
    "I'm unable to process this request. The query was flagged by "
    "the security system. Please rephrase your question using "
    "natural language without special instructions."
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Request schema for asking a question."""
    question: str = Field(
        ..., min_length=3, max_length=1000,
        description="The natural-language question to ask against the document corpus.",
    )
    top_k: Optional[int] = Field(
        default=5, ge=1, le=20,
        description="Number of context chunks to retrieve.",
    )
    include_quarantine: bool = Field(
        default=False,
        description="Include quarantine results (red-team testing only).",
    )
    naive: bool = Field(
        default=False,
        description="Whether to query in Naive mode (bypasses security scans and filters).",
    )


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

@router.post(
    "/ask",
    response_model=QueryResponse,
    summary="Ask a question against the secure document corpus",
    description=(
        "Submit a natural-language question. The pipeline retrieves relevant "
        "chunks from the trusted collection, generates an answer via the local "
        "LLM (Ollama), and passes the output through the security firewall "
        "before returning. Queries containing injection patterns are rejected "
        "with HTTP 403."
    ),
    responses={
        403: {"description": "Query rejected — injection attack detected"},
        503: {"description": "Upstream service unavailable (Ollama / ChromaDB)"},
    },
)
async def ask_question(request: QueryRequest) -> QueryResponse:
    """
    Full RAG pipeline with defense-in-depth security.

    Flow:
        input scan → retrieve → prompt → LLM → citations →
        output firewall → policy engine → response
    """
    settings = get_settings()
    query_hash = hashlib.sha256(request.question.encode()).hexdigest()

    # ------------------------------------------------------------------
    # PHASE 5 — Step 0: Input security scan (query injection detection)
    # ------------------------------------------------------------------
    if not request.naive:
        scanner = SecurityScanner()
        input_scan = scanner.scan(request.question)

        if input_scan.trust_score < settings.trust_threshold:
            logger.warning(
                "query_blocked_input",
                query_hash=query_hash,
                trust_score=input_scan.trust_score,
                flags=input_scan.flags,
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "query_rejected",
                    "message": (
                        "Your query was flagged as a potential injection attack "
                        "and has been blocked."
                    ),
                    "security_flags": input_scan.flags,
                },
            )
    else:
        # Dummy scan result for naive mode
        from app.security.scanner import ScanResult
        input_scan = ScanResult(trust_score=1.0, flags=["NAIVE_MODE_BYPASS"], details=[])

    # ------------------------------------------------------------------
    # Step 1: Retrieve relevant chunks
    # ------------------------------------------------------------------
    try:
        retriever = Retriever()
        chunks = retriever.retrieve(
            query=request.question,
            top_k=request.top_k,
            include_quarantine=request.include_quarantine,
            mode="naive" if request.naive else "secure",
        )
    except Exception as exc:
        logger.error("retrieval_failed", question_len=len(request.question), error=str(exc))
        raise HTTPException(
            status_code=503,
            detail={"error": "retrieval_failed", "message": str(exc)},
        )

    # ------------------------------------------------------------------
    # Step 2 & 3: Build prompt (with or without context)
    # ------------------------------------------------------------------
    try:
        if request.naive:
            # Simple weak system prompt for naive RAG comparison
            naive_sys = "You are a helpful assistant. Answer the user's question based on the provided context."
            builder = PromptBuilder(system_prompt=naive_sys)
            if not chunks:
                prompt = f"Answer the user's query: {request.question}"
            else:
                prompt = builder.build(request.question, chunks)
        else:
            builder = PromptBuilder()
            if not chunks:
                prompt = builder.build_without_context(request.question)
            else:
                prompt = builder.build(request.question, chunks)
    except Exception as exc:
        logger.error("prompt_build_failed", error=str(exc))
        raise HTTPException(status_code=500, detail={"error": "prompt_failed", "message": str(exc)})

    # ------------------------------------------------------------------
    # Step 4: Call Ollama
    # ------------------------------------------------------------------
    try:
        answer = OllamaClient().generate(prompt)
    except Exception as exc:
        logger.error("llm_failed", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail={"error": "llm_unavailable", "message": "Ollama is not responding. Is the container running?"},
        )

    # ------------------------------------------------------------------
    # Step 5: Build citations
    # ------------------------------------------------------------------
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

    # If naive mode, bypass Output Firewall and Policy Engine completely
    if request.naive:
        logger.info(
            "query_answered_naive",
            query_hash=query_hash,
            chunks_used=len(chunks),
            citations=len(citations),
            model=settings.llm_model,
            security_flags=["NAIVE_MODE_BYPASS"],
        )
        return QueryResponse(
            answer=answer,
            citations=citations,
            security_flags=["NAIVE_MODE_BYPASS"],
            model_used=settings.llm_model,
            context_chunks_used=len(chunks),
        )

    # ------------------------------------------------------------------
    # PHASE 5 — Step 6: Output firewall scan
    # ------------------------------------------------------------------
    context_texts = [c.content for c in chunks] if chunks else None
    firewall = OutputFirewall()
    firewall_result = firewall.scan(answer, context_chunks=context_texts)

    # ------------------------------------------------------------------
    # PHASE 5 — Step 7: Policy engine decision on output
    # ------------------------------------------------------------------
    policy_engine = PolicyEngine()
    policy_decision = policy_engine.evaluate_output(firewall_result.flags)

    # Collect all security flags from both input scan and output firewall
    all_security_flags = list(set(input_scan.flags + firewall_result.flags))

    if policy_decision.action == PolicyAction.BLOCK:
        logger.warning(
            "query_blocked_output",
            query_hash=query_hash,
            flags=firewall_result.flags,
            policy="BLOCK",
            risk_level=policy_decision.risk_level,
        )
        return QueryResponse(
            answer=_BLOCKED_RESPONSE,
            citations=[],
            security_flags=all_security_flags,
            model_used=settings.llm_model,
            context_chunks_used=len(chunks),
        )

    # SANITIZE: use the firewall's sanitized response (URLs stripped, etc.)
    if policy_decision.action == PolicyAction.SANITIZE:
        final_answer = firewall_result.sanitized_response
        logger.info(
            "query_sanitized",
            query_hash=query_hash,
            flags=firewall_result.flags,
            policy="SANITIZE",
        )
    else:
        final_answer = answer

    # WARN: log but still return the answer
    if policy_decision.action == PolicyAction.WARN:
        logger.info(
            "query_warned",
            query_hash=query_hash,
            flags=firewall_result.flags,
            policy="WARN",
            risk_level=policy_decision.risk_level,
        )

    logger.info(
        "query_answered",
        query_hash=query_hash,
        chunks_used=len(chunks),
        citations=len(citations),
        model=settings.llm_model,
        policy=policy_decision.action.value,
        security_flags=all_security_flags,
    )

    return QueryResponse(
        answer=final_answer,
        citations=citations,
        security_flags=all_security_flags,
        model_used=settings.llm_model,
        context_chunks_used=len(chunks),
    )


@router.post(
    "/ask/stream",
    summary="Ask a question and stream the response",
    description=(
        "Submit a natural-language question. The pipeline retrieves relevant "
        "chunks, generates an answer via the local LLM (Ollama) in a stream, "
        "and filters the output dynamically using the security firewall. "
        "Results are returned as Server-Sent Events (SSE)."
    ),
)
async def ask_question_stream(request: QueryRequest) -> StreamingResponse:
    """
    RAG query endpoint with streaming response and dynamic security checks.
    """
    from fastapi.responses import StreamingResponse
    import json
    import hashlib
    import re

    async def event_generator():
        settings = get_settings()
        query_hash = hashlib.sha256(request.question.encode()).hexdigest()

        # 1. Input Scan
        if not request.naive:
            scanner = SecurityScanner()
            input_scan = scanner.scan(request.question)
            if input_scan.trust_score < settings.trust_threshold:
                logger.warning("query_blocked_input", query_hash=query_hash, flags=input_scan.flags)
                yield "event: error\ndata: " + json.dumps({
                    "error": "query_rejected",
                    "message": "Your query was flagged as a potential injection attack and has been blocked.",
                    "security_flags": input_scan.flags
                }) + "\n\n"
                return
        else:
            from app.security.scanner import ScanResult
            input_scan = ScanResult(trust_score=1.0, flags=["NAIVE_MODE_BYPASS"], details=[])

        # 2. Retrieve Chunks
        try:
            retriever = Retriever()
            chunks = retriever.retrieve(
                query=request.question,
                top_k=request.top_k,
                include_quarantine=request.include_quarantine,
                mode="naive" if request.naive else "secure",
            )
        except Exception as exc:
            yield "event: error\ndata: " + json.dumps({"error": "retrieval_failed", "message": str(exc)}) + "\n\n"
            return

        # 3. Build Prompt
        if request.naive:
            naive_sys = "You are a helpful assistant. Answer the user's question based on the provided context."
            builder = PromptBuilder(system_prompt=naive_sys)
            prompt = builder.build(request.question, chunks) if chunks else f"Answer the user's query: {request.question}"
        else:
            builder = PromptBuilder()
            prompt = builder.build(request.question, chunks) if chunks else builder.build_without_context(request.question)

        # 4. Generate Stream
        try:
            client = OllamaClient()
            stream = client.generate_stream(prompt)
        except Exception as exc:
            yield "event: error\ndata: " + json.dumps({"error": "llm_unavailable", "message": str(exc)}) + "\n\n"
            return

        full_response = ""
        url_buffer = ""
        in_url = False
        firewall = OutputFirewall()

        for token in stream:
            full_response += token

            # Check prompt leak
            if not request.naive:
                leak_flags, _ = firewall._check_leaked_instructions(full_response)
                if leak_flags:
                    yield "event: blocked\ndata: " + json.dumps({
                        "message": "\n\n[RESPONSE BLOCKED BY SECURITY POLICY]\n\n",
                        "security_flags": list(set(input_scan.flags + ["LEAKED_INSTRUCTIONS"])),
                        "citations": [],
                        "context_chunks_used": len(chunks)
                    }) + "\n\n"
                    return

            # Check URLs in streaming mode
            if not request.naive:
                if not in_url:
                    match = re.search(r"https?://", token, re.I)
                    if match:
                        in_url = True
                        idx = match.start()
                        if idx > 0:
                            yield "event: delta\ndata: " + json.dumps(token[:idx]) + "\n\n"
                        url_buffer = token[idx:]
                    else:
                        yield "event: delta\ndata: " + json.dumps(token) + "\n\n"
                else:
                    url_buffer += token
                    end_match = re.search(r"\s", url_buffer)
                    if end_match:
                        in_url = False
                        split_idx = end_match.start()
                        url = url_buffer[:split_idx]
                        following = url_buffer[split_idx:]
                        _, _, sanitized_url = firewall._check_urls(url)
                        yield "event: delta\ndata: " + json.dumps(f"{sanitized_url}{following}") + "\n\n"
                        url_buffer = ""
            else:
                yield "event: delta\ndata: " + json.dumps(token) + "\n\n"

        if url_buffer:
            if not request.naive:
                _, _, sanitized_url = firewall._check_urls(url_buffer)
                yield "event: delta\ndata: " + json.dumps(sanitized_url) + "\n\n"
            else:
                yield "event: delta\ndata: " + json.dumps(url_buffer) + "\n\n"

        # Citations
        raw_citations = CitationBuilder().build_citations(full_response, chunks)
        citations = [
            {
                "document": c.source_document,
                "chunk_id": c.chunk_id,
                "relevance_score": round(c.relevance_score, 4),
                "trust_level": c.trust_level,
            }
            for c in raw_citations
        ]

        security_flags = list(input_scan.flags)
        if not request.naive:
            context_texts = [c.content for c in chunks] if chunks else None
            ground_flags, _ = firewall._check_groundedness(full_response, context_texts)
            security_flags.extend(ground_flags)

        yield "event: metadata\ndata: " + json.dumps({
            "security_flags": list(set(security_flags)),
            "citations": citations,
            "context_chunks_used": len(chunks)
        }) + "\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
