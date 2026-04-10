"""
Secure RAG MVP — Retriever
Queries the trusted ChromaDB collection for relevant chunks.
"""

from typing import List, Optional
from dataclasses import dataclass

from app.config import get_settings
from app.retrieval.embeddings import EmbeddingGenerator
from app.storage.chroma_trusted import TrustedStore
from app.storage.chroma_quarantine import QuarantineStore


@dataclass
class RetrievedChunk:
    """A chunk retrieved from the vector store with relevance metadata."""
    chunk_id: str
    content: str
    relevance_score: float
    source_document: str
    trust_level: str  # "trusted" or "quarantine"
    metadata: dict


class Retriever:
    """
    Retrieve relevant chunks from the vector store.
    By default, only queries the TRUSTED collection.
    Quarantine collection is available for testing/red-teaming.
    """

    def __init__(self):
        settings = get_settings()
        self.top_k = settings.retrieval_top_k
        self.embedder = EmbeddingGenerator()
        self.trusted_store = TrustedStore()
        self.quarantine_store = QuarantineStore()

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        include_quarantine: bool = False,
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: The user's question.
            top_k: Number of results (default from config).
            include_quarantine: If True, also search quarantine (testing only).

        Returns:
            List of RetrievedChunk sorted by relevance.
        """
        k = top_k or self.top_k
        query_embedding = self.embedder.embed_query(query)

        # Always query trusted collection
        results = self._query_store(
            self.trusted_store, query_embedding, k, "trusted"
        )

        # Optionally include quarantine (for red-teaming)
        if include_quarantine:
            quarantine_results = self._query_store(
                self.quarantine_store, query_embedding, k, "quarantine"
            )
            results.extend(quarantine_results)

        # Sort by relevance score (lower distance = more relevant)
        results.sort(key=lambda c: c.relevance_score)
        return results[:k]

    def _query_store(
        self,
        store,
        query_embedding: List[float],
        top_k: int,
        trust_level: str,
    ) -> List[RetrievedChunk]:
        """Query a single ChromaDB collection."""
        raw = store.query(query_embedding=query_embedding, top_k=top_k)

        chunks = []
        ids = raw.get("ids", [[]])[0]
        docs = raw.get("documents", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]

        for i, chunk_id in enumerate(ids):
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    content=docs[i],
                    relevance_score=distances[i],
                    source_document=metadatas[i].get("source_document", "unknown"),
                    trust_level=trust_level,
                    metadata=metadatas[i],
                )
            )

        return chunks
