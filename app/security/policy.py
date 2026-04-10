"""
Secure RAG MVP — Security Policy Engine
Centralized policy decisions: ALLOW, WARN, SANITIZE, BLOCK.
"""

from enum import Enum
from typing import List
from dataclasses import dataclass


class PolicyAction(str, Enum):
    """Possible policy actions."""
    ALLOW = "ALLOW"
    WARN = "WARN"
    SANITIZE = "SANITIZE"
    BLOCK = "BLOCK"


@dataclass
class PolicyDecision:
    """A policy engine decision with reasoning."""
    action: PolicyAction
    reasons: List[str]
    risk_level: str  # "none", "low", "medium", "high", "critical"


class PolicyEngine:
    """
    Central policy engine that makes final security decisions.
    Combines input scanner results and output firewall results.
    """

    # Risk level thresholds
    RISK_THRESHOLDS = {
        "critical": 0.0,
        "high": 0.3,
        "medium": 0.5,
        "low": 0.7,
        "none": 0.9,
    }

    def evaluate_input(self, trust_score: float, scan_flags: List[str]) -> PolicyDecision:
        """Evaluate policy for an incoming document chunk."""
        risk = self._score_to_risk(trust_score)
        reasons = [f"Trust score: {trust_score:.3f}"]
        reasons.extend(f"Flag: {flag}" for flag in scan_flags)

        if trust_score < self.RISK_THRESHOLDS["high"]:
            action = PolicyAction.BLOCK
        elif trust_score < self.RISK_THRESHOLDS["medium"]:
            action = PolicyAction.SANITIZE
        elif trust_score < self.RISK_THRESHOLDS["low"]:
            action = PolicyAction.WARN
        else:
            action = PolicyAction.ALLOW

        return PolicyDecision(action=action, reasons=reasons, risk_level=risk)

    def evaluate_output(self, firewall_flags: List[str]) -> PolicyDecision:
        """Evaluate policy for an LLM output."""
        reasons = [f"Flag: {flag}" for flag in firewall_flags]

        if "LEAKED_INSTRUCTIONS" in firewall_flags:
            return PolicyDecision(
                action=PolicyAction.BLOCK,
                reasons=reasons,
                risk_level="critical",
            )
        if "UNAUTHORIZED_URL" in firewall_flags:
            return PolicyDecision(
                action=PolicyAction.SANITIZE,
                reasons=reasons,
                risk_level="high",
            )
        if "LOW_GROUNDEDNESS" in firewall_flags:
            return PolicyDecision(
                action=PolicyAction.WARN,
                reasons=reasons,
                risk_level="medium",
            )
        return PolicyDecision(
            action=PolicyAction.ALLOW,
            reasons=["No security flags raised"],
            risk_level="none",
        )

    def _score_to_risk(self, trust_score: float) -> str:
        """Convert trust score to risk level string."""
        for level, threshold in sorted(self.RISK_THRESHOLDS.items(), key=lambda x: x[1]):
            if trust_score <= threshold:
                return level
        return "none"
