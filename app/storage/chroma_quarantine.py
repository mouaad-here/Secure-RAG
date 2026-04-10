"""
Secure RAG MVP — Quarantine ChromaDB Collection
Stores embeddings for documents that failed security scanning.
"""

import chromadb
from typing import List, Optional

from app.config import get_settings


class QuarantineStore:
    """
    ChromaDB collection for QUARANTINED document chunks.
    Chunks with trust_score < threshold are stored here.
    This collection is NOT queried during normal RAG retrieval.
    Used only for analysis, red-teaming, and admin review.
    """

    COLLECTION_NAME = "quarantine_documents"

    def __init__(self, persist_dir: Optional[str] = None):
        settings = get_settings()
        path = persist_dir or settings.chroma_persist_dir

        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[dict]] = None,
    ) -> int:
        """Add quarantined chunks with their embeddings."""
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas or [{}] * len(ids),
        )
        return len(ids)

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> dict:
        """Query quarantine (for testing/red-teaming only)."""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        return results

    def count(self) -> int:
        """Return the number of chunks in quarantine."""
        return self.collection.count()

    def list_flagged_documents(self) -> List[dict]:
        """List all unique documents in quarantine with their flags."""
        all_items = self.collection.get(include=["metadatas"])
        seen = {}
        for meta in (all_items.get("metadatas") or []):
            if meta and meta.get("source_document"):
                doc = meta["source_document"]
                if doc not in seen:
                    seen[doc] = meta
        return list(seen.values())
