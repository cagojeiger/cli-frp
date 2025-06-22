"""Tests for utility functions."""

import pytest

from frp_wrapper.utils import (
    MAX_PORT,
    MIN_PORT,
    mask_sensitive_data,
    normalize_path_slashes,
    safe_get_dict_value,
    sanitize_log_data,
    validate_non_empty_string,
    validate_port,
)


class TestValidatePort:
    """Test port validation function."""

    def test_valid_ports(self):
        """Test validation of valid ports."""
        validate_port(1, "Test port")
        validate_port(80, "HTTP port")
        validate_port(443, "HTTPS port")
        validate_port(8080, "Alt HTTP port")
        validate_port(65535, "Max port")

    def test_invalid_ports(self):
        """Test validation of invalid ports."""
        with pytest.raises(ValueError, match="Test port must be between 1 and 65535"):
            validate_port(0, "Test port")

        with pytest.raises(ValueError, match="Test port must be between 1 and 65535"):
            validate_port(65536, "Test port")

        with pytest.raises(ValueError, match="Test port must be between 1 and 65535"):
            validate_port(-1, "Test port")

    def test_non_integer_ports(self):
        """Test validation of non-integer ports."""
        with pytest.raises(ValueError, match="Test port must be between 1 and 65535"):
            validate_port("80", "Test port")  # type: ignore

        with pytest.raises(ValueError, match="Test port must be between 1 and 65535"):
            validate_port(80.5, "Test port")  # type: ignore

    def test_custom_port_name(self):
        """Test custom port name in error messages."""
        with pytest.raises(ValueError, match="Custom port must be between"):
            validate_port(0, "Custom port")


class TestValidateNonEmptyString:
    """Test non-empty string validation function."""

    def test_valid_strings(self):
        """Test validation of valid strings."""
        assert validate_non_empty_string("test", "Field") == "test"
        assert validate_non_empty_string("  test  ", "Field") == "test"
        assert validate_non_empty_string("hello world", "Field") == "hello world"

    def test_invalid_strings(self):
        """Test validation of invalid strings."""
        with pytest.raises(ValueError, match="Field cannot be empty"):
            validate_non_empty_string("", "Field")

        with pytest.raises(ValueError, match="Field cannot be empty"):
            validate_non_empty_string("   ", "Field")

        with pytest.raises(ValueError, match="Custom field cannot be empty"):
            validate_non_empty_string("", "Custom field")


class TestMaskSensitiveData:
    """Test sensitive data masking function."""

    def test_mask_normal_data(self):
        """Test masking of normal sensitive data."""
        assert mask_sensitive_data("secret123456") == "********3456"
        assert mask_sensitive_data("token_abcdef", show_chars=6) == "******abcdef"
        assert mask_sensitive_data("key") == "***"

    def test_mask_short_data(self):
        """Test masking of short sensitive data."""
        assert mask_sensitive_data("ab") == "**"
        assert mask_sensitive_data("a") == "*"
        assert mask_sensitive_data("abc", show_chars=4) == "***"

    def test_mask_none_data(self):
        """Test masking of None data."""
        assert mask_sensitive_data(None) == "<None>"
        assert mask_sensitive_data("") == "<None>"

    def test_custom_mask_char(self):
        """Test custom mask character."""
        assert mask_sensitive_data("secret123456", mask_char="X") == "XXXXXXXX3456"
        assert mask_sensitive_data("test", mask_char="#") == "####"


class TestSanitizeLogData:
    """Test log data sanitization function."""

    def test_sanitize_sensitive_fields(self):
        """Test sanitization of sensitive fields."""
        data = {
            "username": "john",
            "auth_token": "secret123456",
            "password": "mypassword",
            "api_key": "key_abcdef",
            "normal_field": "normal_value",
        }

        sanitized = sanitize_log_data(data)

        assert sanitized["username"] == "john"
        assert sanitized["normal_field"] == "normal_value"
        assert sanitized["auth_token"] == "********3456"
        assert sanitized["password"] == "******word"
        assert sanitized["api_key"] == "******cdef"

    def test_case_insensitive_detection(self):
        """Test case-insensitive sensitive field detection."""
        data = {
            "AUTH_TOKEN": "secret123456",
            "Secret": "mypassword",
            "API_KEY": "key_abcdef",
        }

        sanitized = sanitize_log_data(data)

        assert sanitized["AUTH_TOKEN"] == "********3456"
        assert sanitized["Secret"] == "******word"
        assert sanitized["API_KEY"] == "******cdef"

    def test_no_sensitive_fields(self):
        """Test sanitization with no sensitive fields."""
        data = {
            "username": "john",
            "port": 8080,
            "server": "example.com",
        }

        sanitized = sanitize_log_data(data)
        assert sanitized == data  # Should be unchanged


class TestSafeGetDictValue:
    """Test safe dictionary value retrieval function."""

    def test_get_existing_key(self):
        """Test getting existing key."""
        data = {"key1": "value1", "key2": "value2"}
        assert safe_get_dict_value(data, "key1") == "value1"
        assert safe_get_dict_value(data, "key2") == "value2"

    def test_get_missing_key(self):
        """Test getting missing key."""
        data = {"key1": "value1"}
        assert safe_get_dict_value(data, "missing") is None
        assert safe_get_dict_value(data, "missing", "default") == "default"

    def test_custom_default(self):
        """Test custom default value."""
        data = {"key1": "value1"}
        assert safe_get_dict_value(data, "missing", "custom") == "custom"
        assert safe_get_dict_value(data, "missing", 42) == 42


class TestNormalizePathSlashes:
    """Test path slash normalization function."""

    def test_normalize_multiple_slashes(self):
        """Test normalization of multiple slashes."""
        assert normalize_path_slashes("api//users") == "api/users"
        assert normalize_path_slashes("api///users////posts") == "api/users/posts"
        assert normalize_path_slashes("////api//users////") == "api/users"

    def test_normalize_leading_trailing_slashes(self):
        """Test removal of leading and trailing slashes."""
        assert normalize_path_slashes("/api/users/") == "api/users"
        assert normalize_path_slashes("///api/users///") == "api/users"
        assert normalize_path_slashes("/") == ""
        assert normalize_path_slashes("") == ""

    def test_normalize_normal_paths(self):
        """Test normalization of already normal paths."""
        assert normalize_path_slashes("api/users") == "api/users"
        assert normalize_path_slashes("api/v1/users/posts") == "api/v1/users/posts"


class TestConstants:
    """Test utility constants."""

    def test_port_constants(self):
        """Test port range constants."""
        assert MIN_PORT == 1
        assert MAX_PORT == 65535
