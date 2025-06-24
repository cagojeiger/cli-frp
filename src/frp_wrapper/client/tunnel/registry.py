"""Tunnel registry for managing active tunnels."""

import logging
from typing import Any

from pydantic import BaseModel, Field

from .exceptions import TunnelRegistryError
from .models import BaseTunnel, HTTPTunnel, TCPTunnel, TunnelStatus, TunnelType

logger = logging.getLogger(__name__)


class TunnelRegistry(BaseModel):
    """In-memory store for active tunnels with add/remove/query operations."""

    tunnels: dict[str, BaseTunnel] = Field(
        default_factory=dict, description="Active tunnels by ID"
    )
    max_tunnels: int = Field(
        default=10, ge=1, le=100, description="Maximum number of tunnels"
    )

    def add_tunnel(self, tunnel: BaseTunnel) -> None:
        """Add tunnel to registry with validation.

        Args:
            tunnel: Tunnel to add

        Raises:
            TunnelRegistryError: If tunnel ID already exists or validation fails
        """
        if tunnel.id in self.tunnels:
            raise TunnelRegistryError(f"Tunnel with ID '{tunnel.id}' already exists")

        if len(self.tunnels) >= self.max_tunnels:
            raise TunnelRegistryError(
                f"Maximum tunnel limit ({self.max_tunnels}) reached"
            )

        if tunnel.tunnel_type == TunnelType.TCP:
            for existing_tunnel in self.tunnels.values():
                if (
                    existing_tunnel.tunnel_type == TunnelType.TCP
                    and existing_tunnel.local_port == tunnel.local_port
                ):
                    raise TunnelRegistryError(
                        f"Local port {tunnel.local_port} already in use"
                    )

        if tunnel.tunnel_type == TunnelType.HTTP and isinstance(tunnel, HTTPTunnel):
            for existing_tunnel in self.tunnels.values():
                if (
                    existing_tunnel.tunnel_type == TunnelType.HTTP
                    and isinstance(existing_tunnel, HTTPTunnel)
                    and existing_tunnel.path == tunnel.path
                ):
                    raise TunnelRegistryError(
                        f"HTTP path '{tunnel.path}' already in use"
                    )

        self.tunnels[tunnel.id] = tunnel
        logger.info(f"Added tunnel {tunnel.id} to registry")

    def remove_tunnel(self, tunnel_id: str) -> BaseTunnel:
        """Remove tunnel from registry.

        Args:
            tunnel_id: ID of tunnel to remove

        Returns:
            Removed tunnel

        Raises:
            TunnelRegistryError: If tunnel not found
        """
        if tunnel_id not in self.tunnels:
            raise TunnelRegistryError(f"Tunnel '{tunnel_id}' not found")

        tunnel = self.tunnels.pop(tunnel_id)
        logger.info(f"Removed tunnel {tunnel_id} from registry")
        return tunnel

    def get_tunnel(self, tunnel_id: str) -> BaseTunnel | None:
        """Get tunnel by ID.

        Args:
            tunnel_id: ID of tunnel to retrieve

        Returns:
            Tunnel if found, None otherwise
        """
        return self.tunnels.get(tunnel_id)

    def update_tunnel_status(self, tunnel_id: str, status: TunnelStatus) -> None:
        """Update tunnel status.

        Args:
            tunnel_id: ID of tunnel to update
            status: New status

        Raises:
            TunnelRegistryError: If tunnel not found
        """
        if tunnel_id not in self.tunnels:
            raise TunnelRegistryError(f"Tunnel '{tunnel_id}' not found")

        tunnel = self.tunnels[tunnel_id]
        updated_tunnel = tunnel.with_status(status)
        self.tunnels[tunnel_id] = updated_tunnel
        logger.info(f"Updated tunnel {tunnel_id} status to {status}")

    def list_tunnels(
        self, tunnel_type: TunnelType | None = None, status: TunnelStatus | None = None
    ) -> list[BaseTunnel]:
        """List tunnels with optional filtering.

        Args:
            tunnel_type: Filter by tunnel type
            status: Filter by status

        Returns:
            List of matching tunnels
        """
        tunnels = list(self.tunnels.values())

        if tunnel_type is not None:
            tunnels = [t for t in tunnels if t.tunnel_type == tunnel_type]

        if status is not None:
            tunnels = [t for t in tunnels if t.status == status]

        return tunnels

    def clear(self) -> None:
        """Clear all tunnels from registry."""
        self.tunnels.clear()
        logger.info("Cleared all tunnels from registry")

    def to_dict(self) -> dict[str, Any]:
        """Serialize registry to dictionary.

        Returns:
            Dictionary representation of registry
        """
        return {
            "tunnels": [tunnel.model_dump() for tunnel in self.tunnels.values()],
            "max_tunnels": self.max_tunnels,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TunnelRegistry":
        """Deserialize registry from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            TunnelRegistry instance
        """
        registry = cls(max_tunnels=data.get("max_tunnels", 10))

        for tunnel_data in data.get("tunnels", []):
            tunnel: BaseTunnel
            if tunnel_data["tunnel_type"] == TunnelType.HTTP:
                tunnel = HTTPTunnel(**tunnel_data)
            elif tunnel_data["tunnel_type"] == TunnelType.TCP:
                tunnel = TCPTunnel(**tunnel_data)
            else:
                continue

            registry.tunnels[tunnel.id] = tunnel

        return registry
