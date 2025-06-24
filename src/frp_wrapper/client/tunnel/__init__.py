"""Tunnel management module for FRP client.

This module provides backward compatibility by re-exporting all classes
from their new locations.
"""

# Models
# Config
from .config import TunnelConfig

# Exceptions
from .exceptions import TunnelManagerError, TunnelRegistryError

# Manager
from .manager import TunnelManager
from .models import BaseTunnel, HTTPTunnel, TCPTunnel, TunnelStatus, TunnelType

# Process management
from .process import TunnelProcessManager

# Registry
from .registry import TunnelRegistry

# Routing
from .routing import (
    PathConflict,
    PathConflictDetector,
    PathConflictType,
    PathPattern,
    PathValidator,
)

__all__ = [
    # Models
    "TunnelType",
    "TunnelStatus",
    "BaseTunnel",
    "HTTPTunnel",
    "TCPTunnel",
    "TunnelConfig",
    # Manager
    "TunnelManager",
    "TunnelRegistry",
    "TunnelRegistryError",
    "TunnelManagerError",
    "TunnelProcessManager",
    # Routing
    "PathConflictDetector",
    "PathValidator",
    "PathPattern",
    "PathConflict",
    "PathConflictType",
]
