"""Custom exceptions for tunnel management."""

from ...common.exceptions import TunnelError


class TunnelRegistryError(TunnelError):
    """Exception raised for tunnel registry operations."""

    pass


class TunnelManagerError(TunnelError):
    """Exception raised for tunnel manager operations."""

    pass
