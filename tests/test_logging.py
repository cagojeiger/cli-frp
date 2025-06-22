"""Test logging configuration."""

import logging
from pathlib import Path

import structlog
from structlog.testing import LogCapture

from frp_wrapper.logging import get_logger, setup_logging


class TestLogging:
    """Test logging functionality."""

    def test_setup_logging_default(self) -> None:
        """Test default logging setup."""
        setup_logging()
        logger = get_logger("test")
        # Just check that we get a logger object
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")

    def setup_method(self) -> None:
        """Setup before each test - reset logging configuration."""
        structlog.reset_defaults()
        # Reset logging handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def test_setup_logging_with_level(self) -> None:
        """Test logging setup with custom level."""
        setup_logging(level="DEBUG")
        # After setup_logging, the root logger should have DEBUG level
        assert logging.getLogger().level == logging.DEBUG

    def test_setup_logging_json_format(self) -> None:
        """Test logging setup with JSON format."""
        setup_logging(json_format=True)
        logger = get_logger("test")

        # Capture logs
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger.info("test message", key="value")

        assert len(cap.entries) == 1
        assert cap.entries[0]["event"] == "test message"
        assert cap.entries[0]["key"] == "value"

    def test_setup_logging_with_file(self, tmp_path: Path) -> None:
        """Test logging setup with file output."""
        log_file = tmp_path / "test.log"
        setup_logging(log_file=str(log_file))

        # Get a Python logger to verify file handler
        python_logger = logging.getLogger("test_file")
        python_logger.info("test message")

        # Force flush
        for handler in logging.getLogger().handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        assert log_file.exists()
        log_contents = log_file.read_text()
        assert "test message" in log_contents

    def test_get_logger(self) -> None:
        """Test getting a logger instance."""
        setup_logging()  # Make sure logging is set up first
        logger = get_logger("test_module")
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "error")
