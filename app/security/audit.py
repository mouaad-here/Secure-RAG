"""
Secure RAG MVP — Security Audit Logger
Writes irrefutable JSONL audit logs of all security scan events.
"""

import json
import os
import time
from typing import Any, Dict, List

from app.config import get_settings


class AuditLogger:
    """
    Logs security scan events to a JSONL file.
    JSONL ensures easy parsing by SIEMs (Splunk, Elastic, etc.).
    """

    def __init__(self):
        settings = get_settings()
        self.log_dir = settings.log_dir
        self.log_file = os.path.join(self.log_dir, "scan_audit.jsonl")

        # Ensure directory exists
        os.makedirs(self.log_dir, exist_ok=True)

    def log_scan_event(
        self,
        doc_id: str,
        filename: str,
        trust_score: float,
        flags: List[str],
        details: List[str],
        action_taken: str,
    ) -> None:
        """
        Log a single document scan event.

        Args:
            doc_id: The UUID of the document.
            filename: The original filename.
            trust_score: The computed trust score (0.0 - 1.0).
            flags: List of triggered security flags.
            details: List of detailed match strings.
            action_taken: E.g., "trusted", "quarantine", "rejected".
        """
        event: Dict[str, Any] = {
            "timestamp": time.time(),
            "event_type": "document_scan",
            "doc_id": doc_id,
            "filename": filename,
            "trust_score": trust_score,
            "flags": flags,
            "details": details,
            "action_taken": action_taken,
        }

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as exc:
            # Fallback to stdout if file write fails, but don't crash the API
            print(f"FAILED TO WRITE AUDIT LOG: {exc}. Event: {event}")
