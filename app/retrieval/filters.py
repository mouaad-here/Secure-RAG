"""
Secure RAG MVP — Retrieval Filters
Secondary layer of defense to ensure untrusted chunks never reach the LLM.
"""

from typing import List
from app.config import get_settings
from app.retrieval.retriever import RetrievedChunk

class TrustFilter:
    """
    Defense-in-depth filter for retrieved chunks.
    Even though the retriever queries the TrustedStore exclusively,
    this filter ensures no chunk with a low trust score is returned,
    protecting against database misconfigurations or manual tampering.
    """

    def __init__(self):
        self.settings = get_settings()

    def filter_chunks(self, chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        """
        Filter out any chunks that fall below the trust threshold.
        """
        safe_chunks = []
        for chunk in chunks:
            # If trust_score is missing, we assume 1.0 (safe) for backward compatibility
            # with Phase 1 chunks, though all Phase 3+ chunks will have it.
            score = chunk.metadata.get("trust_score", 1.0)
            
            if score >= self.settings.trust_threshold:
                safe_chunks.append(chunk)
                
        return safe_chunks
