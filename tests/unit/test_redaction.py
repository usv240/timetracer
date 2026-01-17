"""Tests for redaction policies."""

import pytest
from timetracer.policies.redaction import (
    redact_headers,
    redact_headers_allowlist,
    redact_body,
    detect_pii,
    redact_pii_in_text,
)
from timetracer.constants import Redaction


class TestRedactHeaders:
    """Tests for header redaction."""

    def test_removes_authorization(self):
        """Authorization header should be removed."""
        headers = {
            "Authorization": "Bearer secret-token",
            "Content-Type": "application/json",
        }
        result = redact_headers(headers)

        assert "Authorization" not in result
        assert result["Content-Type"] == "application/json"

    def test_removes_cookie(self):
        """Cookie header should be removed."""
        headers = {
            "Cookie": "session=abc123",
            "Accept": "application/json",
        }
        result = redact_headers(headers)

        assert "Cookie" not in result
        assert result["Accept"] == "application/json"

    def test_removes_set_cookie(self):
        """Set-Cookie header should be removed."""
        headers = {"Set-Cookie": "session=abc123; Path=/"}
        result = redact_headers(headers)

        assert "Set-Cookie" not in result

    def test_case_insensitive(self):
        """Redaction should be case-insensitive."""
        headers = {
            "authorization": "Bearer token",
            "AUTHORIZATION": "Bearer token2",
            "Content-Type": "text/plain",
        }
        result = redact_headers(headers)

        assert "authorization" not in result
        assert "AUTHORIZATION" not in result
        assert result["Content-Type"] == "text/plain"

    def test_mask_mode(self):
        """Mask mode should replace instead of remove."""
        headers = {"Authorization": "Bearer secret"}
        result = redact_headers(headers, mode="mask")

        assert result["Authorization"] == Redaction.REDACTED_VALUE

    def test_additional_sensitive(self):
        """Additional sensitive headers should be removed."""
        headers = {
            "X-Custom-Secret": "secret123",
            "Content-Type": "application/json",
        }
        result = redact_headers(headers, additional_sensitive={"x-custom-secret"})

        assert "X-Custom-Secret" not in result

    def test_removes_new_sensitive_headers(self):
        """New sensitive headers from enhanced list should be removed."""
        headers = {
            "X-CSRF-Token": "abc123",
            "X-Refresh-Token": "refresh123",
            "Proxy-Authorization": "Basic xyz",
            "Content-Type": "application/json",
        }
        result = redact_headers(headers)

        assert "X-CSRF-Token" not in result
        assert "X-Refresh-Token" not in result
        assert "Proxy-Authorization" not in result
        assert result["Content-Type"] == "application/json"


class TestRedactHeadersAllowlist:
    """Tests for allowlist-based header redaction."""

    def test_keeps_only_allowed(self):
        """Only allowed headers should be kept."""
        headers = {
            "content-type": "application/json",
            "authorization": "Bearer secret",
            "x-secret": "hidden",
        }
        result = redact_headers_allowlist(headers, allowed=frozenset({"content-type"}))

        assert result == {"content-type": "application/json"}

    def test_empty_if_none_allowed(self):
        """Result should be empty if no headers match allowed list."""
        headers = {"x-secret": "value"}
        result = redact_headers_allowlist(headers, allowed=frozenset({"content-type"}))

        assert result == {}


