"""
app/exceptions.py — Custom exception hierarchy for Secure RAG MVP.

Layer: all
Imports allowed: none (stdlib only)
"""
from __future__ import annotations


class SecureRAGError(Exception):
    """Base exception for all Secure RAG errors."""


class UnsupportedFileTypeError(SecureRAGError):
    """Raised when a file type is not supported by the document loader."""


class DocumentLoadError(SecureRAGError):
    """Raised when a document cannot be loaded or parsed."""


class StorageError(SecureRAGError):
    """Raised when a storage operation (SQLite or ChromaDB) fails."""


class EmbeddingError(SecureRAGError):
    """Raised when embedding generation fails (e.g. Ollama unreachable)."""


class RetrievalError(SecureRAGError):
    """Raised when vector store retrieval fails."""
