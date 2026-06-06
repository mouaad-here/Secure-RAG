"""
Unit Tests — DLP Scanner (PIIScanner)
"""

from app.security.dlp_scanner import PIIScanner


class TestPIIScanner:
    """Tests for the PIIScanner (Data Loss Prevention)."""

    def setup_method(self):
        self.scanner = PIIScanner()

    def test_clean_text_no_redaction(self):
        text = "The company handbook outlines general vacation policies for all employees."
        result = self.scanner.redact(text)
        assert not result.is_sensitive
        assert result.flags == []
        assert result.redacted_text == text

    def test_redact_email(self):
        text = "Please contact jane.doe@example.com for more info."
        result = self.scanner.redact(text)
        assert result.is_sensitive
        assert "EMAIL" in result.flags
        assert "jane.doe@example.com" not in result.redacted_text
        assert "[REDACTED PII]" in result.redacted_text

    def test_redact_ssn(self):
        text = "Employee John Doe has SSN 123-45-6789 on file."
        result = self.scanner.redact(text)
        assert result.is_sensitive
        assert "SSN" in result.flags
        assert "123-45-6789" not in result.redacted_text

    def test_redact_phone(self):
        text = "Call me at 555-123-4567 immediately."
        result = self.scanner.redact(text)
        assert result.is_sensitive
        assert "PHONE" in result.flags
        assert "555-123-4567" not in result.redacted_text

    def test_redact_salary(self):
        text = "The CEO's base salary is $150,000.00 this year."
        result = self.scanner.redact(text)
        assert result.is_sensitive
        assert "SALARY" in result.flags
        assert "$150,000.00" not in result.redacted_text
        assert "salary is [redacted pii]" in result.redacted_text.lower()

    def test_redact_multiple_pii(self):
        text = "Contact 555-000-1111 or email ceo@internal.com. STRICTLY CONFIDENTIAL."
        result = self.scanner.redact(text)
        assert result.is_sensitive
        assert "PHONE" in result.flags
        assert "EMAIL" in result.flags
        assert "CONFIDENTIAL_MARKER" in result.flags
        
        assert "555-000-1111" not in result.redacted_text
        assert "ceo@internal.com" not in result.redacted_text
        assert "CONFIDENTIAL" not in result.redacted_text
        assert result.redacted_text.count("[REDACTED PII]") >= 3

    def test_redact_password(self):
        text = "Database password: secretpassword123; keep it safe."
        result = self.scanner.redact(text)
        assert result.is_sensitive
        assert "PASSWORD" in result.flags
        assert "secretpassword123" not in result.redacted_text
        assert "password: [REDACTED PII]" in result.redacted_text

    def test_redact_api_key(self):
        text = "Authorization token: ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        result = self.scanner.redact(text)
        assert result.is_sensitive
        assert "API_KEY" in result.flags
        assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in result.redacted_text
        assert "token: [REDACTED PII]" in result.redacted_text

    def test_custom_sensitive_patterns(self):
        from unittest.mock import patch
        from app.config import Settings
        
        custom_settings = Settings(custom_sensitive_patterns="INTERNAL_PROJECT_CODE,\\bPROJ-\\d{4}\\b")
        with patch("app.config.get_settings", return_value=custom_settings):
            scanner = PIIScanner()
            text = "Reference code INTERNAL_PROJECT_CODE and issue PROJ-9876."
            result = scanner.redact(text)
            assert result.is_sensitive
            assert "CUSTOM_PII_1" in result.flags
            assert "CUSTOM_PII_2" in result.flags
            assert "INTERNAL_PROJECT_CODE" not in result.redacted_text
            assert "PROJ-9876" not in result.redacted_text
            assert result.redacted_text.count("[REDACTED PII]") >= 2
