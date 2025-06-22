"""FRP Client implementation for managing tunnels and connections."""

import os
import shutil
import uuid
from types import TracebackType
from typing import TYPE_CHECKING, Any, Literal

from ..common.context import ContextManagerMixin
from ..common.context_config import ContextConfig
from ..common.exceptions import (
    AuthenticationError,
    BinaryNotFoundError,
    ConnectionError,
    ProcessError,
)
from ..common.logging import get_logger
from ..common.utils import (
    sanitize_log_data,
    validate_non_empty_string,
    validate_port,
)
from ..tunnels.models import BaseTunnel, HTTPTunnel, TCPTunnel, TunnelConfig
from .config import ConfigBuilder
from .process import ProcessManager

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class FRPClient(ContextManagerMixin):
    """FRP Client for managing tunnels and server connections."""

    def __init__(
        self,
        server: str,
        port: int = 7000,
        auth_token: str | None = None,
        binary_path: str | None = None,
        context_config: ContextConfig | None = None,
    ):
        """Initialize FRP Client.

        Args:
            server: FRP server address
            port: FRP server port (default: 7000)
            auth_token: Authentication token for server
            binary_path: Path to frpc binary (auto-detected if None)
            context_config: Context manager configuration

        Raises:
            ValueError: If server address is invalid or port is out of range
            BinaryNotFoundError: If frpc binary cannot be found
        """
        super().__init__(context_config=context_config)

        self.server = validate_non_empty_string(server, "Server address")
        validate_port(port, "Server port")

        self.port = port
        self.auth_token = auth_token

        if binary_path is None:
            self.binary_path = self.find_frp_binary()
        else:
            self.binary_path = binary_path

        self._process_manager: ProcessManager | None = None
        self._config_builder: ConfigBuilder | None = None
        self._connected = False
        tunnel_config = TunnelConfig(
            server_host=self.server,
            auth_token=self.auth_token,
            default_domain=None,
            max_tunnels=10,
        )
        from ..tunnels.manager import TunnelManager  # noqa: PLC0415

        self.tunnel_manager = TunnelManager(
            tunnel_config, frp_binary_path=self.binary_path
        )

        # Log initialization with sensitive data masked
        log_data = sanitize_log_data(
            {
                "server": self.server,
                "port": self.port,
                "auth_token": self.auth_token,
                "binary_path": self.binary_path,
            }
        )
        logger.info("FRPClient initialized", **log_data)

    @staticmethod
    def find_frp_binary() -> str:
        """Find frpc binary in system PATH or common locations.

        Returns:
            Path to frpc binary

        Raises:
            BinaryNotFoundError: If binary cannot be found
        """
        binary_path = shutil.which("frpc")
        if binary_path:
            return binary_path

        common_paths = [
            "/usr/local/bin/frpc",
            "/usr/bin/frpc",
            "/opt/frp/frpc",
            "/usr/local/frp/frpc",
            "~/frp/frpc",
            "./frpc",
        ]

        for path in common_paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path) and os.access(expanded_path, os.X_OK):
                return expanded_path

        raise BinaryNotFoundError("frpc binary not found in PATH or common locations")

    def connect(self) -> bool:
        """Connect to FRP server.

        Returns:
            True if connection successful

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        if self._connected:
            logger.debug("Already connected to server")
            return True

        try:
            self._config_builder = ConfigBuilder()
            self._config_builder.add_server(self.server, self.port, self.auth_token)
            config_path = self._config_builder.build()

            self._process_manager = ProcessManager(self.binary_path, config_path)

            if not self._process_manager.start():
                raise ConnectionError("Failed to start FRP process")

            if not self._process_manager.wait_for_startup():
                self._process_manager.stop()
                if not self._process_manager.is_running():
                    raise ConnectionError(
                        "Failed to connect to server - connection refused or server unreachable"
                    )
                else:
                    raise AuthenticationError(
                        "Authentication failed or server unreachable"
                    )

            self._connected = True
            logger.info("Successfully connected to FRP server")
            return True

        except (OSError, ProcessError) as e:
            logger.error("Connection failed", error=str(e))
            raise ConnectionError(f"Failed to connect to server: {e}") from e

    def disconnect(self) -> bool:
        """Disconnect from FRP server.

        Returns:
            True if disconnection successful
        """
        if not self._connected:
            logger.debug("Not connected, nothing to disconnect")
            return True

        try:
            if self._process_manager:
                self._process_manager.stop()
                self._process_manager = None

            if self._config_builder:
                self._config_builder.cleanup()
                self._config_builder = None

            self._connected = False
            logger.info("Disconnected from FRP server")
            return True

        except Exception as e:
            logger.error("Error during disconnect", error=str(e))
            self._connected = False
            return False

    def is_connected(self) -> bool:
        """Check if client is connected to server.

        Returns:
            True if connected
        """
        return self._connected and (
            self._process_manager is not None and self._process_manager.is_running()
        )

    def __enter__(self) -> "FRPClient":
        """Context manager entry - automatically connect.

        Returns:
            Self for use in with statement

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        logger.debug("Entering FRPClient context")
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        """Context manager exit - automatically disconnect.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        Returns:
            False to propagate any exception
        """
        logger.debug("Exiting FRPClient context")
        try:
            self.disconnect()
        except Exception as e:
            logger.error("Error during context exit", error=str(e))
        return False  # Don't suppress exceptions

    def expose_path(
        self,
        local_port: int,
        path: str,
        custom_domains: list[str] | None = None,
        strip_path: bool = True,
        websocket: bool = True,
        auto_start: bool = False,
    ) -> HTTPTunnel:
        """Expose local HTTP service via path-based routing.

        Args:
            local_port: Local port to expose
            path: URL path for routing (without leading slash)
            custom_domains: Custom domains for tunnel
            strip_path: Strip path prefix when forwarding
            websocket: Enable WebSocket support
            auto_start: Automatically start tunnel if client is connected

        Returns:
            Created HTTP tunnel

        Raises:
            ValueError: If port or path is invalid
            TunnelManagerError: If tunnel creation fails
        """
        validate_port(local_port, "Local port")

        path = validate_non_empty_string(path, "Path")

        if path.startswith("/"):
            raise ValueError(
                "Path should not start with '/' - it will be added automatically"
            )

        tunnel_id = f"http-{local_port}-{path}-{uuid.uuid4().hex[:8]}"

        tunnel = self.tunnel_manager.create_http_tunnel(
            tunnel_id=tunnel_id,
            local_port=local_port,
            path=path,
            custom_domains=custom_domains or [],
            strip_path=strip_path,
            websocket=websocket,
        )

        if auto_start and self._connected:
            self.tunnel_manager.start_tunnel(tunnel_id)

        logger.info(f"Exposed HTTP path /{path} on port {local_port}")
        return tunnel

    def expose_tcp(
        self, local_port: int, remote_port: int | None = None, auto_start: bool = False
    ) -> TCPTunnel:
        """Expose local TCP service via port forwarding.

        Args:
            local_port: Local port to expose
            remote_port: Remote port (auto-assigned if None)
            auto_start: Automatically start tunnel if client is connected

        Returns:
            Created TCP tunnel

        Raises:
            ValueError: If port is invalid
            TunnelManagerError: If tunnel creation fails
        """
        validate_port(local_port, "Local port")

        if remote_port is not None:
            validate_port(remote_port, "Remote port")

        if remote_port is not None:
            tunnel_id = f"tcp-{local_port}-{remote_port}-{uuid.uuid4().hex[:8]}"
        else:
            tunnel_id = f"tcp-{local_port}-auto-{uuid.uuid4().hex[:8]}"

        tunnel = self.tunnel_manager.create_tcp_tunnel(
            tunnel_id=tunnel_id, local_port=local_port, remote_port=remote_port
        )

        if auto_start and self._connected:
            self.tunnel_manager.start_tunnel(tunnel_id)

        logger.info(f"Exposed TCP port {local_port} -> {remote_port or 'auto'}")
        return tunnel

    def list_active_tunnels(self) -> list[BaseTunnel]:
        """List all active (connected) tunnels.

        Returns:
            List of connected tunnels
        """
        return self.tunnel_manager.list_active_tunnels()

    def get_tunnel_info(self, tunnel_id: str) -> dict[str, Any]:
        """Get detailed information about a tunnel.

        Args:
            tunnel_id: ID of tunnel to get info for

        Returns:
            Dictionary with tunnel information

        Raises:
            TunnelManagerError: If tunnel not found
        """
        return self.tunnel_manager.get_tunnel_info(tunnel_id)

    def start_tunnel(self, tunnel_id: str) -> bool:
        """Start a specific tunnel.

        Args:
            tunnel_id: ID of tunnel to start

        Returns:
            True if started successfully

        Raises:
            TunnelManagerError: If tunnel not found or start fails
        """
        return self.tunnel_manager.start_tunnel(tunnel_id)

    def stop_tunnel(self, tunnel_id: str) -> bool:
        """Stop a specific tunnel.

        Args:
            tunnel_id: ID of tunnel to stop

        Returns:
            True if stopped successfully

        Raises:
            TunnelManagerError: If tunnel not found or stop fails
        """
        return self.tunnel_manager.stop_tunnel(tunnel_id)

    def remove_tunnel(self, tunnel_id: str) -> BaseTunnel:
        """Remove a tunnel from the client.

        Args:
            tunnel_id: ID of tunnel to remove

        Returns:
            Removed tunnel

        Raises:
            TunnelManagerError: If tunnel not found
        """
        return self.tunnel_manager.remove_tunnel(tunnel_id)

    def shutdown_all_tunnels(self) -> bool:
        """Shutdown all active tunnels.

        Returns:
            True if all tunnels stopped successfully
        """
        return self.tunnel_manager.shutdown_all()
