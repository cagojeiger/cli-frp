"""Configuration builder for FRP client."""

import os
import tempfile
from types import TracebackType
from typing import Any, Literal

from .logging import get_logger

logger = get_logger(__name__)


class ConfigBuilder:
    """Builder for FRP client configuration files."""

    def __init__(self) -> None:
        """Initialize ConfigBuilder with empty state."""
        self._server_addr: str | None = None
        self._server_port: int = 7000
        self._auth_token: str | None = None
        self._config_path: str | None = None
        self._proxies: list[dict[str, Any]] = []

        logger.debug("ConfigBuilder initialized")

    def add_server(
        self, addr: str, port: int = 7000, token: str | None = None
    ) -> "ConfigBuilder":
        """Add server configuration.

        Args:
            addr: Server address
            port: Server port (default: 7000)
            token: Authentication token

        Returns:
            Self for method chaining

        Raises:
            ValueError: If address is empty or port is invalid
        """
        if not addr or not addr.strip():
            raise ValueError("Server address cannot be empty")

        if not (1 <= port <= 65535):
            raise ValueError("Port must be between 1 and 65535")

        self._server_addr = addr.strip()
        self._server_port = port
        self._auth_token = token

        logger.debug(
            "Server configuration added",
            addr=self._server_addr,
            port=self._server_port,
            has_token=token is not None,
        )

        return self

    def add_http_proxy(
        self,
        name: str,
        local_port: int,
        locations: list[str],
        custom_domains: list[str] | None = None,
    ) -> "ConfigBuilder":
        """Add HTTP proxy configuration.

        Args:
            name: Proxy name
            local_port: Local port to forward from
            locations: URL paths for routing
            custom_domains: Custom domains for the proxy

        Returns:
            Self for method chaining
        """
        proxy_config = {
            "type": "http",
            "name": name,
            "local_port": local_port,
            "locations": locations,
        }

        if custom_domains:
            proxy_config["custom_domains"] = custom_domains

        self._proxies.append(proxy_config)
        logger.debug(f"Added HTTP proxy configuration: {name}")
        return self

    def add_tcp_proxy(
        self,
        name: str,
        local_port: int,
        remote_port: int | None = None,
    ) -> "ConfigBuilder":
        """Add TCP proxy configuration.

        Args:
            name: Proxy name
            local_port: Local port to forward from
            remote_port: Remote port to forward to (auto-assigned if None)

        Returns:
            Self for method chaining
        """
        proxy_config = {
            "type": "tcp",
            "name": name,
            "local_port": local_port,
        }

        if remote_port is not None:
            proxy_config["remote_port"] = remote_port

        self._proxies.append(proxy_config)
        logger.debug(f"Added TCP proxy configuration: {name}")
        return self

    def build(self) -> str:
        """Build configuration file and return path.

        Returns:
            Path to generated configuration file

        Raises:
            ValueError: If server address not set
        """
        if not self._server_addr:
            raise ValueError("Server address not set. Call add_server() first.")

        fd, temp_path = tempfile.mkstemp(suffix=".toml", prefix="frp_config_")

        try:
            with os.fdopen(fd, "w") as f:
                # Write common section
                f.write("[common]\n")
                f.write(f'server_addr = "{self._server_addr}"\n')
                f.write(f"server_port = {self._server_port}\n")

                if self._auth_token:
                    f.write(f'token = "{self._auth_token}"\n')

                f.write("\n")

                # Write proxy sections
                for proxy in self._proxies:
                    f.write(f"[{proxy['name']}]\n")
                    f.write(f'type = "{proxy["type"]}"\n')
                    f.write(f"local_port = {proxy['local_port']}\n")

                    if proxy["type"] == "http":
                        # HTTP-specific settings
                        locations_str = ", ".join(
                            f'"{loc}"' for loc in proxy["locations"]
                        )
                        f.write(f"locations = [{locations_str}]\n")

                        if "custom_domains" in proxy:
                            domains_str = ", ".join(
                                f'"{domain}"' for domain in proxy["custom_domains"]
                            )
                            f.write(f"custom_domains = [{domains_str}]\n")

                    elif proxy["type"] == "tcp":
                        # TCP-specific settings
                        if "remote_port" in proxy:
                            f.write(f"remote_port = {proxy['remote_port']}\n")

                    f.write("\n")

            self._config_path = temp_path

            logger.info("Configuration file built", path=self._config_path)
            return self._config_path

        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def cleanup(self) -> None:
        """Clean up temporary configuration file."""
        if self._config_path and os.path.exists(self._config_path):
            try:
                os.unlink(self._config_path)
                logger.debug("Configuration file cleaned up", path=self._config_path)
            except OSError as e:
                logger.warning("Failed to cleanup config file", error=str(e))
            finally:
                self._config_path = None

    def __enter__(self) -> "ConfigBuilder":
        """Context manager entry.

        Returns:
            Self for use in with statement
        """
        logger.debug("Entering ConfigBuilder context")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        """Context manager exit - automatically cleanup.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        Returns:
            False to propagate any exception
        """
        logger.debug("Exiting ConfigBuilder context")
        try:
            self.cleanup()
        except Exception as e:
            logger.error("Error during context exit", error=str(e))
        return False  # Don't suppress exceptions
