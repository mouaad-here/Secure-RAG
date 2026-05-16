"""
app/ingestion/chunker.py — Text chunking using RecursiveCharacterTextSplitter.

Layer: ingestion
Imports allowed: config, stdlib, langchain_text_splitters
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings


@dataclass
class TextChunk:
    """A single chunk of text with positional metadata."""
    chunk_id: str
    content: str
    index: int        # Position in the document (0-based)
    total_chunks: int
    char_count: int
    source_document: str


class TextChunker:
    """
    Split text into overlapping chunks using recursive character splitting.
    Respects paragraph and sentence boundaries where possible.
    """

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        settings = get_settings()
        self.chunk_size = chunk_size or settings.max_chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk(self, text: str, source_document: str) -> List[TextChunk]:
        """
        Split text into chunks.

        Args:
            text: Normalized text to split.
            source_document: Source filename for metadata.

        Returns:
            List of TextChunk objects.
        """
        if not text.strip():
            return []

        raw_chunks = self._splitter.split_text(text)
        total = len(raw_chunks)

        return [
            TextChunk(
                chunk_id=f"{source_document}::chunk_{i:04d}",
                content=chunk,
                index=i,
                total_chunks=total,
                char_count=len(chunk),
                source_document=source_document,
            )
            for i, chunk in enumerate(raw_chunks)
        ]
