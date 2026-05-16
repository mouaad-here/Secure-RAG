"""
app/storage/sqlite_store.py — SQLite metadata and audit log store.

Layer: storage
Imports allowed: config, stdlib, sqlalchemy
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, JSON
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import get_settings

Base = declarative_base()


class DocumentRecord(Base):
    """SQLAlchemy model for document metadata."""
    __tablename__ = "documents"

    doc_id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    source_label = Column(String, default="unknown")
    ingested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    page_count = Column(Integer, nullable=True)
    chunk_count = Column(Integer, default=0)
    trust_score = Column(Float, nullable=True)
    trust_status = Column(String, default="pending")  # trusted, quarantine, pending
    scan_flags = Column(JSON, default=list)


class AuditLog(Base):
    """SQLAlchemy model for audit logging."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    event_type = Column(String, nullable=False)  # ingest, query, scan, firewall
    details = Column(Text, nullable=True)
    severity = Column(String, default="info")  # info, warning, alert, critical


class SQLiteStore:
    """Manages SQLite database for metadata and audit logging."""

    def __init__(self, db_path: Optional[str] = None):
        settings = get_settings()
        self.db_path = db_path or settings.sqlite_path

        # Ensure directory exists (guard: db_path may have no directory component)
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_document(self, metadata) -> str:
        """Save or update a document metadata record."""
        session = self.Session()
        try:
            record = DocumentRecord(
                doc_id=metadata.doc_id,
                filename=metadata.filename,
                file_type=metadata.file_type,
                file_size_bytes=metadata.file_size_bytes,
                source_label=metadata.source_label,
                page_count=metadata.page_count,
                chunk_count=metadata.chunk_count,
                trust_score=metadata.trust_score,
                trust_status=metadata.trust_status,
                scan_flags=metadata.scan_flags,
            )
            session.merge(record)
            session.commit()
            return metadata.doc_id
        finally:
            session.close()

    def get_document(self, doc_id: str) -> Optional[DocumentRecord]:
        """Retrieve a document record by ID."""
        session = self.Session()
        try:
            return session.query(DocumentRecord).filter_by(doc_id=doc_id).first()
        finally:
            session.close()

    def list_documents(self, trust_status: Optional[str] = None) -> List[DocumentRecord]:
        """List all documents, optionally filtered by trust status."""
        session = self.Session()
        try:
            query = session.query(DocumentRecord)
            if trust_status:
                query = query.filter_by(trust_status=trust_status)
            return query.order_by(DocumentRecord.ingested_at.desc()).all()
        finally:
            session.close()

    def log_event(self, event_type: str, details: str, severity: str = "info") -> None:
        """Write an audit log entry."""
        session = self.Session()
        try:
            entry = AuditLog(
                event_type=event_type,
                details=details,
                severity=severity,
            )
            session.add(entry)
            session.commit()
        finally:
            session.close()
