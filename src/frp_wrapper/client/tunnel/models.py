"""Tunnel models for FRP client.

This module defines the base tunnel models and their type-specific implementations.
"""

import re
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    pass


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
    """Base tunnel model with immutable design pattern and context manager support."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="allow")

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

    @property
    def manager(self) -> Any | None:
        """Get associated tunnel manager."""
        return getattr(self, "_manager", None)

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

    def with_manager(self, manager: Any) -> "BaseTunnel":
        """Associate tunnel with a manager for context management.

        Args:
            manager: TunnelManager instance to associate with

        Returns:
            New tunnel instance with manager association
        """
        new_tunnel = self.model_copy()
        object.__setattr__(new_tunnel, "_manager", manager)
        return new_tunnel

    def __enter__(self) -> "BaseTunnel":
        """Enter context manager - start the tunnel.

        Returns:
            Self for method chaining

        Raises:
            RuntimeError: If no manager is associated or tunnel start fails
        """
        if self.manager is None:
            raise RuntimeError(
                f"No manager associated with tunnel {self.id}. "
                "Use tunnel.with_manager(manager) first."
            )

        success = self.manager.start_tunnel(self.id)
        if not success:
            raise RuntimeError(f"Failed to start tunnel {self.id}")

        # Return updated tunnel instance from manager
        updated_tunnel = self.manager.registry.get_tunnel(self.id)
        if updated_tunnel is None:
            raise RuntimeError(f"Tunnel {self.id} not found after start")

        return cast(BaseTunnel, updated_tunnel.with_manager(self.manager))

    def __exit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Exit context manager - stop and remove the tunnel.

        Args:
            _exc_type: Exception type if an exception was raised
            _exc_val: Exception value if an exception was raised
            _exc_tb: Exception traceback if an exception was raised
        """
        if self.manager is not None:
            try:
                # Get current tunnel status from manager
                current_tunnel = self.manager.registry.get_tunnel(self.id)
                if current_tunnel and current_tunnel.status == TunnelStatus.CONNECTED:
                    self.manager.stop_tunnel(self.id)
                self.manager.remove_tunnel(self.id)
            except Exception:
                # Suppress exceptions during cleanup to avoid masking original exceptions
                pass


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

        # Enhanced security: More restrictive character validation
        # Allow only: alphanumeric, hyphens, underscores, single slashes, single dots, and single wildcards
        if not re.match(r"^[a-zA-Z0-9/_\-.*]+$", v):
            raise ValueError(
                "Path must contain only alphanumeric characters, hyphens, underscores, slashes, dots, and wildcards (*)"
            )

        # Security checks for path traversal and malicious patterns
        security_checks = [
            ("..", "Path cannot contain '..' (directory traversal)"),
            ("./", "Path cannot contain './' (relative path)"),
            ("***", "Path cannot contain triple wildcards"),
            ("**/**", "Path cannot contain nested recursive wildcards"),
            ("/**/", "Path cannot contain standalone recursive wildcards"),
        ]

        for pattern, error_msg in security_checks:
            if pattern in v:
                raise ValueError(error_msg)

        # Path format validation
        if v.endswith("/"):
            raise ValueError("Path cannot end with '/'")

        if "//" in v:
            raise ValueError("Path cannot contain consecutive slashes")

        # Additional security: prevent control characters and ensure reasonable length
        MIN_PRINTABLE_CHAR = 32  # ASCII printable characters start at 32
        MAX_PATH_LENGTH = 200  # Reasonable path length limit

        if any(ord(char) < MIN_PRINTABLE_CHAR for char in v):
            raise ValueError("Path cannot contain control characters")

        if len(v) > MAX_PATH_LENGTH:
            raise ValueError(f"Path too long (maximum {MAX_PATH_LENGTH} characters)")

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
