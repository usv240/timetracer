"""Tests for signature matching."""

import pytest
from timetracer.replay.matching import (
    normalize_url,
    normalize_query,
    signatures_match,
    create_signature_summary,
)
from timetracer.types import EventSignature


class TestNormalizeUrl:
    """Tests for URL normalization."""
    
    def test_removes_query_string(self):
        """Query string should be removed."""
        result = normalize_url("https://api.example.com/path?foo=bar")
        
        assert result == "https://api.example.com/path"
    
    def test_preserves_scheme_host_path(self):
        """Scheme, host, and path should be preserved."""
        result = normalize_url("https://api.example.com/v1/users")
        
        assert result == "https://api.example.com/v1/users"
    
    def test_handles_no_path(self):
        """URL with no path should work."""
        result = normalize_url("https://api.example.com")
        
        assert result == "https://api.example.com"


class TestNormalizeQuery:
    """Tests for query normalization."""
    
    def test_parses_query_string(self):
        """Query string should be parsed to dict."""
        result = normalize_query("foo=bar&baz=qux")
        
        assert result == {"foo": "bar", "baz": "qux"}
    
    def test_sorted_keys(self):
        """Keys should be sorted."""
        result = normalize_query("z=1&a=2")
        
        assert list(result.keys()) == ["a", "z"]
    
    def test_multi_value(self):
        """Multi-value params should become sorted list."""
        result = normalize_query("foo=b&foo=a")
        
        assert result["foo"] == ["a", "b"]


class TestSignaturesMatch:
    """Tests for signature matching."""
    
    def test_match_same_signatures(self):
        """Identical signatures should match."""
        expected = EventSignature(
            lib="httpx",
            method="GET",
            url="https://api.example.com/users",
        )
        actual = {
            "lib": "httpx",
            "method": "GET",
            "url": "https://api.example.com/users",
        }
        
        matches, errors = signatures_match(expected, actual)
        
        assert matches is True
        assert errors == []
    
    def test_mismatch_method(self):
        """Different methods should not match."""
        expected = EventSignature(lib="httpx", method="GET", url="https://api.com")
        actual = {"method": "POST", "url": "https://api.com"}
        
        matches, errors = signatures_match(expected, actual)
        
        assert matches is False
        assert any("method" in e for e in errors)
    
    def test_mismatch_url(self):
        """Different URLs should not match."""
        expected = EventSignature(lib="httpx", method="GET", url="https://api.com/v1")
        actual = {"method": "GET", "url": "https://api.com/v2"}
        
        matches, errors = signatures_match(expected, actual)
        
        assert matches is False
        assert any("url" in e for e in errors)
    
    def test_body_hash_optional(self):
        """Body hash check should be optional."""
        expected = EventSignature(
            lib="httpx",
            method="POST",
            url="https://api.com",
            body_hash="sha256:abc123",
        )
        actual = {
            "method": "POST",
            "url": "https://api.com",
            "body_hash": "sha256:different",
        }
        
        # Without body check
        matches, _ = signatures_match(expected, actual, check_body_hash=False)
        assert matches is True
        
        # With body check
        matches, errors = signatures_match(expected, actual, check_body_hash=True)
        assert matches is False


class TestCreateSignatureSummary:
    """Tests for signature summary creation."""
    
    def test_basic_summary(self):
        """Basic signature should produce method + url."""
        sig = EventSignature(lib="httpx", method="GET", url="https://api.com/users")
        
        result = create_signature_summary(sig)
        
        assert "GET" in result
        assert "https://api.com/users" in result
    
    def test_with_query(self):
        """Query params should be mentioned."""
        sig = EventSignature(
            lib="httpx",
            method="GET",
            url="https://api.com",
            query={"page": "1", "limit": "10"},
        )
        
        result = create_signature_summary(sig)
        
        assert "2 params" in result
