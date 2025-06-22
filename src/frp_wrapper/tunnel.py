"""Tunnel models and management using Pydantic for type safety and validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TunnelType(str, Enum):
    """Tunnel type enumeration."""

    HTTP = "http"
    TCP = "tcp"


class TunnelStatus(str, Enum):
    """Tunnel status enumeration."""

    PENDING = "pending"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CLOSED = "closed"


class BaseTunnel(BaseModel):
    """Base tunnel model with immutable design pattern."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    id: str = Field(min_length=1, description="Unique tunnel identifier")
    tunnel_type: TunnelType = Field(description="Type of tunnel (HTTP/TCP)")
    local_port: int = Field(ge=1, le=65535, description="Local port to expose")
    status: TunnelStatus = Field(
        default=TunnelStatus.PENDING, description="Current tunnel status"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Tunnel creation timestamp"
    )
    connected_at: datetime | None = Field(
        default=None, description="Connection timestamp"
    )

    def with_status(self, status: TunnelStatus) -> "BaseTunnel":
        """Create new tunnel instance with updated status (immutable pattern).

        Args:
            status: New tunnel status

        Returns:
            New tunnel instance with updated status
        """
        update_data: dict[str, Any] = {"status": status}

        if status == TunnelStatus.CONNECTED and self.connected_at is None:
            update_data["connected_at"] = datetime.now()

        return self.model_copy(update=update_data)


class TCPTunnel(BaseTunnel):
    """TCP tunnel for raw port forwarding."""

    tunnel_type: Literal[TunnelType.TCP] = TunnelType.TCP
    remote_port: int | None = Field(
        default=None, ge=1, le=65535, description="Remote port (auto-assigned if None)"
    )

    @property
    def endpoint(self) -> str | None:
        """Get tunnel endpoint URL.

        Returns:
            Endpoint URL if connected, None otherwise
        """
        if self.status != TunnelStatus.CONNECTED or self.remote_port is None:
            return None

        return f"{{server_host}}:{self.remote_port}"


class HTTPTunnel(BaseTunnel):
    """HTTP tunnel with path-based routing using FRP locations feature."""

    tunnel_type: Literal[TunnelType.HTTP] = TunnelType.HTTP
    path: str = Field(description="URL path for routing (without leading slash)")
    custom_domains: list[str] = Field(
        default_factory=list, description="Custom domains for tunnel"
    )
    strip_path: bool = Field(
        default=True, description="Strip path prefix when forwarding"
    )
    websocket: bool = Field(default=True, description="Enable WebSocket support")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate path format."""
        if v.startswith("/"):
            raise ValueError(
                "Path should not start with '/' - it will be added automatically"
            )

        if not v.replace("-", "").replace("_", "").replace("/", "").isalnum():
            raise ValueError(
                "Path must contain only alphanumeric characters, hyphens, underscores, and slashes"
            )

        return v

    @property
    def locations(self) -> list[str]:
        """Get FRP locations configuration.

        Returns:
            List of location paths for FRP configuration
        """
        return [f"/{self.path}"]

    @property
    def url(self) -> str | None:
        """Get tunnel public URL.

        Returns:
            Public URL if connected and has domains, None otherwise
        """
        if self.status != TunnelStatus.CONNECTED or not self.custom_domains:
            return None

        domain = self.custom_domains[0]
        return f"https://{domain}/{self.path}/"
