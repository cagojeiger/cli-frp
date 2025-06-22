"""FRP Python Wrapper - A self-hostable tunneling solution."""

# High-level API
from . import (
    core,  # For test access to core.client, core.config, etc.
    tunnels,  # For test access to tunnels.manager, etc.
)
from .api import create_tcp_tunnel, create_tunnel

# Common utilities
from .common.exceptions import (
    AuthenticationError,
    BinaryNotFoundError,
    ConnectionError,
    FRPWrapperError,
    ProcessError,
)
from .common.logging import get_logger, setup_logging
from .common.utils import (
    mask_sensitive_data,
    sanitize_log_data,
    validate_non_empty_string,
    validate_port,
)

# Core functionality
from .core.client import FRPClient
from .core.config import ConfigBuilder

# Tunnel management
from .tunnels.manager import TunnelManager
from .tunnels.models import (
    BaseTunnel,
    HTTPTunnel,
    TCPTunnel,
    TunnelConfig,
    TunnelStatus,
    TunnelType,
)
from .tunnels.process import TunnelProcessManager

# Setup logging on package initialization
setup_logging(level="INFO")

# Package level logger
logger = get_logger(__name__)

__version__ = "0.1.0"

client = core.client
config = core.config
tunnel_manager = tunnels.manager
tunnel_process = tunnels.process

__all__ = [
    # High-level API
    "create_tunnel",
    "create_tcp_tunnel",
    # Core client functionality
    "FRPClient",
    "ConfigBuilder",
    # Tunnel management
    "TunnelManager",
    "TunnelProcessManager",
    "TunnelConfig",
    "BaseTunnel",
    "HTTPTunnel",
    "TCPTunnel",
    "TunnelStatus",
    "TunnelType",
    # Exceptions
    "FRPWrapperError",
    "BinaryNotFoundError",
    "ConnectionError",
    "AuthenticationError",
    "ProcessError",
    # Utilities
    "get_logger",
    "setup_logging",
    "validate_port",
    "validate_non_empty_string",
    "mask_sensitive_data",
    "sanitize_log_data",
    "core",
    "tunnels",
    "client",
    "config",
    "tunnel_manager",
    "tunnel_process",
]
