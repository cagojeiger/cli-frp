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
from .tunnel_process import TunnelProcessManager
from .utils import (
    mask_sensitive_data,
    sanitize_log_data,
    validate_non_empty_string,
    validate_port,
)

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
    "TunnelProcessManager",
    "TunnelConfig",
    "BaseTunnel",
    "HTTPTunnel",
    "TCPTunnel",
    "TunnelStatus",
    "TunnelType",
    # Utilities
    "get_logger",
    "setup_logging",
    "validate_port",
    "validate_non_empty_string",
    "mask_sensitive_data",
    "sanitize_log_data",
]
