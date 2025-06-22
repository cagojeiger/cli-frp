"""Process management for FRP binary."""

import subprocess
import threading
import time
from pathlib import Path
from typing import Optional, Callable

from .exceptions import ProcessError, BinaryNotFoundError


class ProcessManager:
    """Manages FRP binary process lifecycle"""

    def __init__(self, binary_path: str, config_path: str):
        """Initialize ProcessManager with binary and config paths

        Args:
            binary_path: Path to frpc binary
            config_path: Path to FRP configuration file

        Raises:
            BinaryNotFoundError: If binary doesn't exist or isn't executable
            ValueError: If paths are invalid
        """
        self.binary_path = binary_path
        self.config_path = config_path
        self._process: Optional[subprocess.Popen] = None
        self._validate_paths()

    def _validate_paths(self) -> None:
        """Validate binary and config paths"""
        binary_path = Path(self.binary_path)
        config_path = Path(self.config_path)
        
        if not binary_path.exists():
            raise BinaryNotFoundError(f"Binary not found: {self.binary_path}")
        
        if not binary_path.is_file():
            raise BinaryNotFoundError(f"Binary path is not a file: {self.binary_path}")
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

    def start(self) -> bool:
        """Start FRP process

        Returns:
            True if started successfully, False otherwise

        Raises:
            ProcessError: If process fails to start
        """
        if self.is_running():
            return True
        
        try:
            self._process = subprocess.Popen(
                [self.binary_path, "-c", self.config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return True
        except OSError as e:
            raise ProcessError(f"Failed to start FRP process: {e}")

    def stop(self) -> bool:
        """Stop FRP process gracefully

        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.is_running():
            return True
        
        if self._process is None:
            return True
        
        try:
            self._process.terminate()
            try:
                self._process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
                try:
                    self._process.wait()
                except subprocess.TimeoutExpired:
                    pass
            
            self._process = None
            return True
        except Exception:
            self._process = None
            return False

    def restart(self) -> bool:
        """Restart FRP process

        Returns:
            True if restarted successfully, False otherwise
        """
        self.stop()
        return self.start()

    def is_running(self) -> bool:
        """Check if process is currently running"""
        if self._process is None:
            return False
        
        return self._process.poll() is None

    @property
    def pid(self) -> Optional[int]:
        """Get process ID if running"""
        if self.is_running() and self._process:
            return self._process.pid
        return None

    def wait_for_startup(self, timeout: float = 10.0) -> bool:
        """Wait for process to fully start up"""
        if not self.is_running():
            return False
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._check_startup_success():
                return True
            time.sleep(0.1)
        
        return False

    def _check_startup_success(self) -> bool:
        """Check if process has started successfully"""
        if not self.is_running():
            return False
        
        time.sleep(0.1)
        return self.is_running()
