"""
Secure RAG MVP — Document Metadata Builder
Constructs metadata records for ingested documents.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List


@dataclass
class DocumentMetadata:
    """Complete metadata record for an ingested document."""
    doc_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    source_label: str
    ingested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    page_count: Optional[int] = None
    chunk_count: int = 0
    trust_score: Optional[float] = None
    trust_status: str = "pending"  # "trusted", "quarantine", "pending"
    scan_flags: List[str] = field(default_factory=list)


class MetadataBuilder:
    """Build metadata records for documents as they flow through the pipeline."""

    @staticmethod
    def build(
        filename: str,
        file_type: str,
        file_size_bytes: int,
        source_label: str = "unknown",
        page_count: Optional[int] = None,
    ) -> DocumentMetadata:
        """Create initial metadata for a newly loaded document."""
        doc_id = f"{filename}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        return DocumentMetadata(
            doc_id=doc_id,
            filename=filename,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            source_label=source_label,
            page_count=page_count,
        )

    @staticmethod
    def update_after_chunking(metadata: DocumentMetadata, chunk_count: int) -> DocumentMetadata:
        """Update metadata after chunking."""
        metadata.chunk_count = chunk_count
        return metadata

    @staticmethod
    def update_after_scan(
        metadata: DocumentMetadata,
        trust_score: float,
        trust_threshold: float,
        scan_flags: List[str],
    ) -> DocumentMetadata:
        """Update metadata after security scanning."""
        metadata.trust_score = trust_score
        metadata.scan_flags = scan_flags
        metadata.trust_status = "trusted" if trust_score >= trust_threshold else "quarantine"
        return metadata
