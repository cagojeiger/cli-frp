"""Tests for FRP server process management."""

from unittest.mock import MagicMock, patch

from frp_wrapper.client.process import ProcessManager
from frp_wrapper.server.process import ServerProcessManager


class TestServerProcessManager:
    """Test ServerProcessManager functionality."""

    def test_inheritance(self):
        """Test that ServerProcessManager inherits from ProcessManager."""
        assert issubclass(ServerProcessManager, ProcessManager)

    def test_default_binary_path(self):
        """Test default binary path is set to frps."""
        # Create a mock for path validation
        with patch.object(ServerProcessManager, "_validate_paths"):
            manager = ServerProcessManager(config_path="config.toml")
            assert manager.binary_path == "/usr/local/bin/frps"

    def test_custom_binary_path(self):
        """Test custom binary path can be set."""
        with patch.object(ServerProcessManager, "_validate_paths"):
            manager = ServerProcessManager(
                binary_path="/opt/frp/frps", config_path="config.toml"
            )
            assert manager.binary_path == "/opt/frp/frps"

    def test_config_path_passed(self):
        """Test config path is passed correctly."""
        with patch.object(ServerProcessManager, "_validate_paths"):
            manager = ServerProcessManager(config_path="/etc/frp/server.toml")
            assert manager.config_path == "/etc/frp/server.toml"

    @patch("frp_wrapper.server.process.logger")
    def test_initialization_logging(self, mock_logger):
        """Test that initialization is logged."""
        with patch.object(ServerProcessManager, "_validate_paths"):
            ServerProcessManager(config_path="config.toml")

        mock_logger.info.assert_called_once_with(
            "ServerProcessManager initialized", binary_path="/usr/local/bin/frps"
        )

    def test_get_server_status(self):
        """Test get_server_status method."""
        with patch.object(ServerProcessManager, "_validate_paths"):
            manager = ServerProcessManager(config_path="config.toml")
            manager._process = MagicMock()
            manager._process.poll.return_value = None  # Process is running
            manager._process.pid = 12345

            status = manager.get_server_status()

            assert status == {
                "running": True,
                "pid": 12345,
                "binary_path": "/usr/local/bin/frps",
                "config_path": "config.toml",
            }

    def test_get_server_status_not_running(self):
        """Test get_server_status when server is not running."""
        with patch.object(ServerProcessManager, "_validate_paths"):
            manager = ServerProcessManager(config_path="config.toml")
            manager._process = None

            status = manager.get_server_status()

            assert status == {
                "running": False,
                "pid": None,
                "binary_path": "/usr/local/bin/frps",
                "config_path": "config.toml",
            }

    def test_all_process_manager_methods_available(self):
        """Test that all ProcessManager methods are available."""
        with patch.object(ServerProcessManager, "_validate_paths"):
            manager = ServerProcessManager(config_path="config.toml")

            # Check that key methods exist
            assert hasattr(manager, "start")
            assert hasattr(manager, "stop")
            assert hasattr(manager, "is_running")
            assert hasattr(manager, "wait_for_startup")
            assert hasattr(manager, "__enter__")
            assert hasattr(manager, "__exit__")

    @patch("frp_wrapper.server.process.ServerProcessManager._validate_paths")
    @patch("subprocess.Popen")
    @patch("os.path.exists", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.access", return_value=True)
    def test_start_server_process(
        self, mock_access, mock_isfile, mock_exists, mock_popen, mock_validate_paths
    ):
        """Test starting server process uses frps binary."""
        # Mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        manager = ServerProcessManager(config_path="config.toml")
        success = manager.start()

        assert success is True

        # Verify Popen was called with frps
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args == ["/usr/local/bin/frps", "-c", "config.toml"]

    def test_context_manager_support(self):
        """Test ServerProcessManager works as context manager."""
        with patch.object(ServerProcessManager, "_validate_paths"):
            with patch.object(ServerProcessManager, "start", return_value=True):
                with patch.object(
                    ServerProcessManager, "wait_for_startup", return_value=True
                ):
                    with patch.object(
                        ServerProcessManager, "stop", return_value=True
                    ) as mock_stop:
                        with ServerProcessManager(config_path="config.toml") as manager:
                            assert isinstance(manager, ServerProcessManager)

                        # Verify stop was called on exit
                        mock_stop.assert_called_once()
