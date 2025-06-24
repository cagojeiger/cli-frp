"""FRP Python Wrapper - A self-hostable tunneling solution."""

# High-level API
from . import (
    core,  # For test access to core.client, core.config, etc.
    server,  # For test access to server components
    tunnels,  # For test access to tunnels.manager, etc.
)
from .api import (
    create_tcp_tunnel,
    create_tunnel,
    managed_tcp_tunnel,
    managed_tunnel,
    tunnel_group_context,
)

# Context management
from .common.context import (
    AsyncProcessManager,
    NestedContextManager,
    TimeoutContext,
    timeout_context,
)
from .common.context_config import (
    CleanupStrategy,
    ContextConfig,
    TunnelGroupConfig,
)

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

# Server components
from .server.server import FRPServer
from .tunnels.group import TunnelGroup, tunnel_group

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
    "managed_tunnel",
    "managed_tcp_tunnel",
    "tunnel_group_context",
    # Core client functionality
    "FRPClient",
    "ConfigBuilder",
    # Server functionality
    "FRPServer",
    # Tunnel management
    "TunnelManager",
    "TunnelProcessManager",
    "TunnelConfig",
    "BaseTunnel",
    "HTTPTunnel",
    "TCPTunnel",
    "TunnelStatus",
    "TunnelType",
    "TunnelGroup",
    "tunnel_group",
    # Context management
    "NestedContextManager",
    "TimeoutContext",
    "timeout_context",
    "AsyncProcessManager",
    "ContextConfig",
    "TunnelGroupConfig",
    "CleanupStrategy",
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
    "server",
    "tunnels",
    "client",
    "config",
    "tunnel_manager",
    "tunnel_process",
]
