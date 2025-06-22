"""FRP Client implementation for managing tunnels and connections."""

import os
import shutil
from types import TracebackType
from typing import Literal

from .config import ConfigBuilder
from .exceptions import (
    AuthenticationError,
    BinaryNotFoundError,
    ConnectionError,
    ProcessError,
)
from .logging import get_logger
from .process import ProcessManager

logger = get_logger(__name__)


class FRPClient:
    """FRP Client for managing tunnels and server connections."""

    def __init__(
        self,
        server: str,
        port: int = 7000,
        auth_token: str | None = None,
        binary_path: str | None = None,
    ):
        """Initialize FRP Client.

        Args:
            server: FRP server address
            port: FRP server port (default: 7000)
            auth_token: Authentication token for server
            binary_path: Path to frpc binary (auto-detected if None)

        Raises:
            ValueError: If server address is invalid or port is out of range
            BinaryNotFoundError: If frpc binary cannot be found
        """
        if not server or not server.strip():
            raise ValueError("Server address cannot be empty")

        if not (1 <= port <= 65535):
            raise ValueError("Port must be between 1 and 65535")

        self.server = server.strip()
        self.port = port
        self.auth_token = auth_token

        if binary_path is None:
            self.binary_path = self.find_frp_binary()
        else:
            self.binary_path = binary_path

        self._process_manager: ProcessManager | None = None
        self._config_builder: ConfigBuilder | None = None
        self._connected = False

        logger.info(
            "FRPClient initialized",
            server=self.server,
            port=self.port,
            binary_path=self.binary_path,
        )

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
