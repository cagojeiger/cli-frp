"""Utility functions for FRP wrapper."""

import re
from typing import Any

# Port range constants
MIN_PORT = 1
MAX_PORT = 65535


def validate_port(port: int, port_name: str = "Port") -> None:
    """Validate port number range.

    Args:
        port: Port number to validate
        port_name: Name of the port for error messages

    Raises:
        ValueError: If port is not in valid range (1-65535)
    """
    if not isinstance(port, int) or not (MIN_PORT <= port <= MAX_PORT):
        raise ValueError(f"{port_name} must be between {MIN_PORT} and {MAX_PORT}")


def validate_non_empty_string(value: str, field_name: str) -> str:
    """Validate that a string is not empty or only whitespace.

    Args:
        value: String value to validate
        field_name: Name of the field for error messages

    Returns:
        Stripped string value

    Raises:
        ValueError: If string is empty or only whitespace
    """
    if not value or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


def safe_get_dict_value(data: dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get value from dictionary with default.

    Args:
        data: Dictionary to get value from
        key: Key to look up
        default: Default value if key not found

    Returns:
        Value from dictionary or default
    """
    return data.get(key, default)


def normalize_path_slashes(path: str) -> str:
    """Normalize path by removing extra slashes and trailing slashes.

    Args:
        path: Path to normalize

    Returns:
        Normalized path
    """
    # Remove leading/trailing slashes and normalize multiple slashes
    path = path.strip("/")
    path = re.sub(r"/+", "/", path)
    return path


def mask_sensitive_data(
    value: str | None, mask_char: str = "*", show_chars: int = 4
) -> str:
    """Mask sensitive data for logging while preserving some characters for debugging.

    Args:
        value: Sensitive string to mask (e.g., auth token, password)
        mask_char: Character to use for masking
        show_chars: Number of characters to show at the end

    Returns:
        Masked string safe for logging
    """
    if not value:
        return "<None>"

    if len(value) <= show_chars:
        return mask_char * len(value)

    masked_length = len(value) - show_chars
    return mask_char * masked_length + value[-show_chars:]


def sanitize_log_data(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize dictionary data for safe logging by masking sensitive fields.

    Args:
        data: Dictionary potentially containing sensitive data

    Returns:
        Sanitized dictionary safe for logging
    """
    sensitive_fields = {
        "auth_token",
        "token",
        "password",
        "secret",
        "key",
        "api_key",
        "access_token",
        "refresh_token",
        "bearer_token",
    }

    sanitized = {}
    for key, value in data.items():
        if any(sensitive_field in key.lower() for sensitive_field in sensitive_fields):
            sanitized[key] = mask_sensitive_data(str(value) if value else None)
        else:
            sanitized[key] = value

    return sanitized
