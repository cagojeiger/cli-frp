"""FRP Server management class."""

from types import TracebackType
from typing import Any, Literal

from ..common.logging import get_logger
from .config import LogLevel, ServerConfigBuilder
from .process import ServerProcessManager

logger = get_logger(__name__)


class FRPServer:
    """FRP server management class (FRPClient pattern reuse)."""

    def __init__(self, binary_path: str = "/usr/local/bin/frps"):
        """Initialize FRP Server.

        Args:
            binary_path: Path to frps binary
        """
        self.binary_path = binary_path
        self._process_manager: ServerProcessManager | None = None
        self._config_builder: ServerConfigBuilder | None = None
        self._config_path: str | None = None

    def configure(
        self,
        bind_port: int = 7000,
        bind_addr: str = "0.0.0.0",
        auth_token: str | None = None,
        vhost_http_port: int = 80,
        vhost_https_port: int = 443,
        subdomain_host: str | None = None,
    ) -> "FRPServer":
        """Configure server settings."""
        self._config_builder = ServerConfigBuilder()
        self._config_builder.configure_basic(
            bind_port=bind_port, bind_addr=bind_addr, auth_token=auth_token
        ).configure_vhost(
            http_port=vhost_http_port,
            https_port=vhost_https_port,
            subdomain_host=subdomain_host,
        )

        logger.info(
            "Server configured", bind_port=bind_port, subdomain_host=subdomain_host
        )
        return self

    def enable_dashboard(
        self, port: int = 7500, user: str = "admin", password: str = "admin123"
    ) -> "FRPServer":
        """Enable web dashboard."""
        if self._config_builder is None:
            raise ValueError("Must call configure() first")

        self._config_builder.enable_dashboard(port=port, user=user, password=password)
        logger.info("Dashboard enabled", port=port, user=user)
        return self

    def configure_logging(
        self,
        level: LogLevel = LogLevel.INFO,
        file_path: str | None = None,
        max_days: int = 3,
    ) -> "FRPServer":
        """Configure logging settings."""
        if self._config_builder is None:
            raise ValueError("Must call configure() first")

        self._config_builder.configure_logging(
            level=level, file_path=file_path, max_days=max_days
        )
        return self

    def start(self) -> bool:
        """Start FRP server."""
        if self._config_builder is None:
            raise ValueError("Must call configure() first")

        try:
            # Build configuration
            self._config_path = self._config_builder.build()

            # Create process manager
            self._process_manager = ServerProcessManager(
                binary_path=self.binary_path, config_path=self._config_path
            )

            # Start server
            success = self._process_manager.start()
            if success:
                logger.info("FRP server started successfully")
            else:
                logger.error("Failed to start FRP server")

            return success
        except Exception as e:
            logger.error("Failed to start FRP server", error=str(e))
            return False

    def stop(self) -> bool:
        """Stop FRP server."""
        if self._process_manager is None:
            return True

        success = self._process_manager.stop()
        if success:
            logger.info("FRP server stopped")
        else:
            logger.warning("Failed to stop FRP server gracefully")

        return success

    def is_running(self) -> bool:
        """Check if server is running."""
        if self._process_manager is None:
            return False
        return self._process_manager.is_running()

    def get_status(self) -> dict[str, Any]:
        """Get server status."""
        if self._process_manager is None:
            return {"running": False, "configured": self._config_builder is not None}

        return self._process_manager.get_server_status()

    def __enter__(self) -> "FRPServer":
        """Context manager entry - automatically start server."""
        logger.debug("Entering FRPServer context")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        """Context manager exit - automatically stop server."""
        logger.debug("Exiting FRPServer context")
        try:
            self.stop()
            if self._config_builder:
                self._config_builder.cleanup()
        except Exception as e:
            logger.error("Error during context exit", error=str(e))
        return False
