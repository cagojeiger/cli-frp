"""Protocol interfaces for tunnel management to avoid circular dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from .models import BaseTunnel


class TunnelRegistryProtocol(Protocol):
    """Protocol for tunnel registry operations."""

    def get_tunnel(self, tunnel_id: str) -> BaseTunnel | None:
        """Get tunnel by ID."""
        ...

    def update_tunnel_status(self, tunnel_id: str, status: Any) -> None:
        """Update tunnel status."""
        ...


class TunnelManagerProtocol(Protocol):
    """Protocol for tunnel manager operations."""

    @property
    def registry(self) -> TunnelRegistryProtocol:
        """Get tunnel registry."""
        ...

    def start_tunnel(self, tunnel_id: str) -> bool:
        """Start tunnel process."""
        ...

    def stop_tunnel(self, tunnel_id: str) -> bool:
        """Stop tunnel process."""
        ...

    def remove_tunnel(self, tunnel_id: str) -> BaseTunnel:
        """Remove tunnel from manager."""
        ...
