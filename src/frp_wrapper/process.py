"""Process management for FRP binary."""

import os
import subprocess
import time
from pathlib import Path
from types import TracebackType
from typing import Literal

from .exceptions import BinaryNotFoundError, ProcessError
from .logging import get_logger

logger = get_logger(__name__)


class ProcessManager:
    """Manages FRP binary process lifecycle with context manager support"""

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
        self._process: subprocess.Popen[str] | None = None
        self._validate_paths()
        logger.info(
            "ProcessManager initialized",
            binary_path=binary_path,
            config_path=config_path,
        )

    def _validate_paths(self) -> None:
        """Validate binary and config paths"""
        binary_path = Path(self.binary_path)
        config_path = Path(self.config_path)

        if not binary_path.exists():
            raise BinaryNotFoundError(f"Binary not found: {self.binary_path}")

        if not binary_path.is_file():
            raise BinaryNotFoundError(f"Binary path is not a file: {self.binary_path}")

        # Check if binary is executable
        if not os.access(self.binary_path, os.X_OK):
            raise BinaryNotFoundError(f"Binary is not executable: {self.binary_path}")

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
            logger.debug("Process already running", pid=self.pid)
            return True

        logger.info("Starting FRP process", binary_path=self.binary_path)
        try:
            self._process = subprocess.Popen(
                [self.binary_path, "-c", self.config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.info("FRP process started successfully", pid=self._process.pid)
            return True
        except OSError as e:
            logger.error("Failed to start FRP process", error=str(e))
            raise ProcessError(f"Failed to start FRP process: {e}") from e

    def stop(self) -> bool:
        """Stop FRP process gracefully

        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.is_running():
            logger.debug("Process not running, nothing to stop")
            return True

        if self._process is None:
            return True

        logger.info("Stopping FRP process", pid=self.pid)
        try:
            self._process.terminate()
            try:
                self._process.wait(timeout=5.0)
                logger.info("FRP process terminated gracefully")
            except subprocess.TimeoutExpired:
                logger.warning(
                    "Process did not terminate gracefully, force killing", pid=self.pid
                )
                self._process.kill()
                try:
                    self._process.wait()
                except subprocess.TimeoutExpired:
                    logger.error("Failed to kill process", pid=self.pid)
                    pass

            self._process = None
            return True
        except Exception as e:
            logger.error("Error stopping process", error=str(e))
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
    def pid(self) -> int | None:
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

    def __enter__(self) -> "ProcessManager":
        """Context manager entry - automatically start process

        Returns:
            Self for use in with statement

        Raises:
            ProcessError: If process fails to start
        """
        logger.debug("Entering ProcessManager context")
        self.start()
        if not self.wait_for_startup():
            raise ProcessError("Process failed to start within timeout")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        """Context manager exit - automatically stop process

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        Returns:
            False to propagate any exception
        """
        logger.debug("Exiting ProcessManager context")
        try:
            self.stop()
        except Exception as e:
            logger.error("Error during context exit", error=str(e))
        return False  # Don't suppress exceptions
