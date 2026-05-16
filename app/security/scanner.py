"""
Secure RAG MVP — Input Security Scanner
Detects prompt injection attempts and suspicious content in documents.
Computes a trust score (0.0 to 1.0) per chunk.
"""

import re
from typing import List, Tuple
from dataclasses import dataclass, field

import tldextract


@dataclass
class ScanResult:
    """Result of scanning a text chunk for security threats."""
    trust_score: float  # 0.0 (very suspicious) to 1.0 (clean)
    flags: List[str] = field(default_factory=list)
    details: List[str] = field(default_factory=list)


class SecurityScanner:
    """
    Scan document text for prompt injection patterns and suspicious content.

    Detection categories:
    1. Direct injection (imperative instructions to the LLM)
    2. Indirect injection (hidden instructions in document text)
    3. Data exfiltration (suspicious URLs)
    4. Jailbreak patterns (roleplay, persona switching)
    """

    # --- Direct injection patterns ---
    DIRECT_INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|prompts?)", re.I),
        re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.I),
        re.compile(r"forget\s+(everything|all|your)\s+(you|instructions?|rules?)", re.I),
        re.compile(r"you\s+are\s+now\s+", re.I),
        re.compile(r"new\s+instructions?:", re.I),
        re.compile(r"system\s*prompt:", re.I),
        re.compile(r"override\s+(previous|all|system)", re.I),
    ]

    # --- Indirect injection patterns ---
    INDIRECT_INJECTION_PATTERNS = [
        re.compile(r"when\s+asked\s+about\s+.+,?\s+(respond|say|answer|reply)\s+with", re.I),
        re.compile(r"always\s+(respond|say|answer|reply)\s+(with|that)", re.I),
        re.compile(r"if\s+(the\s+)?user\s+asks?\s+", re.I),
        re.compile(r"instead\s+of\s+.+,?\s+(say|respond|answer)", re.I),
    ]

    # --- Jailbreak patterns ---
    JAILBREAK_PATTERNS = [
        re.compile(r"(pretend|imagine|act\s+as\s+if)\s+you\s+are", re.I),
        re.compile(r"roleplay\s+as", re.I),
        re.compile(r"reveal\s+(your\s+)?(system\s+)?prompt", re.I),
        re.compile(r"DAN\s+mode", re.I),
        re.compile(r"developer\s+mode\s+(enabled|on)", re.I),
    ]

    # --- Scoring weights (single hit drives score below 0.7 threshold) ---
    WEIGHTS = {
        "direct_injection": 0.40,   # 1 hit → score 0.60
        "indirect_injection": 0.35, # 1 hit → score 0.65
        "jailbreak": 0.35,          # 1 hit → score 0.65
        "suspicious_url": 0.15,
    }

    def __init__(self, url_allowlist: set | None = None):
        from app.config import get_settings
        settings = get_settings()
        self.url_allowlist = url_allowlist or settings.url_allowlist_set

    def scan(self, text: str) -> ScanResult:
        """
        Scan text and return a trust score with detailed flags.

        Args:
            text: The text content to scan.

        Returns:
            ScanResult with trust_score and flags.
        """
        flags = []
        details = []
        penalty = 0.0

        # Check direct injection
        hits, msgs = self._check_patterns(text, self.DIRECT_INJECTION_PATTERNS, "DIRECT_INJECTION")
        if hits > 0:
            penalty += self.WEIGHTS["direct_injection"] * min(hits, 3)
            flags.append("DIRECT_INJECTION")
            details.extend(msgs)

        # Check indirect injection
        hits, msgs = self._check_patterns(text, self.INDIRECT_INJECTION_PATTERNS, "INDIRECT_INJECTION")
        if hits > 0:
            penalty += self.WEIGHTS["indirect_injection"] * min(hits, 3)
            flags.append("INDIRECT_INJECTION")
            details.extend(msgs)

        # Check jailbreak
        hits, msgs = self._check_patterns(text, self.JAILBREAK_PATTERNS, "JAILBREAK")
        if hits > 0:
            penalty += self.WEIGHTS["jailbreak"] * min(hits, 3)
            flags.append("JAILBREAK")
            details.extend(msgs)

        # Check suspicious URLs
        url_hits, url_msgs = self._check_urls(text)
        if url_hits > 0:
            penalty += self.WEIGHTS["suspicious_url"] * min(url_hits, 3)
            flags.append("SUSPICIOUS_URL")
            details.extend(url_msgs)

        trust_score = max(0.0, min(1.0, 1.0 - penalty))

        return ScanResult(
            trust_score=round(trust_score, 3),
            flags=flags,
            details=details,
        )

    def scan_chunks(self, chunks: List[str]) -> List[ScanResult]:
        """Scan multiple chunks."""
        return [self.scan(chunk) for chunk in chunks]

    def _check_patterns(
        self,
        text: str,
        patterns: List[re.Pattern],
        category: str,
    ) -> Tuple[int, List[str]]:
        """Check text against a list of regex patterns."""
        hits = 0
        messages = []
        for pattern in patterns:
            matches = pattern.findall(text)
            if matches:
                hits += len(matches)
                messages.append(f"{category}: matched '{pattern.pattern}' ({len(matches)}x)")
        return hits, messages

    def _check_urls(self, text: str) -> Tuple[int, List[str]]:
        """Check for suspicious URLs not on the allowlist."""
        url_pattern = re.compile(r"https?://[^\s<>\"']+", re.I)
        urls = url_pattern.findall(text)

        hits = 0
        messages = []
        for url in urls:
            extracted = tldextract.extract(url)
            domain = f"{extracted.domain}.{extracted.suffix}"
            if domain not in self.url_allowlist:
                hits += 1
                messages.append(f"SUSPICIOUS_URL: '{url}' (domain: {domain} not in allowlist)")

        return hits, messages
