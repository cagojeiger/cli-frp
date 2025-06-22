"""Server configuration models using Pydantic v2.

This module provides comprehensive configuration models for FRP server setup,
including server settings, dashboard configuration, SSL/TLS management,
and complete server configuration generation.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MIN_AUTH_TOKEN_LENGTH = 8
MIN_UNIQUE_CHARS = 4
MIN_PASSWORD_LENGTH = 8


class LogLevel(str, Enum):
    """FRP server log levels"""

    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class AuthMethod(str, Enum):
    """Authentication methods"""

    TOKEN = "token"
    OIDC = "oidc"


class ServerConfig(BaseModel):
    """Pydantic model for FRP server configuration"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    bind_addr: str = Field(default="0.0.0.0", description="Server bind address")
    bind_port: int = Field(default=7000, ge=1, le=65535, description="Control port")
    kcp_bind_port: int | None = Field(
        None, ge=1, le=65535, description="KCP protocol port"
    )

    vhost_http_port: int = Field(
        default=80, ge=1, le=65535, description="HTTP virtual host port"
    )
    vhost_https_port: int = Field(
        default=443, ge=1, le=65535, description="HTTPS virtual host port"
    )

    auth_method: AuthMethod = Field(default=AuthMethod.TOKEN)
    auth_token: str | None = Field(
        None, min_length=8, description="Authentication token"
    )

    subdomain_host: str | None = Field(None, description="Subdomain host for tunnels")
    custom_404_page: str | None = Field(None, description="Custom 404 page path")

    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_max_days: int = Field(default=3, ge=1, le=365, description="Log retention days")
    log_file: str | None = Field(None, description="Log file path")

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
        """Validate auth token strength"""
        if v is not None:
            if len(v) < MIN_AUTH_TOKEN_LENGTH:
                raise ValueError(
                    f"Auth token must be at least {MIN_AUTH_TOKEN_LENGTH} characters"
                )
            if v.isalnum() and len(set(v)) < MIN_UNIQUE_CHARS:
                raise ValueError("Auth token should contain diverse characters")
        return v

    @field_validator("subdomain_host")
    @classmethod
    def validate_subdomain_host(cls, v: str | None) -> str | None:
        """Validate subdomain host format"""
        if v is not None:
            if not v or "." not in v:
                raise ValueError("Subdomain host must be a valid domain")
            parts = v.split(".")
            for part in parts:
                if not part or not part.replace("-", "").isalnum():
                    raise ValueError(f"Invalid domain part: {part}")
        return v

    def to_toml(self) -> str:
        """Generate TOML configuration for FRP server"""
        lines = []

        lines.append(f'bindAddr = "{self.bind_addr}"')
        lines.append(f"bindPort = {self.bind_port}")

        if self.kcp_bind_port:
            lines.append(f"kcpBindPort = {self.kcp_bind_port}")

        lines.append(f"vhostHTTPPort = {self.vhost_http_port}")
        lines.append(f"vhostHTTPSPort = {self.vhost_https_port}")

        if self.auth_token:
            lines.append(f'auth.token = "{self.auth_token}"')

        if self.subdomain_host:
            lines.append(f'subDomainHost = "{self.subdomain_host}"')

        if self.custom_404_page:
            lines.append(f'custom404Page = "{self.custom_404_page}"')

        lines.append(f'log.level = "{self.log_level.value}"')
        lines.append(f"log.maxDays = {self.log_max_days}")

        if self.log_file:
            lines.append(f'log.to = "{self.log_file}"')

        lines.append(f"maxPoolCount = {self.max_pool_count}")

        if self.max_ports_per_client > 0:
            lines.append(f"maxPortsPerClient = {self.max_ports_per_client}")

        lines.append(f"transport.heartbeatTimeout = {self.heartbeat_timeout}")

        return "\n".join(lines)


