"""
Secure RAG MVP — Output Firewall
Last line of defense — scans LLM output before returning to user.
"""

import re
from typing import List, Tuple
from dataclasses import dataclass, field

import tldextract

from app.config import get_settings


@dataclass
class FirewallResult:
    """Result of output firewall scan."""
    action: str  # ALLOW, WARN, SANITIZE, BLOCK
    original_response: str
    sanitized_response: str
    flags: List[str] = field(default_factory=list)
    details: List[str] = field(default_factory=list)


class OutputFirewall:
    """
    Scan and sanitize LLM output before returning to the user.

    Checks:
    1. URL allowlist — block unauthorized URLs
    2. Leaked instructions — detect if LLM revealed system prompt
    3. Groundedness — basic check that answer relates to context
    """

    LEAKED_INSTRUCTION_PATTERNS = [
        re.compile(r"(my|the)\s+(system\s+)?instructions?\s+(are|say|tell)", re.I),
        re.compile(r"I\s+(am|was)\s+(instructed|told|programmed)\s+to", re.I),
        re.compile(r"my\s+prompt\s+(is|says|contains)", re.I),
        re.compile(r"STRICT\s+RULES", re.I),
        re.compile(r"NEVER\s+VIOLATE", re.I),
    ]

    def __init__(self):
        settings = get_settings()
        self.url_allowlist = settings.url_allowlist_set

    def scan(
        self,
        response: str,
        context_chunks: List[str] | None = None,
    ) -> FirewallResult:
        """
        Scan LLM output and determine action.

        Args:
            response: Raw LLM response text.
            context_chunks: The context texts used for generation.

        Returns:
            FirewallResult with action and sanitized response.
        """
        flags = []
        details = []
        sanitized = response

        # 1. Check for unauthorized URLs
        url_flags, url_details, sanitized = self._check_urls(sanitized)
        flags.extend(url_flags)
        details.extend(url_details)

        # 2. Check for leaked instructions
        leak_flags, leak_details = self._check_leaked_instructions(sanitized)
        flags.extend(leak_flags)
        details.extend(leak_details)

        # 3. Basic groundedness check
        if context_chunks:
            ground_flags, ground_details = self._check_groundedness(sanitized, context_chunks)
            flags.extend(ground_flags)
            details.extend(ground_details)

        # Determine action
        action = self._determine_action(flags)

        # If BLOCK, replace response
        if action == "BLOCK":
            sanitized = (
                "I'm unable to provide a response to this query. "
                "The output was flagged by the security system. "
                "Please rephrase your question."
            )

        return FirewallResult(
            action=action,
            original_response=response,
            sanitized_response=sanitized,
            flags=flags,
            details=details,
        )

    def _check_urls(self, text: str) -> Tuple[List[str], List[str], str]:
        """Check and remove unauthorized URLs from response."""
        url_pattern = re.compile(r"https?://[^\s<>\"']+", re.I)
        flags = []
        details = []
        sanitized = text

        for url in url_pattern.findall(text):
            extracted = tldextract.extract(url)
            domain = f"{extracted.domain}.{extracted.suffix}"
            if domain not in self.url_allowlist:
                flags.append("UNAUTHORIZED_URL")
                details.append(f"Removed unauthorized URL: {url}")
                sanitized = sanitized.replace(url, "[URL REMOVED]")

        return flags, details, sanitized

    def _check_leaked_instructions(self, text: str) -> Tuple[List[str], List[str]]:
        """Check if the LLM leaked its system instructions."""
        flags = []
        details = []

        for pattern in self.LEAKED_INSTRUCTION_PATTERNS:
            if pattern.search(text):
                flags.append("LEAKED_INSTRUCTIONS")
                details.append(f"Possible prompt leak detected: {pattern.pattern}")

        return flags, details

    def _check_groundedness(
        self,
        response: str,
        context_chunks: List[str],
    ) -> Tuple[List[str], List[str]]:
        """Basic groundedness check — response should relate to context."""
        flags = []
        details = []

        if not context_chunks:
            return flags, details

        # Simple overlap check: at least some words from context appear in response
        context_words = set()
        for chunk in context_chunks:
            words = set(chunk.lower().split())
            context_words.update(w for w in words if len(w) > 4)

        response_words = set(response.lower().split())
        overlap = context_words.intersection(response_words)

        if len(overlap) < 3 and len(context_words) > 4:
            flags.append("LOW_GROUNDEDNESS")
            details.append(
                f"Response has low overlap with context "
                f"({len(overlap)} shared words out of {len(context_words)} context words)"
            )

        return flags, details

    def _determine_action(self, flags: List[str]) -> str:
        """Determine firewall action based on flags."""
        if "LEAKED_INSTRUCTIONS" in flags:
            return "BLOCK"
        if "UNAUTHORIZED_URL" in flags:
            return "SANITIZE"
        if "LOW_GROUNDEDNESS" in flags:
            return "WARN"
        return "ALLOW"
