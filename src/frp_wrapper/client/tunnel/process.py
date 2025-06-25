"""Process management for individual tunnels."""

import logging

from ...common.process import ProcessManager
from ..config import ConfigBuilder
from .config import TunnelConfig
from .models import BaseTunnel, HTTPTunnel, TCPTunnel

logger = logging.getLogger(__name__)


class TunnelProcessManager:
    """Manages FRP processes for individual tunnels."""

    def __init__(self, config: TunnelConfig, frp_binary_path: str):
        """Initialize tunnel process manager.

        Args:
            config: Tunnel configuration with server details
            frp_binary_path: Path to FRP binary
        """
        self.config = config
        self._frp_binary_path = frp_binary_path
        self._processes: dict[str, ProcessManager] = {}

    def start_tunnel_process(self, tunnel: BaseTunnel) -> bool:
        """Start FRP process for tunnel.

        Args:
            tunnel: Tunnel to start process for

        Returns:
            True if process started successfully
        """
        try:
            logger.debug(f"Starting FRP process for tunnel {tunnel.id}")

            # Create configuration for this tunnel
            with ConfigBuilder() as config_builder:
                config_builder.add_server(
                    self.config.server_host,
                    token=self.config.auth_token,
                )

                # Add tunnel-specific configuration
                if isinstance(tunnel, HTTPTunnel):
                    config_builder.add_http_proxy(
                        name=tunnel.id,
                        local_port=tunnel.local_port,
                        locations=tunnel.locations,
                        custom_domains=tunnel.custom_domains,
                    )
                elif isinstance(tunnel, TCPTunnel):
                    config_builder.add_tcp_proxy(
                        name=tunnel.id,
                        local_port=tunnel.local_port,
                        remote_port=tunnel.remote_port,
                    )
                else:
                    logger.error(f"Unsupported tunnel type: {type(tunnel)}")
                    return False

                config_path = config_builder.build()

            # Start FRP process
            process_manager = ProcessManager(self._frp_binary_path, config_path)
            success = process_manager.start()

            if success:
                # Wait for startup
                startup_success = process_manager.wait_for_startup(timeout=10)
                if startup_success and process_manager.is_running():
                    self._processes[tunnel.id] = process_manager
                    logger.info(
                        f"Successfully started FRP process for tunnel {tunnel.id}"
                    )
                    return True
                else:
                    logger.error(
                        f"FRP process for tunnel {tunnel.id} failed to start properly"
                    )
                    process_manager.stop()
                    return False
            else:
                logger.error(f"Failed to start FRP process for tunnel {tunnel.id}")
                return False

        except Exception as e:
            logger.error(f"Exception starting FRP process for tunnel {tunnel.id}: {e}")
            return False

    def stop_tunnel_process(self, tunnel_id: str) -> bool:
        """Stop FRP process for tunnel.

        Args:
            tunnel_id: ID of tunnel to stop process for

        Returns:
            True if process stopped successfully
        """
        try:
            logger.debug(f"Stopping FRP process for tunnel {tunnel_id}")

            if tunnel_id not in self._processes:
                logger.warning(f"No FRP process found for tunnel {tunnel_id}")
                return True

            process_manager = self._processes[tunnel_id]
            success = process_manager.stop()

            if success:
                logger.info(f"Successfully stopped FRP process for tunnel {tunnel_id}")
            else:
                logger.warning(
                    f"FRP process for tunnel {tunnel_id} may not have stopped cleanly"
                )

            # Remove from processes dict regardless of stop success
            del self._processes[tunnel_id]
            return success

        except Exception as e:
            logger.error(f"Exception stopping FRP process for tunnel {tunnel_id}: {e}")
            # Still remove from processes dict to avoid leaks
            if tunnel_id in self._processes:
                del self._processes[tunnel_id]
            return False

    def is_process_running(self, tunnel_id: str) -> bool:
        """Check if FRP process is running for tunnel.

        Args:
            tunnel_id: ID of tunnel to check

        Returns:
            True if process is running
        """
        if tunnel_id not in self._processes:
            return False
        return self._processes[tunnel_id].is_running()

    def cleanup_all_processes(self) -> bool:
        """Stop all running FRP processes.

        Returns:
            True if all processes stopped successfully
        """
        success = True
        tunnel_ids = list(self._processes.keys())

        for tunnel_id in tunnel_ids:
            try:
                if not self.stop_tunnel_process(tunnel_id):
                    success = False
            except Exception as e:
                logger.error(f"Error stopping process for tunnel {tunnel_id}: {e}")
                success = False

        return success

    def get_running_process_count(self) -> int:
        """Get count of currently running processes.

        Returns:
            Number of running processes
        """
        return len(
            [
                tunnel_id
                for tunnel_id, process in self._processes.items()
                if process.is_running()
            ]
        )
