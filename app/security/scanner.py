"""
Secure RAG MVP — Input Security Scanner
Detects prompt injection attempts and suspicious content in documents.
Computes a trust score (0.0 to 1.0) per chunk.
"""

import math
import re
from typing import List, Tuple
from dataclasses import dataclass, field

import tldextract

from app.security.patterns import (
    DIRECT_INJECTION_PATTERNS,
    INDIRECT_INJECTION_PATTERNS,
    JAILBREAK_PATTERNS,
)


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

    # Patterns are imported from app.security.patterns

    # --- Scoring weights (single hit drives score below 0.7 threshold) ---
    WEIGHTS = {
        "direct_injection": 0.40,   # 1 hit → score 0.60
        "indirect_injection": 0.35, # 1 hit → score 0.65
        "jailbreak": 0.35,          # 1 hit → score 0.65
        "suspicious_url": 0.15,
        "high_entropy": 0.35,       # Detects base64/obfuscation
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
        hits, msgs = self._check_patterns(text, DIRECT_INJECTION_PATTERNS, "DIRECT_INJECTION")
        if hits > 0:
            penalty += self.WEIGHTS["direct_injection"] * min(hits, 3)
            flags.append("DIRECT_INJECTION")
            details.extend(msgs)

        # Check indirect injection
        hits, msgs = self._check_patterns(text, INDIRECT_INJECTION_PATTERNS, "INDIRECT_INJECTION")
        if hits > 0:
            penalty += self.WEIGHTS["indirect_injection"] * min(hits, 3)
            flags.append("INDIRECT_INJECTION")
            details.extend(msgs)

        # Check jailbreak
        hits, msgs = self._check_patterns(text, JAILBREAK_PATTERNS, "JAILBREAK")
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

        # Check entropy (obfuscation detection)
        entropy = self._calculate_entropy(text)
        if entropy > 5.5:
            penalty += self.WEIGHTS["high_entropy"]
            flags.append("HIGH_ENTROPY")
            details.append(f"HIGH_ENTROPY: Shannon entropy is {entropy:.2f} (threshold 5.5)")

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

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy to detect heavily obfuscated text."""
        if not text:
            return 0.0
        
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1
            
        entropy = 0.0
        text_len = len(text)
        for count in char_counts.values():
            p = count / text_len
            entropy -= p * math.log2(p)
            
        return entropy
