"""FRP Python Wrapper - A self-hostable tunneling solution."""

# High-level API
from . import (
    client,  # For test access to client components
    server,  # For test access to server components
)
from .api import (
    create_tcp_tunnel,
    create_tunnel,
    managed_tcp_tunnel,
    managed_tunnel,
    tunnel_group_context,
)

# Client functionality
from .client import (
    BaseTunnel,
    ConfigBuilder,
    FRPClient,
    HTTPTunnel,
    TCPTunnel,
    TunnelConfig,
    TunnelManager,
    TunnelStatus,
    TunnelType,
)
from .client.group import TunnelGroup, tunnel_group

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
from .common.process import ProcessManager
from .common.utils import (
    mask_sensitive_data,
    sanitize_log_data,
    validate_non_empty_string,
    validate_port,
)

# Server components
from .server.server import FRPServer

# Setup logging on package initialization
setup_logging(level="INFO")

# Package level logger
logger = get_logger(__name__)

__version__ = "0.1.0"


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
    "TunnelConfig",
    "BaseTunnel",
    "HTTPTunnel",
    "TCPTunnel",
    "TunnelStatus",
    "TunnelType",
    "TunnelGroup",
    "tunnel_group",
    "ProcessManager",
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
    "client",
    "server",
]
