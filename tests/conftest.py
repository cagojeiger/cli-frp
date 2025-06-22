"""Shared pytest fixtures for FRP wrapper tests."""

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess.Popen for testing process management.

    Returns:
        Mock: Mocked Popen class
    """
    mock_popen = Mock()
    monkeypatch.setattr("subprocess.Popen", mock_popen)
    return mock_popen


@pytest.fixture
def temp_paths(tmp_path):
    """Create temporary binary and config paths for testing.

    Args:
        tmp_path: pytest's tmp_path fixture

    Returns:
        tuple: (binary_path, config_path) as Path objects
    """
    # Create temporary binary file
    binary_path = tmp_path / "frpc"
    binary_path.touch(mode=0o755)

    # Create temporary config file
    config_path = tmp_path / "config.toml"
    config_content = """[common]
server_addr = "test.example.com"
server_port = 7000
token = "test_token"
"""
    config_path.write_text(config_content)

    return binary_path, config_path


@pytest.fixture
def mock_process():
    """Create a mock process object for testing.

    Returns:
        Mock: Mock process with common attributes
    """
    process = Mock()
    process.pid = 12345
    process.poll.return_value = None  # Process is running
    process.terminate.return_value = None
    process.kill.return_value = None
    process.wait.return_value = 0
    process.stdout = Mock()
    process.stderr = Mock()
    return process


@pytest.fixture
def running_process_manager(temp_paths, mock_subprocess, mock_process):
    """Create a ProcessManager with a running mock process.

    Args:
        temp_paths: Temporary file paths
        mock_subprocess: Mocked subprocess.Popen
        mock_process: Mock process object

    Returns:
        ProcessManager: Manager with running process
    """
    from frp_wrapper.process import ProcessManager  # noqa: PLC0415

    binary_path, config_path = temp_paths
    mock_subprocess.return_value = mock_process

    manager = ProcessManager(str(binary_path), str(config_path))
    manager.start()

    return manager


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock the logger to capture log messages.

    Returns:
        Mock: Mocked logger
    """
    mock_log = Mock()
    monkeypatch.setattr("frp_wrapper.process.logger", mock_log)
    return mock_log


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration after each test.

    This prevents tests from interfering with each other's logging setup.
    """
    yield
    # Reset is handled automatically by pytest's isolation
