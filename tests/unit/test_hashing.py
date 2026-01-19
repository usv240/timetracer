"""Tests for hashing utilities."""

from timetracer.utils.hashing import hash_body, hash_string, short_hash


class TestHashBody:
    """Tests for body hashing."""

    def test_string_hash(self):
        """String input should produce consistent hash."""
        result = hash_body("hello world")

        assert result.startswith("sha256:")
        assert len(result) == 7 + 64  # "sha256:" + 64 hex chars

    def test_bytes_hash(self):
        """Bytes input should produce consistent hash."""
        result = hash_body(b"hello world")

        assert result.startswith("sha256:")

    def test_dict_hash(self):
        """Dict input should produce consistent hash."""
        result = hash_body({"key": "value"})

        assert result.startswith("sha256:")

    def test_consistency(self):
        """Same input should produce same hash."""
        hash1 = hash_body("test data")
        hash2 = hash_body("test data")

        assert hash1 == hash2

    def test_different_inputs(self):
        """Different inputs should produce different hashes."""
        hash1 = hash_body("data1")
        hash2 = hash_body("data2")

        assert hash1 != hash2

    def test_none_input(self):
        """None input should return special hash."""
        result = hash_body(None)

        assert result == "sha256:none"

    def test_dict_order_independent(self):
        """Dict hash should be order-independent due to sort_keys."""
        hash1 = hash_body({"b": 2, "a": 1})
        hash2 = hash_body({"a": 1, "b": 2})

        assert hash1 == hash2


class TestHashString:
    """Tests for string hashing."""

    def test_produces_hash(self):
        """Should produce sha256 hash."""
        result = hash_string("test")

        assert result.startswith("sha256:")

    def test_consistency(self):
        """Same string should produce same hash."""
        assert hash_string("hello") == hash_string("hello")


class TestShortHash:
    """Tests for short hash."""

    def test_default_length(self):
        """Default length should be 8."""
        result = short_hash("test data")

        assert len(result) == 8

    def test_custom_length(self):
        """Custom length should be respected."""
        result = short_hash("test data", length=4)

        assert len(result) == 4

    def test_no_prefix(self):
        """Short hash should not have sha256 prefix."""
        result = short_hash("test")

        assert not result.startswith("sha256")
