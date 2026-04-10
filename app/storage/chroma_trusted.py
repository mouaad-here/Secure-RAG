"""
Secure RAG MVP — Trusted ChromaDB Collection
Stores embeddings for documents that passed security scanning.
"""

import chromadb
from typing import List, Optional

from app.config import get_settings


class TrustedStore:
    """
    ChromaDB collection for TRUSTED document chunks.
    Only chunks with trust_score >= threshold are stored here.
    This is the primary collection queried during RAG retrieval.
    """

    COLLECTION_NAME = "trusted_documents"

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
        """Add trusted chunks with their embeddings."""
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
        """Query the trusted collection for similar chunks."""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        return results

    def count(self) -> int:
        """Return the number of chunks in the trusted collection."""
        return self.collection.count()

    def delete_by_document(self, source_document: str) -> None:
        """Delete all chunks from a specific document."""
        self.collection.delete(
            where={"source_document": source_document}
        )
