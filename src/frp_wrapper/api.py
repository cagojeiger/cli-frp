"""High-level API for FRP Python Wrapper.

This module provides simple, user-friendly functions for common tunneling tasks.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from .common.logging import get_logger
from .core.client import FRPClient
from .tunnels import TunnelConfig, TunnelManager
from .tunnels.group import TunnelGroup, TunnelGroupConfig

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


def create_tunnel(
    server: str,
    local_port: int,
    path: str,
    *,
    auth_token: str | None = None,
    domain: str | None = None,
    **kwargs: Any,
) -> str:
    """Create an HTTP tunnel with path-based routing.

    This is a simple wrapper that creates a tunnel and returns the public URL.

    Args:
        server: FRP server address
        local_port: Local port to expose
        path: URL path for routing (e.g., "/myapp")
        auth_token: Optional authentication token
        domain: Custom domain (uses server as domain if not specified)
        **kwargs: Additional tunnel configuration options

    Returns:
        str: The public URL for accessing the tunnel

    Example:
        >>> url = create_tunnel("example.com", 3000, "/myapp")
        >>> print(f"Your app is live at: {url}")
        https://example.com/myapp/
    """
    # Use server as domain if not specified
    if domain is None:
        domain = server

    # Create tunnel configuration
    config = TunnelConfig(
        server_host=server,
        auth_token=auth_token,
        default_domain=domain,
    )

    # Create and start tunnel manager
    manager = TunnelManager(config)

    # Create HTTP tunnel
    tunnel = manager.create_http_tunnel(
        tunnel_id=f"tunnel-{local_port}-{path.strip('/')}",
        local_port=local_port,
        path=path,
        custom_domains=[domain],
        **kwargs,
    )

    # Start the tunnel
    if not manager.start_tunnel(tunnel.id):
        raise RuntimeError(f"Failed to start tunnel for {path}")

    # Construct and return the URL
    url = f"https://{domain}{path}"
    if not path.endswith("/"):
        url += "/"

    logger.info("Tunnel created", url=url, local_port=local_port, path=path)

    return url


def create_tcp_tunnel(
    server: str,
    local_port: int,
    remote_port: int | None = None,
    *,
    auth_token: str | None = None,
) -> str:
    """Create a TCP tunnel.

    Args:
        server: FRP server address
        local_port: Local port to expose
        remote_port: Remote port on server (defaults to local_port)
        auth_token: Optional authentication token

    Returns:
        str: The server endpoint for accessing the tunnel

    Example:
        >>> endpoint = create_tcp_tunnel("example.com", 3306)
        >>> print(f"Database available at: {endpoint}")
        example.com:3306
    """
    if remote_port is None:
        remote_port = local_port

    # Create tunnel configuration
    config = TunnelConfig(
        server_host=server,
        auth_token=auth_token,
        default_domain=server,  # TCP tunnels don't use domains, but it's required
    )

    # Create and start tunnel manager
    manager = TunnelManager(config)

    # Create TCP tunnel
    tunnel = manager.create_tcp_tunnel(
        tunnel_id=f"tcp-{local_port}-{remote_port}",
        local_port=local_port,
        remote_port=remote_port,
    )

    # Start the tunnel
    if not manager.start_tunnel(tunnel.id):
        raise RuntimeError(f"Failed to start TCP tunnel on port {remote_port}")

    endpoint = f"{server}:{remote_port}"
    logger.info("TCP tunnel created", endpoint=endpoint, local_port=local_port)

    return endpoint


@contextmanager
def managed_tunnel(
    server: str,
    local_port: int,
    path: str,
    *,
    auth_token: str | None = None,
    domain: str | None = None,
    **kwargs: Any,
) -> Iterator[str]:
    """Create a managed HTTP tunnel with automatic cleanup.

    This context manager creates a tunnel and automatically cleans it up
    when exiting the context, even if an exception occurs.

    Args:
        server: FRP server address
        local_port: Local port to expose
        path: URL path for routing (e.g., "/myapp")
        auth_token: Optional authentication token
        domain: Custom domain (uses server as domain if not specified)
        **kwargs: Additional tunnel configuration options

    Yields:
        str: The public URL for accessing the tunnel

    Example:
        >>> with managed_tunnel("example.com", 3000, "/myapp") as url:
        ...     print(f"Your app is live at: {url}")
        ...     # Do something with the tunnel
        https://example.com/myapp/
        # Tunnel is automatically cleaned up here
    """
    # Use server as domain if not specified
    if domain is None:
        domain = server

    # Create FRP client with context management
    with FRPClient(server, auth_token=auth_token) as client:
        # Create and start tunnel
        client.expose_path(
            local_port=local_port,
            path=path.lstrip("/"),  # Remove leading slash
            custom_domains=[domain],
            auto_start=True,
            **kwargs,
        )

        # Construct the URL
        url = f"https://{domain}/{path.lstrip('/')}"
        if not path.endswith("/"):
            url += "/"

        logger.info("Managed tunnel created", url=url, local_port=local_port, path=path)

        try:
            yield url
        finally:
            # Cleanup is handled by FRPClient context manager
            logger.info("Managed tunnel cleaned up", url=url)


@contextmanager
def managed_tcp_tunnel(
    server: str,
    local_port: int,
    remote_port: int | None = None,
    *,
    auth_token: str | None = None,
) -> Iterator[str]:
    """Create a managed TCP tunnel with automatic cleanup.

    This context manager creates a TCP tunnel and automatically cleans it up
    when exiting the context, even if an exception occurs.

    Args:
        server: FRP server address
        local_port: Local port to expose
        remote_port: Remote port on server (defaults to local_port)
        auth_token: Optional authentication token

    Yields:
        str: The server endpoint for accessing the tunnel

    Example:
        >>> with managed_tcp_tunnel("example.com", 3306) as endpoint:
        ...     print(f"Database available at: {endpoint}")
        ...     # Use the database connection
        example.com:3306
        # Tunnel is automatically cleaned up here
    """
    if remote_port is None:
        remote_port = local_port

    # Create FRP client with context management
    with FRPClient(server, auth_token=auth_token) as client:
        # Create and start tunnel
        client.expose_tcp(
            local_port=local_port,
            remote_port=remote_port,
            auto_start=True,
        )

        endpoint = f"{server}:{remote_port}"
        logger.info(
            "Managed TCP tunnel created", endpoint=endpoint, local_port=local_port
        )

        try:
            yield endpoint
        finally:
            # Cleanup is handled by FRPClient context manager
            logger.info("Managed TCP tunnel cleaned up", endpoint=endpoint)


@contextmanager
def tunnel_group_context(
    server: str,
    *,
    auth_token: str | None = None,
    group_name: str = "default",
    max_tunnels: int = 10,
    **config_kwargs: Any,
) -> Iterator[TunnelGroup]:
    """Create a tunnel group context for managing multiple tunnels.

    This context manager creates an FRP client and tunnel group that can
    manage multiple tunnels with automatic cleanup.

    Args:
        server: FRP server address
        auth_token: Optional authentication token
        group_name: Name for the tunnel group
        max_tunnels: Maximum number of tunnels in the group
        **config_kwargs: Additional configuration options

    Yields:
        TunnelGroup: A group that can manage multiple tunnels

    Example:
        >>> with tunnel_group_context("example.com", auth_token="secret") as group:
        ...     group.add_http_tunnel(3000, "/web")
        ...     group.add_http_tunnel(8080, "/api")
        ...     group.add_tcp_tunnel(5432)
        ...     group.start_all()
        ...     # Use the tunnels
        # All tunnels are automatically cleaned up here
    """
    # Create FRP client with context management
    with FRPClient(server, auth_token=auth_token) as client:
        # Create tunnel group configuration
        config = TunnelGroupConfig(
            group_name=group_name,
            max_tunnels=max_tunnels,
            **config_kwargs,
        )

        # Create and yield the tunnel group
        with TunnelGroup(client, config) as group:
            logger.info(
                "Tunnel group created",
                group_name=group_name,
                max_tunnels=max_tunnels,
            )
            yield group
            logger.info("Tunnel group cleaned up", group_name=group_name)
