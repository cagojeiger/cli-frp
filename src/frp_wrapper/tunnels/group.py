import logging
from contextlib import contextmanager
from typing import Iterator, List, Optional, Any, Type
from types import TracebackType

from typing import TYPE_CHECKING

from ..common.context_config import ContextConfig, TunnelGroupConfig, ResourceTracker, CleanupStrategy
from ..common.exceptions import TunnelError
from .models import BaseTunnel, HTTPTunnel, TCPTunnel

if TYPE_CHECKING:
    from ..core.client import FRPClient

logger = logging.getLogger(__name__)

class TunnelGroup:
    """Pydantic-configured tunnel group with context manager support"""

    def __init__(self, client: 'FRPClient', config: Optional[TunnelGroupConfig] = None):
        self.client = client
        self.config = config or TunnelGroupConfig(group_name="default")
        self.tunnels: List[BaseTunnel] = []
        self._resource_tracker = ResourceTracker()

    def add_http_tunnel(self, local_port: int, path: str, **kwargs) -> 'TunnelGroup':
        """Add HTTP tunnel to group (chainable)"""
        if len(self.tunnels) >= self.config.max_tunnels:
            raise TunnelError(f"Maximum tunnels ({self.config.max_tunnels}) exceeded for group {self.config.group_name}")
        
        tunnel = self.client.expose_path(local_port, path, **kwargs)
        self.tunnels.append(tunnel)
        self._resource_tracker.register_resource(
            tunnel.tunnel_id, tunnel, lambda: self._cleanup_tunnel(tunnel)
        )
        return self

    def add_tcp_tunnel(self, local_port: int, **kwargs) -> 'TunnelGroup':
        """Add TCP tunnel to group (chainable)"""
        if len(self.tunnels) >= self.config.max_tunnels:
            raise TunnelError(f"Maximum tunnels ({self.config.max_tunnels}) exceeded for group {self.config.group_name}")
        
        tunnel = self.client.expose_tcp(local_port, **kwargs)
        self.tunnels.append(tunnel)
        self._resource_tracker.register_resource(
            tunnel.tunnel_id, tunnel, lambda: self._cleanup_tunnel(tunnel)
        )
        return self

    def _cleanup_tunnel(self, tunnel: BaseTunnel) -> None:
        """Clean up a single tunnel"""
        try:
            if hasattr(tunnel, 'manager') and tunnel.manager:
                tunnel.manager.stop_tunnel(tunnel.tunnel_id)
                tunnel.manager.remove_tunnel(tunnel.tunnel_id)
        except Exception as e:
            logger.error(f"Failed to cleanup tunnel {tunnel.tunnel_id}: {e}")

    def start_all(self) -> bool:
        """Start all tunnels in the group"""
        success = True
        for tunnel in self.tunnels:
            try:
                if hasattr(tunnel, 'manager') and tunnel.manager:
                    tunnel.manager.start_tunnel(tunnel.tunnel_id)
            except Exception as e:
                logger.error(f"Failed to start tunnel {tunnel.tunnel_id}: {e}")
                success = False
        return success

    def stop_all(self) -> bool:
        """Stop all tunnels in the group"""
        success = True
        tunnels_to_stop = self.tunnels.copy()
        
        if self.config.cleanup_order == "fifo":
            pass  # Use original order
        else:
            tunnels_to_stop.reverse()

        for tunnel in tunnels_to_stop:
            try:
                if hasattr(tunnel, 'manager') and tunnel.manager:
                    tunnel.manager.stop_tunnel(tunnel.tunnel_id)
            except Exception as e:
                logger.error(f"Failed to stop tunnel {tunnel.tunnel_id}: {e}")
                success = False
        return success

    def __enter__(self) -> 'TunnelGroup':
        """Context manager entry"""
        logger.debug(f"Entering TunnelGroup context: {self.config.group_name}")
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Context manager exit with cleanup"""
        logger.debug(f"Exiting TunnelGroup context: {self.config.group_name}")
        
        try:
            cleanup_errors = self._resource_tracker.cleanup_all()
            
            if cleanup_errors:
                for error in cleanup_errors:
                    logger.error(f"TunnelGroup cleanup error: {error}")
        except Exception as e:
            logger.error(f"TunnelGroup cleanup failed: {e}")

    def __len__(self) -> int:
        """Return number of tunnels in group"""
        return len(self.tunnels)

    def __iter__(self) -> Iterator[BaseTunnel]:
        """Iterate over tunnels in group"""
        return iter(self.tunnels)

@contextmanager
def tunnel_group(
    client: 'FRPClient',
    group_name: str = "default",
    max_tunnels: int = 10,
    **config_kwargs
) -> Iterator[TunnelGroup]:
    """Create a temporary tunnel group with automatic cleanup"""
    config = TunnelGroupConfig(
        group_name=group_name,
        max_tunnels=max_tunnels,
        **config_kwargs
    )

    with TunnelGroup(client, config) as group:
        yield group
