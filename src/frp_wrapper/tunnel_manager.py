"""Tunnel management system with registry and lifecycle management."""

import logging
from typing import Any

from pydantic import BaseModel, Field

from .tunnel import BaseTunnel, HTTPTunnel, TCPTunnel, TunnelStatus, TunnelType

logger = logging.getLogger(__name__)


class TunnelRegistryError(Exception):
    """Exception raised for tunnel registry operations."""

    pass


class TunnelManagerError(Exception):
    """Exception raised for tunnel manager operations."""

    pass


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


class TunnelManager:
    """Registry for active tunnels with lifecycle management."""

    def __init__(self, max_tunnels: int = 10):
        """Initialize tunnel manager.

        Args:
            max_tunnels: Maximum number of tunnels to allow
        """
        self.registry = TunnelRegistry(max_tunnels=max_tunnels)
        self._processes: dict[str, Any] = {}  # Store process handles
        logger.info(f"Initialized TunnelManager with max_tunnels={max_tunnels}")

    def create_http_tunnel(
        self,
        tunnel_id: str,
        local_port: int,
        path: str,
        custom_domains: list[str] | None = None,
        strip_path: bool = True,
        websocket: bool = True,
    ) -> HTTPTunnel:
        """Create HTTP tunnel and add to registry.

        Args:
            tunnel_id: Unique tunnel identifier
            local_port: Local port to expose
            path: URL path for routing
            custom_domains: Custom domains for tunnel
            strip_path: Strip path prefix when forwarding
            websocket: Enable WebSocket support

        Returns:
            Created HTTP tunnel
        """
        tunnel = HTTPTunnel(
            id=tunnel_id,
            local_port=local_port,
            path=path,
            custom_domains=custom_domains or [],
            strip_path=strip_path,
            websocket=websocket,
        )

        self.registry.add_tunnel(tunnel)
        logger.info(f"Created HTTP tunnel {tunnel_id} for path /{path}")
        return tunnel

    def create_tcp_tunnel(
        self, tunnel_id: str, local_port: int, remote_port: int | None = None
    ) -> TCPTunnel:
        """Create TCP tunnel and add to registry.

        Args:
            tunnel_id: Unique tunnel identifier
            local_port: Local port to expose
            remote_port: Remote port (auto-assigned if None)

        Returns:
            Created TCP tunnel
        """
        tunnel = TCPTunnel(id=tunnel_id, local_port=local_port, remote_port=remote_port)

        self.registry.add_tunnel(tunnel)
        logger.info(f"Created TCP tunnel {tunnel_id} for port {local_port}")
        return tunnel

    def start_tunnel(self, tunnel_id: str) -> bool:
        """Start tunnel process.

        Args:
            tunnel_id: ID of tunnel to start

        Returns:
            True if started successfully

        Raises:
            TunnelManagerError: If tunnel not found or start fails
        """
        tunnel = self.registry.get_tunnel(tunnel_id)
        if tunnel is None:
            raise TunnelManagerError(f"Tunnel '{tunnel_id}' not found")

        if tunnel.status == TunnelStatus.CONNECTED:
            logger.warning(f"Tunnel {tunnel_id} is already connected")
            return True

        self.registry.update_tunnel_status(tunnel_id, TunnelStatus.CONNECTING)

        try:
            success = self._start_frp_process(tunnel)

            if success:
                self.registry.update_tunnel_status(tunnel_id, TunnelStatus.CONNECTED)
                logger.info(f"Started tunnel {tunnel_id}")
                return True
            else:
                self.registry.update_tunnel_status(tunnel_id, TunnelStatus.ERROR)
                logger.error(f"Failed to start tunnel {tunnel_id}")
                return False

        except Exception as e:
            self.registry.update_tunnel_status(tunnel_id, TunnelStatus.ERROR)
            logger.error(f"Error starting tunnel {tunnel_id}: {e}")
            raise TunnelManagerError(f"Failed to start tunnel: {e}") from e

    def stop_tunnel(self, tunnel_id: str) -> bool:
        """Stop tunnel process.

        Args:
            tunnel_id: ID of tunnel to stop

        Returns:
            True if stopped successfully

        Raises:
            TunnelManagerError: If tunnel not found or stop fails
        """
        tunnel = self.registry.get_tunnel(tunnel_id)
        if tunnel is None:
            raise TunnelManagerError(f"Tunnel '{tunnel_id}' not found")

        if tunnel.status != TunnelStatus.CONNECTED:
            logger.warning(f"Tunnel {tunnel_id} is not connected")
            return True

        try:
            success = self._stop_frp_process(tunnel_id)

            if success:
                self.registry.update_tunnel_status(tunnel_id, TunnelStatus.DISCONNECTED)
                logger.info(f"Stopped tunnel {tunnel_id}")
                return True
            else:
                logger.error(f"Failed to stop tunnel {tunnel_id}")
                return False

        except Exception as e:
            logger.error(f"Error stopping tunnel {tunnel_id}: {e}")
            raise TunnelManagerError(f"Failed to stop tunnel: {e}") from e

    def remove_tunnel(self, tunnel_id: str) -> BaseTunnel:
        """Remove tunnel from manager.

        Args:
            tunnel_id: ID of tunnel to remove

        Returns:
            Removed tunnel
        """
        tunnel = self.registry.get_tunnel(tunnel_id)
        if tunnel and tunnel.status == TunnelStatus.CONNECTED:
            self.stop_tunnel(tunnel_id)

        removed_tunnel = self.registry.remove_tunnel(tunnel_id)

        if tunnel_id in self._processes:
            del self._processes[tunnel_id]

        logger.info(f"Removed tunnel {tunnel_id}")
        return removed_tunnel

    def list_active_tunnels(self) -> list[BaseTunnel]:
        """List only active (connected) tunnels.

        Returns:
            List of connected tunnels
        """
        return self.registry.list_tunnels(status=TunnelStatus.CONNECTED)

    def get_tunnel_info(self, tunnel_id: str) -> dict[str, Any]:
        """Get detailed tunnel information.

        Args:
            tunnel_id: ID of tunnel

        Returns:
            Dictionary with tunnel information

        Raises:
            TunnelManagerError: If tunnel not found
        """
        tunnel = self.registry.get_tunnel(tunnel_id)
        if tunnel is None:
            raise TunnelManagerError(f"Tunnel '{tunnel_id}' not found")

        info: dict[str, Any] = {
            "id": tunnel.id,
            "type": tunnel.tunnel_type.value,
            "local_port": tunnel.local_port,
            "status": tunnel.status.value,
            "created_at": tunnel.created_at.isoformat(),
            "connected_at": tunnel.connected_at.isoformat()
            if tunnel.connected_at
            else None,
        }

        if tunnel.tunnel_type == TunnelType.HTTP and isinstance(tunnel, HTTPTunnel):
            info.update(
                {
                    "path": tunnel.path,
                    "custom_domains": tunnel.custom_domains,
                    "url": tunnel.url,
                }
            )
        elif tunnel.tunnel_type == TunnelType.TCP and isinstance(tunnel, TCPTunnel):
            info.update(
                {"remote_port": tunnel.remote_port, "endpoint": tunnel.endpoint}
            )

        return info

    def shutdown_all(self) -> bool:
        """Shutdown all active tunnels.

        Returns:
            True if all tunnels stopped successfully
        """
        active_tunnels = self.list_active_tunnels()
        success = True

        for tunnel in active_tunnels:
            try:
                if not self.stop_tunnel(tunnel.id):
                    success = False
            except Exception as e:
                logger.error(f"Error stopping tunnel {tunnel.id}: {e}")
                success = False

        logger.info(f"Shutdown all tunnels, success={success}")
        return success

    def _start_frp_process(self, tunnel: BaseTunnel) -> bool:
        """Start FRP process for tunnel (implementation placeholder).

        Args:
            tunnel: Tunnel to start process for

        Returns:
            True if process started successfully
        """
        logger.debug(f"Starting FRP process for tunnel {tunnel.id}")
        return True

    def _stop_frp_process(self, tunnel_id: str) -> bool:
        """Stop FRP process for tunnel (implementation placeholder).

        Args:
            tunnel_id: ID of tunnel to stop process for

        Returns:
            True if process stopped successfully
        """
        logger.debug(f"Stopping FRP process for tunnel {tunnel_id}")
        return True
