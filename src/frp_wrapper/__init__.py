"""FRP Python Wrapper - A self-hostable tunneling solution."""

from .client import FRPClient
from .config import ConfigBuilder
from .logging import get_logger, setup_logging
from .tunnel import (
    BaseTunnel,
    HTTPTunnel,
    TCPTunnel,
    TunnelConfig,
    TunnelStatus,
    TunnelType,
)
from .tunnel_manager import TunnelManager

# Setup logging on package initialization
setup_logging(level="INFO")

# Package level logger
logger = get_logger(__name__)

__version__ = "0.1.0"

__all__ = [
    # Core client functionality
    "FRPClient",
    "ConfigBuilder",
    # Tunnel management (Checkpoint 3)
    "TunnelManager",
    "TunnelConfig",
    "BaseTunnel",
    "HTTPTunnel",
    "TCPTunnel",
    "TunnelStatus",
    "TunnelType",
    # Utilities
    "get_logger",
    "setup_logging",
]
