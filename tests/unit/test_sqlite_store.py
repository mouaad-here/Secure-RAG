"""Unit tests for app/storage/sqlite_store.py"""
from __future__ import annotations

from app.ingestion.metadata import DocumentMetadata, MetadataBuilder
from app.storage.sqlite_store import SQLiteStore


def _make_store(tmp_path) -> SQLiteStore:
    """Create an isolated SQLiteStore backed by a temp file."""
    db_path = str(tmp_path / "test.db")
    return SQLiteStore(db_path=db_path)


def _make_metadata(**overrides) -> DocumentMetadata:
    """Build a minimal DocumentMetadata for testing."""
    meta = MetadataBuilder.build(
        filename=overrides.get("filename", "test_doc.txt"),
        file_type=overrides.get("file_type", "txt"),
        file_size_bytes=overrides.get("file_size_bytes", 100),
        source_label=overrides.get("source_label", "test"),
    )
    meta.chunk_count = overrides.get("chunk_count", 3)
    meta.trust_score = overrides.get("trust_score", 1.0)
    meta.trust_status = overrides.get("trust_status", "trusted")
    return meta


class TestSQLiteStore:
    """Tests for SQLiteStore."""

    def test_save_and_retrieve_document(self, tmp_path) -> None:
        """Saved document must be retrievable by doc_id."""
        store = _make_store(tmp_path)
        meta = _make_metadata(filename="handbook.pdf")
        store.save_document(meta)

        record = store.get_document(meta.doc_id)
        assert record is not None
        assert record.doc_id == meta.doc_id
        assert record.filename == "handbook.pdf"

    def test_list_documents_returns_all(self, tmp_path) -> None:
        """list_documents() must return all saved documents."""
        store = _make_store(tmp_path)
        meta_a = _make_metadata(filename="a.txt")
        meta_b = _make_metadata(filename="b.txt")
        store.save_document(meta_a)
        store.save_document(meta_b)

        records = store.list_documents()
        assert len(records) == 2

    def test_list_documents_filtered_by_trust_status(self, tmp_path) -> None:
        """list_documents(trust_status) must return only matching records."""
        store = _make_store(tmp_path)
        trusted = _make_metadata(filename="clean.txt", trust_status="trusted")
        quarantine = _make_metadata(filename="bad.txt", trust_status="quarantine")
        store.save_document(trusted)
        store.save_document(quarantine)

        trusted_records = store.list_documents(trust_status="trusted")
        quarantine_records = store.list_documents(trust_status="quarantine")
        assert len(trusted_records) == 1
        assert trusted_records[0].filename == "clean.txt"
        assert len(quarantine_records) == 1
        assert quarantine_records[0].filename == "bad.txt"

    def test_log_event_writes_audit_record(self, tmp_path) -> None:
        """log_event() must persist at least one audit_log row."""
        store = _make_store(tmp_path)
        store.log_event("ingest_complete", "doc_id=abc chunks=5 status=trusted")

        from app.storage.sqlite_store import AuditLog
        session = store.Session()
        try:
            logs = session.query(AuditLog).all()
            assert len(logs) == 1
            assert logs[0].event_type == "ingest_complete"
        finally:
            session.close()

    def test_get_nonexistent_document_returns_none(self, tmp_path) -> None:
        """get_document() must return None for an unknown doc_id."""
        store = _make_store(tmp_path)
        result = store.get_document("non-existent-uuid")
        assert result is None

    def test_save_updates_existing_document(self, tmp_path) -> None:
        """Saving the same doc_id twice must update, not duplicate."""
        store = _make_store(tmp_path)
        meta = _make_metadata(filename="update_me.txt", chunk_count=2)
        store.save_document(meta)

        meta.chunk_count = 10
        store.save_document(meta)

        records = store.list_documents()
        assert len(records) == 1
        assert records[0].chunk_count == 10

    def test_trust_score_persisted(self, tmp_path) -> None:
        """trust_score and trust_status must be accurately stored."""
        store = _make_store(tmp_path)
        meta = _make_metadata(trust_score=0.42, trust_status="quarantine")
        store.save_document(meta)

        record = store.get_document(meta.doc_id)
        assert record is not None
        assert abs(record.trust_score - 0.42) < 0.001
        assert record.trust_status == "quarantine"
