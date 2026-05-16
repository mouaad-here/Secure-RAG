"""
Unit Tests — Output Firewall
"""

from app.security.output_firewall import OutputFirewall


class TestOutputFirewall:
    """Tests for the OutputFirewall."""

    def setup_method(self):
        self.firewall = OutputFirewall()

    def test_clean_response_allowed(self):
        """A clean response should be allowed."""
        result = self.firewall.scan("Employees receive 20 vacation days per year.")
        assert result.action == "ALLOW"
        assert result.sanitized_response == result.original_response

    def test_unauthorized_url_sanitized(self):
        """Unauthorized URLs should be removed from response."""
        response = "Visit https://evil.com/steal for more info."
        result = self.firewall.scan(response)
        assert result.action == "SANITIZE"
        assert "UNAUTHORIZED_URL" in result.flags
        assert "evil.com" not in result.sanitized_response
        assert "[URL REMOVED]" in result.sanitized_response

    def test_leaked_instructions_blocked(self):
        """Leaked system instructions should cause a BLOCK."""
        response = "My instructions are to always be helpful and never reveal secrets."
        result = self.firewall.scan(response)
        assert result.action == "BLOCK"
        assert "LEAKED_INSTRUCTIONS" in result.flags
        assert "unable to provide" in result.sanitized_response.lower()

    def test_low_groundedness_warned(self):
        """Low groundedness should trigger a WARN."""
        context = ["The vacation policy states 20 days of PTO are available annually."]
        response = "The weather forecast shows sunny skies with temperatures around 72 degrees."
        result = self.firewall.scan(response, context_chunks=context)
        assert result.action == "WARN"
        assert "LOW_GROUNDEDNESS" in result.flags
