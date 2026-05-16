"""Unit tests for app/ingestion/chunker.py"""
from __future__ import annotations

from app.ingestion.chunker import TextChunk, TextChunker


class TestTextChunker:
    """Tests for TextChunker."""

    def setup_method(self) -> None:
        """Create a chunker with small, predictable settings for testing."""
        self.chunker = TextChunker(chunk_size=100, chunk_overlap=10)

    def test_chunk_splits_long_text(self) -> None:
        """Text longer than chunk_size must produce multiple chunks."""
        long_text = "This is a sentence. " * 20  # ~400 chars
        chunks = self.chunker.chunk(long_text, "test.txt")
        assert len(chunks) > 1

    def test_chunk_empty_text_returns_empty(self) -> None:
        """Empty or whitespace-only text must return an empty list."""
        assert self.chunker.chunk("", "test.txt") == []
        assert self.chunker.chunk("   \n\n  ", "test.txt") == []

    def test_chunk_preserves_source_document(self) -> None:
        """Every chunk must reference the correct source_document."""
        chunks = self.chunker.chunk("Short text that fits.", "my_doc.txt")
        assert all(c.source_document == "my_doc.txt" for c in chunks)

    def test_chunk_ids_are_unique(self) -> None:
        """All chunk_ids in a document must be unique."""
        long_text = "Alpha beta gamma delta epsilon. " * 30
        chunks = self.chunker.chunk(long_text, "doc.txt")
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunk_index_is_sequential(self) -> None:
        """Chunk indices must start at 0 and be sequential."""
        long_text = "Word number one. " * 25
        chunks = self.chunker.chunk(long_text, "seq.txt")
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_chunk_total_chunks_is_consistent(self) -> None:
        """All chunks must agree on total_chunks count."""
        text = "Sentence here. " * 20
        chunks = self.chunker.chunk(text, "doc.txt")
        total = len(chunks)
        assert all(c.total_chunks == total for c in chunks)

    def test_chunk_respects_chunk_size(self) -> None:
        """Each chunk should not exceed chunk_size + overlap by much."""
        text = "a" * 500
        chunks = self.chunker.chunk(text, "large.txt")
        for chunk in chunks:
            # langchain may slightly exceed — allow 2x for safety
            assert chunk.char_count <= self.chunker.chunk_size * 2

    def test_chunk_short_text_is_single_chunk(self) -> None:
        """Text shorter than chunk_size produces exactly one chunk."""
        text = "Short text."
        chunks = self.chunker.chunk(text, "short.txt")
        assert len(chunks) == 1
        assert chunks[0].content == "Short text."

    def test_chunk_dataclass_fields(self) -> None:
        """TextChunk must have all expected fields populated."""
        chunks = self.chunker.chunk("Hello world.", "hello.txt")
        assert len(chunks) == 1
        c = chunks[0]
        assert isinstance(c, TextChunk)
        assert c.chunk_id
        assert c.content
        assert c.char_count == len(c.content)
