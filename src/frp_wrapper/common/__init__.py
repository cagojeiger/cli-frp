"""Common utilities and shared functionality."""

from .exceptions import (
    AuthenticationError,
    BinaryNotFoundError,
    ConnectionError,
    FRPWrapperError,
    ProcessError,
)
from .logging import get_logger, setup_logging
from .process import ProcessManager
from .utils import (
    MAX_PORT,
    MIN_PORT,
    mask_sensitive_data,
    normalize_path_slashes,
    safe_get_dict_value,
    sanitize_log_data,
    validate_non_empty_string,
    validate_port,
)

__all__ = [
    # Process management
    "ProcessManager",
    # Exceptions
    "FRPWrapperError",
    "BinaryNotFoundError",
    "ConnectionError",
    "AuthenticationError",
    "ProcessError",
    # Logging
    "get_logger",
    "setup_logging",
    # Utils
    "validate_port",
    "validate_non_empty_string",
    "mask_sensitive_data",
    "sanitize_log_data",
    "safe_get_dict_value",
    "normalize_path_slashes",
    "MIN_PORT",
    "MAX_PORT",
]
