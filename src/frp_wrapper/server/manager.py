"""Server process management for FRP server.

This module provides ServerManager class for managing FRP server (frps) process
lifecycle, including start, stop, restart, configuration reloading, and monitoring.
"""

import os
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .config import CompleteServerConfig


class ServerStatus(str, Enum):
    """FRP server status enumeration"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class ServerManager:
    """Manages FRP server process lifecycle and configuration.

    This class provides comprehensive server management including:
    - Process lifecycle (start, stop, restart)
    - Configuration management and reloading
    - Status monitoring and health checks
    - Context manager support for automatic cleanup
    """

    def __init__(
        self,
        config_path: str | None = None,
        config: CompleteServerConfig | None = None,
        binary_path: str | None = None
    ):
        """Initialize ServerManager.

        Args:
            config_path: Path to TOML configuration file
            config: CompleteServerConfig object
            binary_path: Path to frps binary (auto-discovered if None)

        Raises:
            ValueError: If neither or both config_path and config are provided
        """
        if not config_path and not config:
            raise ValueError("Either config_path or config must be provided")

        if config_path and config:
            raise ValueError("Cannot provide both config_path and config")

        self.config_path = config_path
        self.config = config
        self.binary_path = binary_path

        self._process: subprocess.Popen[str] | None = None
        self._status = ServerStatus.STOPPED
        self._start_time: datetime | None = None
        self._temp_config_file: Any | None = None

    @property
    def status(self) -> ServerStatus:
        """Get current server status"""
        self._update_status()
        return self._status

    @property
    def pid(self) -> int | None:
        """Get server process PID"""
        return self._process.pid if self._process else None

    def _find_binary(self) -> str:
        """Find FRP server binary.

        Returns:
            Path to frps binary

        Raises:
            FileNotFoundError: If binary cannot be found
        """
        if self.binary_path:
            if Path(self.binary_path).exists():
                return self.binary_path
            else:
                raise FileNotFoundError(f"FRP server binary not found at {self.binary_path}")

        binary_path = shutil.which('frps')
        if binary_path:
            return binary_path

        env_path = os.environ.get('FRP_SERVER_BINARY_PATH')
        if env_path and Path(str(env_path)).exists():
            return env_path

        common_paths = [
            "/usr/local/bin/frps",
            "/opt/frp/frps",
            "/usr/bin/frps",
            Path.home() / "bin" / "frps",
        ]

        for path in common_paths:
            if Path(str(path)).exists():
                return str(path)

        raise FileNotFoundError(
            "FRP server binary (frps) not found. Please install FRP or set FRP_SERVER_BINARY_PATH environment variable."
        )

    def _get_config_path(self) -> str:
        """Get configuration file path.

        Returns:
            Path to configuration file
        """
        if self.config_path:
            return self.config_path

        if not self._temp_config_file and self.config:
            self._temp_config_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.toml',
                delete=False
            )
            toml_content = self.config.generate_toml()
            self._temp_config_file.write(toml_content)
            self._temp_config_file.flush()

        return self._temp_config_file.name if self._temp_config_file else ""

    def _update_status(self) -> None:
        """Update server status based on process state"""
        if not self._process:
            self._status = ServerStatus.STOPPED
            return

        poll_result = self._process.poll()
        if poll_result is None:
            if self._status == ServerStatus.STARTING:
                bind_port = 7000  # Default port
                if self.config:
                    bind_port = self.config.server.bind_port

                if self._is_port_in_use(bind_port):
                    self._status = ServerStatus.RUNNING
            elif self._status not in [ServerStatus.RUNNING, ServerStatus.STOPPING]:
                self._status = ServerStatus.RUNNING
        else:
            if poll_result == 0:
                self._status = ServerStatus.STOPPED
            else:
                self._status = ServerStatus.ERROR
            self._process = None

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use.

        Args:
            port: Port number to check

        Returns:
            True if port is in use, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                result = sock.connect_ex(('localhost', port))
                return result == 0
        except Exception:
            return False

    def start(self) -> bool:
        """Start the FRP server.

        Returns:
            True if server started successfully, False otherwise

        Raises:
            FileNotFoundError: If FRP binary cannot be found
        """
        if self._status == ServerStatus.RUNNING:
            return True

        try:
            binary_path = self._find_binary()
            config_path = self._get_config_path()

            self._status = ServerStatus.STARTING

            self._process = subprocess.Popen(
                [binary_path, "-c", config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            self._start_time = datetime.now()

            time.sleep(0.5)

            self._update_status()

            return self._status == ServerStatus.RUNNING

        except Exception as e:
            self._status = ServerStatus.ERROR
            if isinstance(e, FileNotFoundError):
                raise
            return False

    def stop(self, timeout: float = 5.0) -> bool:
        """Stop the FRP server.

        Args:
            timeout: Maximum time to wait for graceful shutdown

        Returns:
            True if server stopped successfully, False otherwise
        """
        if self._status == ServerStatus.STOPPED:
            return True

        if not self._process:
            self._status = ServerStatus.STOPPED
            return True

        try:
            self._status = ServerStatus.STOPPING

            self._process.terminate()

            start_time = time.time()
            while time.time() - start_time < timeout:
                if self._process.poll() is not None:
                    break
                time.sleep(0.1)

            if self._process.poll() is None:
                self._process.kill()
                self._process.wait()

            self._process = None
            self._status = ServerStatus.STOPPED

            if self._temp_config_file:
                try:
                    temp_path = self._temp_config_file.name
                    self._temp_config_file.close()
                    Path(temp_path).unlink(missing_ok=True)
                    self._temp_config_file = None
                except Exception:
                    pass

            return True

        except Exception:
            self._status = ServerStatus.ERROR
            return False

    def restart(self) -> bool:
        """Restart the FRP server.

        Returns:
            True if server restarted successfully, False otherwise
        """
        if not self.stop():
            return False

        return self.start()

    def reload_config(self) -> bool:
        """Reload server configuration without restarting.

        Uses SIGHUP signal to reload configuration.

        Returns:
            True if config reloaded successfully, False otherwise
        """
        if self._status != ServerStatus.RUNNING or not self._process:
            return False

        try:
            self._process.send_signal(signal.SIGHUP)
            return True
        except Exception:
            return False

    def get_server_info(self) -> dict[str, Any]:
        """Get comprehensive server information.

        Returns:
            Dictionary containing server status and configuration info
        """
        info = {
            'status': self.status.value,
            'pid': self.pid,
            'start_time': self._start_time.isoformat() if self._start_time else None,
            'config_path': self.config_path or (self._temp_config_file.name if self._temp_config_file else None),
        }

        if self.config:
            info.update({
                'bind_port': self.config.server.bind_port,
                'vhost_http_port': self.config.server.vhost_http_port,
                'vhost_https_port': self.config.server.vhost_https_port,
                'subdomain_host': self.config.server.subdomain_host,
                'dashboard_enabled': self.config.dashboard.enabled,
                'ssl_enabled': self.config.ssl.enabled,
            })

        return info

    def __enter__(self) -> 'ServerManager':
        """Context manager entry"""
        if not self.start():
            raise RuntimeError("Failed to start FRP server")
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object | None) -> None:
        """Context manager exit"""
        self.stop()

    def __del__(self) -> None:
        """Cleanup on deletion"""
        if hasattr(self, '_process') and self._process:
            try:
                self.stop()
            except Exception:
                pass
