"""High-level API for FRP Python Wrapper.

This module provides simple, user-friendly functions for common tunneling tasks.
"""

from typing import Any

from .common.logging import get_logger
from .tunnels import TunnelConfig, TunnelManager

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