class DashboardConfig(BaseModel):
    """Pydantic model for FRP dashboard configuration"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    enabled: bool = Field(default=False, description="Enable web dashboard")
    port: int = Field(default=7500, ge=1, le=65535, description="Dashboard port")
    user: str = Field(default="admin", description="Dashboard username")
    password: str | None = Field(None, min_length=8, description="Dashboard password")
    assets_dir: str | None = Field(None, description="Custom assets directory")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        """Validate dashboard password strength"""
        if v is not None and len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Dashboard password must be at least {MIN_PASSWORD_LENGTH} characters"
            )
        return v

    def to_toml(self) -> str:
        """Generate TOML configuration for dashboard"""
        if not self.enabled:
            return ""

        lines = ["[webServer]"]
        lines.append(f"port = {self.port}")
        lines.append(f'user = "{self.user}"')

        if self.password:
            lines.append(f'password = "{self.password}"')

        if self.assets_dir:
            lines.append(f'assetsDir = "{self.assets_dir}"')

        return "\n".join(lines)


class SSLConfig(BaseModel):
    """Pydantic model for SSL/TLS configuration"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    enabled: bool = Field(default=False, description="Enable SSL/TLS")

    cert_file: str | None = Field(None, description="SSL certificate file path")
    key_file: str | None = Field(None, description="SSL private key file path")

    use_letsencrypt: bool = Field(
        default=False, description="Use Let's Encrypt for certificates"
    )
    letsencrypt_email: str | None = Field(None, description="Let's Encrypt email")
    letsencrypt_domains: list[str] = Field(
        default_factory=list, description="Domains for Let's Encrypt"
    )
    letsencrypt_challenge_type: str = Field(
        default="http", description="Challenge type (http/dns)"
    )

    auto_renew: bool = Field(default=True, description="Auto-renew certificates")
    renew_days_before: int = Field(
        default=30, ge=1, le=90, description="Days before expiry to renew"
    )

    @model_validator(mode="after")
    def validate_ssl_config(self) -> "SSLConfig":
        """Validate SSL configuration consistency"""
        if not self.enabled:
            return self

        has_manual_certs = bool(self.cert_file or self.key_file)

        if has_manual_certs and self.use_letsencrypt:
            raise ValueError("Cannot use both manual certificates and Let's Encrypt")

        if has_manual_certs:
            if not (self.cert_file and self.key_file):
                raise ValueError(
                    "Both cert_file and key_file are required for manual certificates"
                )

        if self.use_letsencrypt:
            if not self.letsencrypt_email:
                raise ValueError(
                    "Let's Encrypt email is required when using Let's Encrypt"
                )

            if not self.letsencrypt_domains:
                raise ValueError("At least one domain is required for Let's Encrypt")

        return self

    def to_toml(self) -> str:
        """Generate TOML configuration for SSL"""
        if not self.enabled:
            return ""

        lines = []

        if self.cert_file and self.key_file:
            lines.append(f'tlsCertFile = "{self.cert_file}"')
            lines.append(f'tlsKeyFile = "{self.key_file}"')

        return "\n".join(lines)


class CompleteServerConfig(BaseModel):
    """Complete server configuration combining all components"""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    server: ServerConfig = Field(
        default_factory=lambda: ServerConfig(
            kcp_bind_port=None,
            auth_token=None,
            subdomain_host=None,
            custom_404_page=None,
            log_file=None,
        )
    )
    dashboard: DashboardConfig = Field(
        default_factory=lambda: DashboardConfig(password=None, assets_dir=None)
    )
    ssl: SSLConfig = Field(
        default_factory=lambda: SSLConfig(
            cert_file=None, key_file=None, letsencrypt_email=None
        )
    )
    description: str | None = Field(None, description="Configuration description")
    created_at: datetime = Field(default_factory=datetime.now)

    def generate_toml(self) -> str:
        """Generate complete TOML configuration file"""
        lines = []

        lines.append("# FRP Server Configuration")
        if self.description:
            lines.append(f"# Description: {self.description}")
        lines.append(f"# Generated: {self.created_at.isoformat()}")
        lines.append("")

        lines.append("# Server Settings")
        lines.append(self.server.to_toml())
        lines.append("")

        if self.ssl.enabled:
            lines.append("# SSL/TLS Settings")
            ssl_toml = self.ssl.to_toml()
            if ssl_toml:
                lines.append(ssl_toml)
                lines.append("")

        if self.dashboard.enabled:
            lines.append("# Dashboard Settings")
            lines.append(self.dashboard.to_toml())
            lines.append("")

        return "\n".join(lines)

    def save_to_file(self, path: Path) -> None:
        """Save configuration to TOML file"""
        toml_content = self.generate_toml()
        path.write_text(toml_content, encoding="utf-8")

    @classmethod
    def load_from_file(cls, file_path: Path | str) -> "CompleteServerConfig":
        """Load configuration from TOML file."""
        try:
            import tomllib  # noqa: PLC0415
        except ImportError:
            import tomli as tomllib  # noqa: PLC0415, F811

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, "rb") as f:
            data = tomllib.load(f)

        server_config = ServerConfig(
            bind_addr=data.get("bindAddr", "0.0.0.0"),
            bind_port=data.get("bindPort", 7000),
            kcp_bind_port=data.get("kcpBindPort"),
            vhost_http_port=data.get("vhostHTTPPort", 80),
            vhost_https_port=data.get("vhostHTTPSPort", 443),
            auth_token=data.get("auth", {}).get("token"),
            subdomain_host=data.get("subDomainHost"),
            custom_404_page=data.get("custom404Page"),
            log_level=LogLevel(data.get("log", {}).get("level", "info")),
            log_max_days=data.get("log", {}).get("maxDays", 3),
            log_file=data.get("log", {}).get("to"),
            max_pool_count=data.get("maxPoolCount", 5),
            max_ports_per_client=data.get("maxPortsPerClient", 0),
            heartbeat_timeout=data.get("transport", {}).get("heartbeatTimeout", 90),
        )

        web_server = data.get("webServer", {})
        dashboard_config = DashboardConfig(
            enabled=bool(web_server),
            port=web_server.get("port", 7500),
            user=web_server.get("user", "admin"),
            password=web_server.get("password"),
            assets_dir=web_server.get("assetsDir"),
        )

        ssl_config = SSLConfig(
            enabled=bool(data.get("tlsCertFile") and data.get("tlsKeyFile")),
            cert_file=data.get("tlsCertFile"),
            key_file=data.get("tlsKeyFile"),
            letsencrypt_email=None,
        )

        return cls(
            server=server_config,
            dashboard=dashboard_config,
            ssl=ssl_config,
            description=f"Loaded from {path.name}",
        )
