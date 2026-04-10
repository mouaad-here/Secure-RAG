"""
Secure RAG MVP — Citation Builder
Extracts and validates citations from LLM responses.
"""

import re
from typing import List
from dataclasses import dataclass

from app.retrieval.retriever import RetrievedChunk


@dataclass
class Citation:
    """A validated citation linking a claim to a source document."""
    source_document: str
    chunk_id: str
    relevance_score: float
    trust_level: str
    cited_in_response: bool  # Whether the LLM actually cited this source


class CitationBuilder:
    """
    Build and validate citations from LLM responses.
    Cross-references [Source: filename] tags in the response
    against the actual retrieved chunks.
    """

    # Pattern to match [Source: filename] citations in LLM output
    CITATION_PATTERN = re.compile(r"\[Source:\s*(.+?)\]", re.IGNORECASE)

    def build_citations(
        self,
        response: str,
        chunks: List[RetrievedChunk],
    ) -> List[Citation]:
        """
        Build citations by matching LLM response references to retrieved chunks.

        Args:
            response: The raw LLM response text.
            chunks: The chunks that were provided as context.

        Returns:
            List of Citation objects.
        """
        # Extract cited sources from the response
        cited_sources = set(self.CITATION_PATTERN.findall(response))
        cited_sources_lower = {s.lower().strip() for s in cited_sources}

        citations = []
        for chunk in chunks:
            doc_name = chunk.source_document
            cited = any(
                doc_name.lower() in cs or cs in doc_name.lower()
                for cs in cited_sources_lower
            )

            citations.append(
                Citation(
                    source_document=doc_name,
                    chunk_id=chunk.chunk_id,
                    relevance_score=chunk.relevance_score,
                    trust_level=chunk.trust_level,
                    cited_in_response=cited,
                )
            )

        return citations

    def citation_accuracy(self, citations: List[Citation]) -> float:
        """
        Calculate citation accuracy: % of retrieved chunks that were cited.
        Returns value between 0.0 and 1.0.
        """
        if not citations:
            return 0.0
        cited = sum(1 for c in citations if c.cited_in_response)
        return cited / len(citations)
