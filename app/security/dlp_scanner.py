"""
Secure RAG MVP — Data Loss Prevention (DLP) Scanner
Detects and redacts sensitive PII (Personally Identifiable Information) and 
confidential data to prevent it from reaching the embedding store or LLM.
"""

import re
from typing import List, Tuple
from dataclasses import dataclass, field


@dataclass
class DLPResult:
    """Result of scanning text for sensitive data."""
    original_text: str
    redacted_text: str
    is_sensitive: bool
    flags: List[str] = field(default_factory=list)


class PIIScanner:
    """
    Scans for sensitive information and replaces it with [REDACTED PII].
    
    Checks for:
    - Emails
    - Phone numbers (basic formats)
    - Social Security Numbers / ID patterns
    - Salary or financial numbers
    - Passwords and credentials
    - API keys and tokens
    - Keywords: CONFIDENTIAL, INTERNAL ONLY
    - User-defined custom sensitive patterns
    """
    
    # Regex patterns for sensitive data
    PATTERNS = {
        "EMAIL": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
        "SSN": re.compile(r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b"),
        "PHONE": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "CREDIT_CARD": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
        "SALARY": re.compile(r"(?i)((?:salary|compensation|bonus|pay).{0,15})(\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"),
        "PASSWORD": re.compile(r"(?i)((?:password|passwd|pwd)\b.{0,10}\b)([a-zA-Z0-9_\-@#$!%*?&]{8,40})"),
        "API_KEY": re.compile(r"(?i)((?:api[_-]?key|token|auth[_-]?token|secret[_-]?key|private[_-]?key)\b.{0,10}\b)([a-zA-Z0-9_\-]{20,60})"),
        "CONFIDENTIAL_MARKER": re.compile(r"(?i)\b(?:strictly\s+confidential|internal\s+only|do\s+not\s+share)\b")
    }

    def __init__(self) -> None:
        """Initialize the scanner and load custom patterns from configuration."""
        from app.config import get_settings
        settings = get_settings()
        self.custom_patterns: list[re.Pattern] = []
        if settings.custom_sensitive_patterns:
            for pat in settings.custom_sensitive_patterns.split(","):
                pat = pat.strip()
                if pat:
                    try:
                        self.custom_patterns.append(re.compile(pat, re.I))
                    except re.error:
                        self.custom_patterns.append(re.compile(re.escape(pat), re.I))

    def redact(self, text: str) -> DLPResult:
        """
        Scan text for sensitive patterns and redact them.
        """
        flags = set()
        redacted_text = text
        
        # We process patterns sequentially, redacting matches
        for flag_name, pattern in self.PATTERNS.items():
            matches = pattern.findall(redacted_text)
            if matches:
                flags.add(flag_name)
                # For SALARY, PASSWORD, and API_KEY, we redact only the sensitive value (Group 2) to preserve context.
                if flag_name in ("SALARY", "PASSWORD", "API_KEY"):
                    redacted_text = pattern.sub(r"\1[REDACTED PII]", redacted_text)
                else:
                    redacted_text = pattern.sub("[REDACTED PII]", redacted_text)
                    
        # Process custom patterns
        for i, pattern in enumerate(self.custom_patterns):
            matches = pattern.findall(redacted_text)
            if matches:
                flags.add(f"CUSTOM_PII_{i+1}")
                redacted_text = pattern.sub("[REDACTED PII]", redacted_text)
                
        is_sensitive = len(flags) > 0
        
        return DLPResult(
            original_text=text,
            redacted_text=redacted_text,
            is_sensitive=is_sensitive,
            flags=list(flags)
        )
