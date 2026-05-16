"""Unit tests for app/retrieval/retriever.py — all dependencies mocked."""
from __future__ import annotations

from typing import List
from unittest.mock import MagicMock, patch

import pytest
from app.retrieval.retriever import Retriever


def _make_chroma_result(ids: List[str], docs: List[str], distances: List[float]) -> dict:
    """Helper to build a Chroma-style query result dict."""
    metadatas = [{"source_document": f"doc_{i}.txt"} for i in range(len(ids))]
    return {
        "ids": [ids],
        "documents": [docs],
        "distances": [distances],
        "metadatas": [metadatas],
    }


@pytest.fixture()
def mock_retriever():
    """Return a Retriever with all external dependencies mocked."""
    with (
        patch("app.retrieval.retriever.EmbeddingGenerator") as mock_embed_cls,
        patch("app.retrieval.retriever.TrustedStore") as mock_trusted_cls,
        patch("app.retrieval.retriever.QuarantineStore") as mock_quarantine_cls,
    ):
        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.1] * 768
        mock_embed_cls.return_value = mock_embedder

        mock_trusted = MagicMock()
        mock_trusted.query.return_value = _make_chroma_result(
            ["chunk_0", "chunk_1", "chunk_2"],
            ["Text A", "Text B", "Text C"],
            [0.1, 0.3, 0.5],
        )
        mock_trusted_cls.return_value = mock_trusted

        mock_quarantine = MagicMock()
        mock_quarantine.query.return_value = _make_chroma_result(
            ["q_chunk_0"],
            ["Quarantine text"],
            [0.2],
        )
        mock_quarantine_cls.return_value = mock_quarantine

        retriever = Retriever()
        retriever.embedder = mock_embedder
        retriever.trusted_store = mock_trusted
        retriever.quarantine_store = mock_quarantine

        yield retriever, mock_trusted, mock_quarantine, mock_embedder


class TestRetriever:
    """Tests for Retriever — all I/O mocked."""

    def test_retrieve_calls_trusted_store_only(self, mock_retriever) -> None:
        """Default retrieve() must only query the trusted collection."""
        retriever, mock_trusted, mock_quarantine, _ = mock_retriever
        retriever.retrieve("What is the vacation policy?")
        mock_trusted.query.assert_called_once()
        mock_quarantine.query.assert_not_called()

    def test_retrieve_returns_sorted_by_relevance(self, mock_retriever) -> None:
        """Results must be sorted by relevance_score ascending (lower = better)."""
        retriever, *_ = mock_retriever
        chunks = retriever.retrieve("Vacation days?")
        scores = [c.relevance_score for c in chunks]
        assert scores == sorted(scores)

    def test_retrieve_does_not_call_quarantine_by_default(self, mock_retriever) -> None:
        """include_quarantine=False must never touch QuarantineStore."""
        retriever, _, mock_quarantine, _ = mock_retriever
        retriever.retrieve("Question", include_quarantine=False)
        mock_quarantine.query.assert_not_called()

    def test_retrieve_can_include_quarantine_when_flag_set(self, mock_retriever) -> None:
        """include_quarantine=True must query both collections."""
        retriever, mock_trusted, mock_quarantine, _ = mock_retriever
        retriever.retrieve("Question", include_quarantine=True)
        mock_trusted.query.assert_called_once()
        mock_quarantine.query.assert_called_once()

    def test_retrieve_respects_top_k(self, mock_retriever) -> None:
        """retrieve() must return at most top_k results."""
        retriever, *_ = mock_retriever
        chunks = retriever.retrieve("Question", top_k=2)
        assert len(chunks) <= 2

    def test_retrieve_embeds_query(self, mock_retriever) -> None:
        """embed_query must be called exactly once per retrieve() call."""
        retriever, _, _, mock_embedder = mock_retriever
        retriever.retrieve("How many holidays?")
        mock_embedder.embed_query.assert_called_once_with("How many holidays?")

    def test_retrieved_chunk_trust_level(self, mock_retriever) -> None:
        """All chunks from trusted store must have trust_level='trusted'."""
        retriever, *_ = mock_retriever
        chunks = retriever.retrieve("Question")
        assert all(c.trust_level == "trusted" for c in chunks)
