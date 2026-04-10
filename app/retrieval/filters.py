"""
Secure RAG MVP — Retrieval Filters
Trust and risk filters applied to retrieved chunks before generation.
"""

from typing import List

from app.retrieval.retriever import RetrievedChunk
from app.config import get_settings


class RetrievalFilters:
    """
    Apply post-retrieval filtering to ensure only safe content
    reaches the generation layer.
    """

    def __init__(self):
        settings = get_settings()
        self.trust_threshold = settings.trust_threshold

    def filter_by_trust(
        self, chunks: List[RetrievedChunk]
    ) -> List[RetrievedChunk]:
        """Remove any quarantine chunks that may have leaked through."""
        return [c for c in chunks if c.trust_level == "trusted"]

    def filter_by_relevance(
        self,
        chunks: List[RetrievedChunk],
        max_distance: float = 1.5,
    ) -> List[RetrievedChunk]:
        """Remove chunks that are too dissimilar to the query."""
        return [c for c in chunks if c.relevance_score <= max_distance]

    def apply_all(
        self,
        chunks: List[RetrievedChunk],
        allow_quarantine: bool = False,
    ) -> List[RetrievedChunk]:
        """Apply all filters in sequence."""
        if not allow_quarantine:
            chunks = self.filter_by_trust(chunks)
        chunks = self.filter_by_relevance(chunks)
        return chunks
