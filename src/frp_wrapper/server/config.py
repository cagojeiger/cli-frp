"""Configuration models for FRP server."""

import os
import tempfile
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Constants for validation
MIN_AUTH_TOKEN_LENGTH = 8
MIN_TOKEN_DIVERSITY = 4
MIN_PASSWORD_LENGTH = 6


class LogLevel(str, Enum):
    """FRP server log levels."""

    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class AuthMethod(str, Enum):
    """Authentication methods."""

    TOKEN = "token"
    OIDC = "oidc"


class ServerConfig(BaseModel):
    """Pydantic model for FRP server configuration."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    # Basic server settings
    bind_addr: str = Field(default="0.0.0.0", description="Server bind address")
    bind_port: int = Field(default=7000, ge=1, le=65535, description="Control port")
    kcp_bind_port: int | None = Field(
        default=None, ge=1, le=65535, description="KCP protocol port"
    )

    # Virtual host ports
    vhost_http_port: int = Field(
        default=80, ge=1, le=65535, description="HTTP virtual host port"
    )
    vhost_https_port: int = Field(
        default=443, ge=1, le=65535, description="HTTPS virtual host port"
    )

    # Authentication
    auth_method: AuthMethod = Field(default=AuthMethod.TOKEN)
    auth_token: str | None = Field(
        default=None, min_length=8, description="Authentication token"
    )

    # Domain settings
    subdomain_host: str | None = Field(
        default=None, description="Subdomain host for tunnels"
    )
    custom_404_page: str | None = Field(
        default=None, description="Custom 404 page path"
    )

    # Logging
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_max_days: int = Field(default=3, ge=1, le=365, description="Log retention days")
    log_file: str | None = Field(default=None, description="Log file path")

    # Performance
    max_pool_count: int = Field(
        default=5, ge=1, le=100, description="Maximum pool count"
    )
    max_ports_per_client: int = Field(
        default=0, ge=0, description="Max ports per client (0=unlimited)"
    )
    heartbeat_timeout: int = Field(
        default=90, ge=30, le=300, description="Heartbeat timeout seconds"
    )

    @field_validator("auth_token")
    @classmethod
    def validate_auth_token(cls, v: str | None) -> str | None:
        """Validate auth token strength."""
        if v is not None:
            if len(v) < MIN_AUTH_TOKEN_LENGTH:
                raise ValueError(
                    f"Auth token must be at least {MIN_AUTH_TOKEN_LENGTH} characters"
                )
            if v.isalnum() and len(set(v)) < MIN_TOKEN_DIVERSITY:
                raise ValueError("Auth token should contain diverse characters")
        return v

    @field_validator("subdomain_host")
    @classmethod
    def validate_subdomain_host(cls, v: str | None) -> str | None:
        """Validate subdomain host format."""
        if v is not None:
            if not v or "." not in v:
                raise ValueError("Subdomain host must be a valid domain")
            # Basic domain validation
            parts = v.split(".")
            for part in parts:
                if not part or not part.replace("-", "").isalnum():
                    raise ValueError(f"Invalid domain part: {part}")
        return v

    def to_toml(self) -> str:
        """Generate FRP server TOML configuration."""
        config_lines = []

        # Basic settings
        config_lines.append(f'bindAddr = "{self.bind_addr}"')
        config_lines.append(f"bindPort = {self.bind_port}")

        if self.kcp_bind_port:
            config_lines.append(f"kcpBindPort = {self.kcp_bind_port}")

        # Virtual host settings
        config_lines.append(f"vhostHTTPPort = {self.vhost_http_port}")
        config_lines.append(f"vhostHTTPSPort = {self.vhost_https_port}")

        # Authentication
        if self.auth_token:
            config_lines.append(f'auth.method = "{self.auth_method.value}"')
            config_lines.append(f'auth.token = "{self.auth_token}"')

        # Domain settings
        if self.subdomain_host:
            config_lines.append(f'subDomainHost = "{self.subdomain_host}"')

        if self.custom_404_page:
            config_lines.append(f'custom404Page = "{self.custom_404_page}"')

        # Logging
        config_lines.append(f'log.level = "{self.log_level.value}"')
        config_lines.append(f"log.maxDays = {self.log_max_days}")

        if self.log_file:
            config_lines.append(f'log.file = "{self.log_file}"')

        # Performance
        config_lines.append(f"maxPoolCount = {self.max_pool_count}")
        if self.max_ports_per_client > 0:
            config_lines.append(f"maxPortsPerClient = {self.max_ports_per_client}")
        config_lines.append(f"heartbeatTimeout = {self.heartbeat_timeout}")

        return "\n".join(config_lines)


class DashboardConfig(BaseModel):
    """Pydantic model for FRP dashboard configuration."""

    model_config = ConfigDict(str_strip_whitespace=True)

    enabled: bool = Field(default=False, description="Enable web dashboard")
    port: int = Field(default=7500, ge=1, le=65535, description="Dashboard port")
    user: str = Field(default="admin", min_length=3, description="Dashboard username")
    password: str = Field(..., min_length=6, description="Dashboard password")
    assets_dir: str | None = Field(default=None, description="Custom assets directory")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate dashboard password strength."""
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
            )

        # Check for basic password strength
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "Password should contain uppercase, lowercase, and numbers"
            )

        return v

    def to_toml_section(self) -> str:
        """Generate dashboard TOML section."""
        if not self.enabled:
            return ""

        lines = [
            "",
            "[webServer]",
            'addr = "0.0.0.0"',
            f"port = {self.port}",
            f'user = "{self.user}"',
            f'password = "{self.password}"',
        ]

        if self.assets_dir:
            lines.append(f'assetsDir = "{self.assets_dir}"')

        return "\n".join(lines)


