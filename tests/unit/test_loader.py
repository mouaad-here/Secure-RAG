"""
Unit Tests — Document Loader
"""

import pytest
from app.ingestion.loader import DocumentLoader, LoadedDocument


class TestDocumentLoader:
    """Tests for the DocumentLoader class."""

    def setup_method(self):
        self.loader = DocumentLoader()

    def test_load_txt_from_bytes(self):
        """Load a plain text file from bytes."""
        content = b"Hello, this is a test document."
        doc = self.loader.load_from_bytes(content, "test.txt", "unit_test")
        assert isinstance(doc, LoadedDocument)
        assert doc.filename == "test.txt"
        assert doc.file_type == "txt"
        assert doc.content == "Hello, this is a test document."
        assert doc.file_size_bytes == len(content)

    def test_load_md_from_bytes(self):
        """Load a markdown file from bytes."""
        content = b"# Title\n\nSome **bold** text."
        doc = self.loader.load_from_bytes(content, "readme.md")
        assert doc.file_type == "md"
        assert "# Title" in doc.content

    def test_reject_unsupported_type(self):
        """Reject unsupported file types."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            self.loader.load_from_bytes(b"data", "file.exe")

    def test_reject_no_extension(self):
        """Reject files without extensions."""
        with pytest.raises(ValueError):
            self.loader.load_from_bytes(b"data", "noext")

    def test_metadata_fields(self):
        """Verify all metadata fields are populated."""
        doc = self.loader.load_from_bytes(b"test", "doc.txt", "test_source")
        assert doc.source_label == "test_source"
        assert doc.loaded_at is not None
        assert doc.page_count is None  # Only PDFs have page count
