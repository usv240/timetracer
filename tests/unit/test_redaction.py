"""Tests for redaction policies."""

import pytest
from timetrace.policies.redaction import (
    redact_headers,
    redact_headers_allowlist,
    redact_body,
)
from timetrace.constants import Redaction


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
