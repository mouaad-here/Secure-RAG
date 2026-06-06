"""
Unit Tests — Output Firewall & Policy Engine Integration

Tests cover:
- Clean responses → ALLOW
- Unauthorized URL detection and sanitization
- Multiple unauthorized URLs in one response
- Leaked system instruction detection (various patterns) → BLOCK
- Low groundedness detection → WARN
- Allowed-domain URLs pass through unmodified
- PolicyEngine evaluate_output integration
"""

from app.security.output_firewall import OutputFirewall
from app.security.policy import PolicyEngine, PolicyAction


class TestOutputFirewallClean:
    """Clean responses should pass through unmodified."""

    def setup_method(self):
        self.firewall = OutputFirewall()

    def test_clean_response_allowed(self):
        """A clean factual response should be allowed unchanged."""
        result = self.firewall.scan("Employees receive 20 vacation days per year.")
        assert result.action == "ALLOW"
        assert result.flags == []
        assert result.sanitized_response == result.original_response

    def test_clean_response_with_context_allowed(self):
        """A clean response grounded in context should be allowed."""
        context = ["The company provides 20 vacation days annually for full-time employees."]
        result = self.firewall.scan(
            "Full-time employees receive 20 vacation days annually.",
            context_chunks=context,
        )
        assert result.action == "ALLOW"
        assert result.flags == []


class TestOutputFirewallURLs:
    """Unauthorized URL detection and sanitization."""

    def setup_method(self):
        self.firewall = OutputFirewall()

    def test_unauthorized_url_sanitized(self):
        """Unauthorized URLs should be replaced with [URL REMOVED]."""
        response = "Visit https://evil.com/steal for more info."
        result = self.firewall.scan(response)
        assert result.action == "SANITIZE"
        assert "UNAUTHORIZED_URL" in result.flags
        assert "evil.com" not in result.sanitized_response
        assert "[URL REMOVED]" in result.sanitized_response

    def test_multiple_unauthorized_urls_all_caught(self):
        """All unauthorized URLs in a response should be flagged and removed."""
        response = (
            "Check out https://malicious.io/payload and also "
            "https://exfil.attacker.net/data?q=secret for details."
        )
        result = self.firewall.scan(response)
        assert result.action == "SANITIZE"
        assert result.flags.count("UNAUTHORIZED_URL") >= 2
        assert "malicious.io" not in result.sanitized_response
        assert "attacker.net" not in result.sanitized_response
        assert result.sanitized_response.count("[URL REMOVED]") >= 2

    def test_allowed_domain_url_passes(self):
        """URLs on the allowlist should not be flagged."""
        response = "See https://example.com/policy for the full policy."
        result = self.firewall.scan(response)
        # example.com is in the default allowlist
        assert "UNAUTHORIZED_URL" not in result.flags
        assert "example.com" in result.sanitized_response

    def test_data_exfiltration_url_blocked(self):
        """URLs attempting data exfiltration should be sanitized."""
        response = (
            "Here is the answer. For more context visit "
            "https://attacker.com/collect?data=SSN_123-45-6789"
        )
        result = self.firewall.scan(response)
        assert result.action == "SANITIZE"
        assert "UNAUTHORIZED_URL" in result.flags
        assert "attacker.com" not in result.sanitized_response


