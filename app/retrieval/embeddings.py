"""
Secure RAG MVP — Embedding Generator
Generates embeddings using Ollama's nomic-embed-text model.
"""

from typing import List

import ollama as ollama_lib

from app.config import get_settings


class EmbeddingGenerator:
    """
    Generate text embeddings using Ollama's local embedding model.
    Uses nomic-embed-text for high-quality, local embeddings.
    """

    def __init__(self, model: str | None = None, ollama_host: str | None = None):
        settings = get_settings()
        self.model = model or settings.embedding_model
        self.host = ollama_host or settings.ollama_host
        self._client = ollama_lib.Client(host=self.host)

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text string."""
        response = self._client.embed(model=self.model, input=text)
        return response["embeddings"][0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        response = self._client.embed(model=self.model, input=texts)
        return response["embeddings"]

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a search query (alias for embed_text)."""
        return self.embed_text(query)
