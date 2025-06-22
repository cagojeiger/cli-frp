"""Custom exceptions for FRP wrapper."""


class FRPWrapperError(Exception):
    """Base exception for all FRP wrapper errors."""
    pass


class ProcessError(FRPWrapperError):
    """Raised when FRP process operations fail."""
    pass


class BinaryNotFoundError(FRPWrapperError):
    """Raised when FRP binary is not found or not executable."""
    pass


class ConfigurationError(FRPWrapperError):
    """Raised when configuration is invalid."""
    pass


class ConnectionError(FRPWrapperError):
    """Raised when connection to FRP server fails."""
    pass
