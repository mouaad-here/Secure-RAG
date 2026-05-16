"""
app/ingestion/normalizer.py — Text normalization for extracted document content.

Layer: ingestion
Imports allowed: stdlib only
"""
from __future__ import annotations

import re
import unicodedata


class TextNormalizer:
    """
    Normalize raw document text for reliable downstream processing.
    Handles: unicode normalization, whitespace cleanup, control character removal.
    """

    def normalize(self, text: str) -> str:
        """
        Apply all normalization steps to raw text.

        Args:
            text: Raw extracted text from document loader.

        Returns:
            Cleaned and normalized text.
        """
        if not text or not text.strip():
            return ""

        text = self._normalize_unicode(text)
        text = self._remove_control_chars(text)
        text = self._normalize_whitespace(text)
        text = self._normalize_line_breaks(text)
        text = text.strip()

        return text

    def _normalize_unicode(self, text: str) -> str:
        """Normalize unicode to NFC form (composed characters)."""
        return unicodedata.normalize("NFC", text)

    def _remove_control_chars(self, text: str) -> str:
        """Remove non-printable control characters (except newlines and tabs)."""
        return "".join(
            char for char in text
            if char in ("\n", "\t", "\r") or not unicodedata.category(char).startswith("C")
        )

    def _normalize_whitespace(self, text: str) -> str:
        """Collapse multiple spaces/tabs into single space (preserving newlines)."""
        # Replace tabs with spaces
        text = text.replace("\t", " ")
        # Collapse multiple spaces (but not newlines)
        text = re.sub(r"[^\S\n]+", " ", text)
        return text

    def _normalize_line_breaks(self, text: str) -> str:
        """Normalize line breaks: collapse 3+ newlines into 2."""
        text = text.replace("\r\n", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text