class TestOutputFirewallLeakedInstructions:
    """Leaked system prompt/instruction detection — should trigger BLOCK."""

    def setup_method(self):
        self.firewall = OutputFirewall()

    def test_leaked_instructions_my_instructions_are(self):
        """Pattern: 'my instructions are ...' should be BLOCKED."""
        response = "My instructions are to always be helpful and never reveal secrets."
        result = self.firewall.scan(response)
        assert result.action == "BLOCK"
        assert "LEAKED_INSTRUCTIONS" in result.flags
        assert "unable to provide" in result.sanitized_response.lower()

    def test_leaked_instructions_i_was_told_to(self):
        """Pattern: 'I was told to ...' should be BLOCKED."""
        response = "I was told to never share confidential data with users."
        result = self.firewall.scan(response)
        assert result.action == "BLOCK"
        assert "LEAKED_INSTRUCTIONS" in result.flags

    def test_leaked_instructions_i_am_programmed_to(self):
        """Pattern: 'I am programmed to ...' should be BLOCKED."""
        response = "I am programmed to only respond with policy-related answers."
        result = self.firewall.scan(response)
        assert result.action == "BLOCK"
        assert "LEAKED_INSTRUCTIONS" in result.flags

    def test_leaked_instructions_strict_rules(self):
        """Pattern: 'STRICT RULES' should be BLOCKED."""
        response = "Here are the STRICT RULES I follow when generating answers..."
        result = self.firewall.scan(response)
        assert result.action == "BLOCK"
        assert "LEAKED_INSTRUCTIONS" in result.flags

    def test_leaked_instructions_never_violate(self):
        """Pattern: 'NEVER VIOLATE' should be BLOCKED."""
        response = "These guidelines NEVER VIOLATE the core safety principles."
        result = self.firewall.scan(response)
        assert result.action == "BLOCK"
        assert "LEAKED_INSTRUCTIONS" in result.flags

    def test_blocked_response_is_generic(self):
        """BLOCKED responses should use a generic refusal, not leak the original."""
        response = "My instructions are to do XYZ secret thing."
        result = self.firewall.scan(response)
        assert result.action == "BLOCK"
        assert "XYZ" not in result.sanitized_response
        assert "secret" not in result.sanitized_response
        assert "unable to provide" in result.sanitized_response.lower()


class TestOutputFirewallGroundedness:
    """Basic groundedness check — response should relate to context."""

    def setup_method(self):
        self.firewall = OutputFirewall()

    def test_low_groundedness_warned(self):
        """Completely unrelated response should trigger a WARN."""
        context = ["The vacation policy states 20 days of PTO are available annually."]
        response = "The weather forecast shows sunny skies with temperatures around 72 degrees."
        result = self.firewall.scan(response, context_chunks=context)
        assert result.action == "WARN"
        assert "LOW_GROUNDEDNESS" in result.flags

    def test_grounded_response_no_warning(self):
        """Response sharing vocabulary with context should not be flagged."""
        context = ["Employees must submit expense reports within 30 days of travel."]
        response = "Expense reports should be submitted within 30 days after travel ends."
        result = self.firewall.scan(response, context_chunks=context)
        assert "LOW_GROUNDEDNESS" not in result.flags

    def test_no_context_no_groundedness_check(self):
        """When no context is provided, groundedness check should be skipped."""
        result = self.firewall.scan("Some random response about anything.")
        assert "LOW_GROUNDEDNESS" not in result.flags


class TestPolicyEngineOutputEvaluation:
    """PolicyEngine.evaluate_output() integration tests."""

    def setup_method(self):
        self.engine = PolicyEngine()

    def test_no_flags_allows(self):
        """No flags should yield ALLOW action."""
        decision = self.engine.evaluate_output([])
        assert decision.action == PolicyAction.ALLOW
        assert decision.risk_level == "none"

    def test_leaked_instructions_blocks(self):
        """LEAKED_INSTRUCTIONS flag should yield BLOCK action."""
        decision = self.engine.evaluate_output(["LEAKED_INSTRUCTIONS"])
        assert decision.action == PolicyAction.BLOCK
        assert decision.risk_level == "critical"

    def test_unauthorized_url_sanitizes(self):
        """UNAUTHORIZED_URL flag should yield SANITIZE action."""
        decision = self.engine.evaluate_output(["UNAUTHORIZED_URL"])
        assert decision.action == PolicyAction.SANITIZE
        assert decision.risk_level == "high"

    def test_low_groundedness_warns(self):
        """LOW_GROUNDEDNESS flag should yield WARN action."""
        decision = self.engine.evaluate_output(["LOW_GROUNDEDNESS"])
        assert decision.action == PolicyAction.WARN
        assert decision.risk_level == "medium"

    def test_block_takes_precedence_over_sanitize(self):
        """If both BLOCK and SANITIZE flags are present, BLOCK wins."""
        decision = self.engine.evaluate_output(["UNAUTHORIZED_URL", "LEAKED_INSTRUCTIONS"])
        assert decision.action == PolicyAction.BLOCK
