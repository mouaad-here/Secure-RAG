"""
Secure RAG MVP — Document Loader
Handles loading PDF, Markdown, and plain text files.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone


@dataclass
class LoadedDocument:
    """Represents a loaded document with its raw text and metadata."""
    filename: str
    content: str
    file_type: str  # "pdf", "md", "txt"
    file_size_bytes: int
    source_label: str = "unknown"
    loaded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    page_count: Optional[int] = None


class DocumentLoader:
    """
    Load documents from various file formats.
    Supports: PDF, Markdown (.md), Plain Text (.txt)
    """

    SUPPORTED_TYPES = {".pdf", ".md", ".txt"}

    def load_from_bytes(
        self,
        content: bytes,
        filename: str,
        source_label: str = "unknown",
    ) -> LoadedDocument:
        """Load a document from raw bytes."""
        file_ext = self._get_extension(filename)
        self._validate_type(file_ext)

        if file_ext == ".pdf":
            text, page_count = self._load_pdf(content)
        elif file_ext in (".md", ".txt"):
            text = content.decode("utf-8", errors="replace")
            page_count = None
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

        return LoadedDocument(
            filename=filename,
            content=text,
            file_type=file_ext.lstrip("."),
            file_size_bytes=len(content),
            source_label=source_label,
            page_count=page_count,
        )

    def load_from_path(self, filepath: str, source_label: str = "unknown") -> LoadedDocument:
        """Load a document from a file path."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(filepath, "rb") as f:
            content = f.read()

        filename = os.path.basename(filepath)
        return self.load_from_bytes(content, filename, source_label)

    def _load_pdf(self, content: bytes) -> tuple[str, int]:
        """Extract text from a PDF file."""
        from pypdf import PdfReader
        from io import BytesIO

        reader = PdfReader(BytesIO(content))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())

        return "\n\n".join(pages), len(reader.pages)

    def _get_extension(self, filename: str) -> str:
        """Extract file extension."""
        if "." not in filename:
            return ""
        return "." + filename.rsplit(".", 1)[-1].lower()

    def _validate_type(self, file_ext: str) -> None:
        """Validate file type is supported."""
        if file_ext not in self.SUPPORTED_TYPES:
            raise ValueError(
                f"Unsupported file type: '{file_ext}'. "
                f"Supported: {self.SUPPORTED_TYPES}"
            )