class TestRedactBody:
    """Tests for body redaction."""

    def test_redacts_password(self):
        """Password keys should be redacted."""
        body = {"username": "john", "password": "secret123"}
        result = redact_body(body)

        assert result["username"] == "john"
        assert result["password"] == Redaction.REDACTED_VALUE

    def test_redacts_nested(self):
        """Nested sensitive keys should be redacted."""
        body = {
            "user": {
                "name": "john",
                "credentials": {
                    "password": "secret",
                    "api_key": "key123",
                }
            }
        }
        result = redact_body(body)

        assert result["user"]["name"] == "john"
        assert result["user"]["credentials"]["password"] == Redaction.REDACTED_VALUE
        assert result["user"]["credentials"]["api_key"] == Redaction.REDACTED_VALUE

    def test_redacts_in_list(self):
        """Sensitive keys in list items should be redacted."""
        body = [
            {"name": "user1", "token": "abc"},
            {"name": "user2", "token": "def"},
        ]
        result = redact_body(body)

        assert result[0]["name"] == "user1"
        assert result[0]["token"] == Redaction.REDACTED_VALUE
        assert result[1]["token"] == Redaction.REDACTED_VALUE

    def test_none_body(self):
        """None body should return None."""
        assert redact_body(None) is None

    def test_jwt_masked(self):
        """JWT tokens in values should be masked."""
        body = {"data": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"}
        result = redact_body(body)

        assert result["data"] == Redaction.REDACTED_VALUE

    def test_redacts_enhanced_keys(self):
        """Enhanced sensitive keys should be redacted."""
        body = {
            "user_ssn": "123-45-6789",
            "credit_card_number": "4111111111111111",
            "bank_account": "123456789",
            "phone_number": "555-123-4567",
            "email_address": "test@example.com",
            "name": "John Doe",  # Should NOT be redacted
        }
        result = redact_body(body)

        assert result["user_ssn"] == Redaction.REDACTED_VALUE
        assert result["credit_card_number"] == Redaction.REDACTED_VALUE
        assert result["bank_account"] == Redaction.REDACTED_VALUE
        assert result["phone_number"] == Redaction.REDACTED_VALUE
        assert result["email_address"] == Redaction.REDACTED_VALUE
        assert result["name"] == "John Doe"

    def test_redacts_healthcare_keys(self):
        """Healthcare (HIPAA) sensitive keys should be redacted."""
        body = {
            "patient_id": "P12345",
            "medical_record_number": "MRN-001",
            "diagnosis_code": "ICD-10-123",
            "insurance_id": "INS-999",
        }
        result = redact_body(body)

        assert result["patient_id"] == Redaction.REDACTED_VALUE
        assert result["medical_record_number"] == Redaction.REDACTED_VALUE
        assert result["diagnosis_code"] == Redaction.REDACTED_VALUE
        assert result["insurance_id"] == Redaction.REDACTED_VALUE

    def test_redacts_financial_keys(self):
        """Financial (PCI-DSS) sensitive keys should be redacted."""
        body = {
            "cvv": "123",
            "expiry_date": "12/25",
            "cardholder_name": "John Doe",
            "iban_number": "DE89370400440532013000",
        }
        result = redact_body(body)

        assert result["cvv"] == Redaction.REDACTED_VALUE
        assert result["expiry_date"] == Redaction.REDACTED_VALUE
        assert result["cardholder_name"] == Redaction.REDACTED_VALUE
        assert result["iban_number"] == Redaction.REDACTED_VALUE


class TestDetectPii:
    """Tests for PII pattern detection."""

    def test_detects_email(self):
        """Email addresses should be detected."""
        assert detect_pii("test@example.com") == "email"
        assert detect_pii("user.name+tag@domain.co.uk") == "email"

    def test_detects_phone(self):
        """Phone numbers should be detected."""
        assert detect_pii("555-123-4567") == "phone"
        assert detect_pii("(555) 123-4567") == "phone"
        assert detect_pii("+1-555-123-4567") == "phone"

    def test_detects_ssn(self):
        """Social Security Numbers should be detected."""
        # Note: SSN detection requires fullmatch on digits
        assert detect_pii("123-45-6789") == "ssn"
        assert detect_pii("123 45 6789") == "ssn"

    def test_detects_credit_card_with_luhn(self):
        """Valid credit card numbers (passing Luhn) should be detected."""
        # Valid Visa card number (passes Luhn)
        assert detect_pii("4111111111111111") == "credit_card"
        assert detect_pii("4111-1111-1111-1111") == "credit_card"

    def test_rejects_invalid_credit_card(self):
        """Invalid credit card numbers (failing Luhn) should not be detected as CC."""
        # Invalid number (fails Luhn)
        assert detect_pii("1234567890123456") != "credit_card"

    def test_detects_ipv4(self):
        """IPv4 addresses should be detected."""
        assert detect_pii("192.168.1.1") == "ipv4"
        assert detect_pii("10.0.0.1") == "ipv4"

    def test_detects_ipv6(self):
        """IPv6 addresses should be detected."""
        assert detect_pii("2001:0db8:85a3:0000:0000:8a2e:0370:7334") == "ipv6"

    def test_returns_none_for_normal_text(self):
        """Normal text should not trigger PII detection."""
        assert detect_pii("hello world") is None
        assert detect_pii("12345") is None  # Too short
        assert detect_pii("") is None


class TestRedactPiiInText:
    """Tests for redacting PII in unstructured text."""

    def test_redacts_email_in_text(self):
        """Emails in text should be redacted."""
        text = "Contact me at john.doe@example.com for more info."
        result = redact_pii_in_text(text)

        assert "john.doe@example.com" not in result
        assert "[REDACTED:EMAIL]" in result

    def test_redacts_ssn_in_text(self):
        """SSNs in text should be redacted."""
        text = "My SSN is 123-45-6789, please verify."
        result = redact_pii_in_text(text)

        assert "123-45-6789" not in result
        assert "[REDACTED:SSN]" in result

    def test_redacts_credit_card_in_text(self):
        """Valid credit cards in text should be redacted."""
        text = "Payment with card 4111-1111-1111-1111 was processed."
        result = redact_pii_in_text(text)

        assert "4111-1111-1111-1111" not in result
        assert "[REDACTED:CREDIT_CARD]" in result

    def test_redacts_phone_in_text(self):
        """Phone numbers in text should be redacted."""
        text = "Call us at (555) 123-4567 for support."
        result = redact_pii_in_text(text)

        assert "(555) 123-4567" not in result
        assert "[REDACTED:PHONE]" in result

    def test_redacts_ip_in_text(self):
        """IP addresses in text should be redacted."""
        text = "Request from 192.168.1.100 was blocked."
        result = redact_pii_in_text(text)

        assert "192.168.1.100" not in result
        assert "[REDACTED:IP]" in result

    def test_preserves_normal_text(self):
        """Text without PII should be preserved."""
        text = "Hello, how are you today?"
        result = redact_pii_in_text(text)

        assert result == text

    def test_multiple_pii_types(self):
        """Multiple PII types in same text should all be redacted."""
        text = "User john@example.com called from 555-123-4567 with IP 10.0.0.1"
        result = redact_pii_in_text(text)

        assert "[REDACTED:EMAIL]" in result
        assert "[REDACTED:PHONE]" in result
        assert "[REDACTED:IP]" in result

