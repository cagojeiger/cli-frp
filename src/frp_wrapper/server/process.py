"""Server process management for FRP server."""

from typing import Any

from ..client.process import ProcessManager
from ..common.logging import get_logger

logger = get_logger(__name__)


class ServerProcessManager(ProcessManager):
    """FRP server process management (ProcessManager pattern reuse)."""

    def __init__(self, binary_path: str = "/usr/local/bin/frps", config_path: str = ""):
        """Initialize ServerProcessManager.

        Args:
            binary_path: Path to frps binary (default: /usr/local/bin/frps)
            config_path: Path to FRP server configuration file
        """
        super().__init__(binary_path, config_path)
        logger.info("ServerProcessManager initialized", binary_path=binary_path)

    def get_server_status(self) -> dict[str, Any]:
        """Get detailed server status."""
        return {
            "running": self.is_running(),
            "pid": self.pid,
            "binary_path": self.binary_path,
            "config_path": self.config_path,
        }
