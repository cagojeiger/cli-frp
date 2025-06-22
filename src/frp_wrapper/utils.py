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