class ServerConfigBuilder:
    """ConfigBuilder pattern for FRP server configuration."""

    def __init__(self) -> None:
        """Initialize ServerConfigBuilder with empty state."""
        self._server_config = ServerConfig()
        self._dashboard_config: DashboardConfig | None = None
        self._config_path: str | None = None

    def configure_basic(
        self,
        bind_port: int = 7000,
        bind_addr: str = "0.0.0.0",
        auth_token: str | None = None,
    ) -> "ServerConfigBuilder":
        """Configure basic server settings."""
        # Get current values and update with new ones
        current_dict = self._server_config.model_dump()
        current_dict.update(
            {
                "bind_port": bind_port,
                "bind_addr": bind_addr,
            }
        )
        if auth_token is not None:
            current_dict["auth_token"] = auth_token

        # Create new instance to trigger validation
        self._server_config = ServerConfig(**current_dict)
        return self

    def configure_vhost(
        self,
        http_port: int = 80,
        https_port: int = 443,
        subdomain_host: str | None = None,
    ) -> "ServerConfigBuilder":
        """Configure virtual host settings."""
        current_dict = self._server_config.model_dump()
        current_dict.update(
            {
                "vhost_http_port": http_port,
                "vhost_https_port": https_port,
                "subdomain_host": subdomain_host,
            }
        )
        self._server_config = ServerConfig(**current_dict)
        return self

    def enable_dashboard(
        self, port: int = 7500, user: str = "admin", password: str = "admin123"
    ) -> "ServerConfigBuilder":
        """Enable web dashboard."""
        self._dashboard_config = DashboardConfig(
            enabled=True, port=port, user=user, password=password
        )
        return self

    def configure_logging(
        self,
        level: LogLevel = LogLevel.INFO,
        file_path: str | None = None,
        max_days: int = 3,
    ) -> "ServerConfigBuilder":
        """Configure logging settings."""
        current_dict = self._server_config.model_dump()
        current_dict.update(
            {"log_level": level, "log_file": file_path, "log_max_days": max_days}
        )
        self._server_config = ServerConfig(**current_dict)
        return self

    def build(self) -> str:
        """Build configuration file and return path."""
        fd, temp_path = tempfile.mkstemp(suffix=".toml", prefix="frps_config_")

        try:
            with os.fdopen(fd, "w") as f:
                # Write header comment
                f.write("# FRP Server Configuration\n")
                f.write(f"# Generated at: {datetime.now().isoformat()}\n\n")

                # Write server configuration
                f.write(self._server_config.to_toml())

                # Write dashboard configuration
                if self._dashboard_config:
                    dashboard_section = self._dashboard_config.to_toml_section()
                    if dashboard_section:
                        f.write(dashboard_section)

            self._config_path = temp_path
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
            except OSError:
                pass
            finally:
                self._config_path = None

    def __enter__(self) -> "ServerConfigBuilder":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> Literal[False]:
        """Context manager exit - automatically cleanup."""
        try:
            self.cleanup()
        except Exception:
            pass
        return False
