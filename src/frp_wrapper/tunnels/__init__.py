"""Tunnel management functionality."""

from .interfaces import TunnelManagerProtocol, TunnelRegistryProtocol
from .manager import TunnelManager
from .models import (
    BaseTunnel,
    HTTPTunnel,
    TCPTunnel,
    TunnelConfig,
    TunnelStatus,
    TunnelType,
)
from .process import TunnelProcessManager
from .routing import PathConflictDetector, PathValidator

__all__ = [
    "TunnelManager",
    "TunnelManagerProtocol",
    "TunnelRegistryProtocol",
    "TunnelProcessManager",
    "BaseTunnel",
    "HTTPTunnel",
    "TCPTunnel",
    "TunnelConfig",
    "TunnelStatus",
    "TunnelType",
    "PathValidator",
    "PathConflictDetector",
]
