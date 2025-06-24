"""Tests for FRP server management."""

from unittest.mock import MagicMock, patch

import pytest

from frp_wrapper.server import FRPServer
from frp_wrapper.server.config import LogLevel


class TestFRPServer:
    """Test FRPServer functionality."""

    def test_initialization(self):
        """Test FRPServer initialization."""
        server = FRPServer()

        assert server.binary_path == "/usr/local/bin/frps"
        assert server._process_manager is None
        assert server._config_builder is None
        assert server._config_path is None

    def test_initialization_with_custom_binary(self):
        """Test FRPServer initialization with custom binary path."""
        server = FRPServer(binary_path="/opt/frp/frps")

        assert server.binary_path == "/opt/frp/frps"

    def test_configure_basic(self):
        """Test basic server configuration."""
        server = FRPServer()
        result = server.configure(
            bind_port=8000, bind_addr="127.0.0.1", auth_token="secure-token-12345"
        )

        # Should return self for chaining
        assert result is server

        # Config builder should be created
        assert server._config_builder is not None

        # Verify configuration was set
        assert server._config_builder._server_config.bind_port == 8000
        assert server._config_builder._server_config.bind_addr == "127.0.0.1"
        assert server._config_builder._server_config.auth_token == "secure-token-12345"

    def test_configure_with_vhost(self):
        """Test configuration with virtual host settings."""
        server = FRPServer()
        result = server.configure(
            bind_port=8000,
            vhost_http_port=8080,
            vhost_https_port=8443,
            subdomain_host="frp.example.com",
        )

        assert result is server
        assert server._config_builder._server_config.vhost_http_port == 8080
        assert server._config_builder._server_config.vhost_https_port == 8443
        assert server._config_builder._server_config.subdomain_host == "frp.example.com"

    @patch("frp_wrapper.server.server.logger")
    def test_configure_logging(self, mock_logger):
        """Test that configuration is logged."""
        server = FRPServer()
        server.configure(bind_port=8000, subdomain_host="example.com")

        mock_logger.info.assert_called_once_with(
            "Server configured", bind_port=8000, subdomain_host="example.com"
        )

    def test_enable_dashboard(self):
        """Test enabling dashboard."""
        server = FRPServer()
        server.configure()  # Must configure first

        result = server.enable_dashboard(
            port=8500, user="superadmin", password="SuperSecure123"
        )

        assert result is server
        assert server._config_builder._dashboard_config.enabled is True
        assert server._config_builder._dashboard_config.port == 8500
        assert server._config_builder._dashboard_config.user == "superadmin"
        assert server._config_builder._dashboard_config.password == "SuperSecure123"

    def test_enable_dashboard_without_configure(self):
        """Test enabling dashboard without configuring first raises error."""
        server = FRPServer()

        with pytest.raises(ValueError) as exc_info:
            server.enable_dashboard(password="Admin123")

        assert "Must call configure() first" in str(exc_info.value)

    @patch("frp_wrapper.server.server.logger")
    def test_enable_dashboard_logging(self, mock_logger):
        """Test that dashboard enabling is logged."""
        server = FRPServer()
        server.configure()
        server.enable_dashboard(port=8500, user="admin", password="Admin123")

        # First call is from configure, second from enable_dashboard
        assert mock_logger.info.call_count == 2
        second_call = mock_logger.info.call_args_list[1]
        assert second_call[0][0] == "Dashboard enabled"
        assert second_call[1]["port"] == 8500
        assert second_call[1]["user"] == "admin"

    def test_configure_logging_method(self):
        """Test configure_logging method."""
        server = FRPServer()
        server.configure()

        result = server.configure_logging(
            level=LogLevel.DEBUG, file_path="/var/log/frps.log", max_days=7
        )

        assert result is server
        assert server._config_builder._server_config.log_level == LogLevel.DEBUG
        assert server._config_builder._server_config.log_file == "/var/log/frps.log"
        assert server._config_builder._server_config.log_max_days == 7

    def test_configure_logging_without_configure(self):
        """Test configure_logging without configuring first raises error."""
        server = FRPServer()

        with pytest.raises(ValueError) as exc_info:
            server.configure_logging(level=LogLevel.DEBUG)

        assert "Must call configure() first" in str(exc_info.value)

    @patch("frp_wrapper.server.server.ServerProcessManager")
    def test_start_server(self, mock_process_manager_class):
        """Test starting the server."""
        # Mock process manager
        mock_process_manager = MagicMock()
        mock_process_manager.start.return_value = True
        mock_process_manager_class.return_value = mock_process_manager

        # Mock config builder
        mock_config_path = "/tmp/frps_config_test.toml"

        server = FRPServer()
        server.configure(bind_port=8000)
        server._config_builder.build = MagicMock(return_value=mock_config_path)

        success = server.start()

        assert success is True
        assert server._config_path == mock_config_path
        assert server._process_manager is mock_process_manager

        # Verify process manager was created with correct args
        mock_process_manager_class.assert_called_once_with(
            binary_path="/usr/local/bin/frps", config_path=mock_config_path
        )

        # Verify start was called
        mock_process_manager.start.assert_called_once()

    def test_start_without_configure(self):
        """Test starting without configuring first raises error."""
        server = FRPServer()

        with pytest.raises(ValueError) as exc_info:
            server.start()

        assert "Must call configure() first" in str(exc_info.value)

    @patch("frp_wrapper.server.server.ServerProcessManager")
    @patch("frp_wrapper.server.server.logger")
    def test_start_success_logging(self, mock_logger, mock_process_manager_class):
        """Test successful start is logged."""
        mock_process_manager = MagicMock()
        mock_process_manager.start.return_value = True
        mock_process_manager_class.return_value = mock_process_manager

        server = FRPServer()
        server.configure()
        server._config_builder.build = MagicMock(return_value="/tmp/test.toml")

        server.start()

        # Find the success log
        success_logged = False
        for call in mock_logger.info.call_args_list:
            if call[0][0] == "FRP server started successfully":
                success_logged = True
                break
        assert success_logged

    @patch("frp_wrapper.server.server.ServerProcessManager")
    @patch("frp_wrapper.server.server.logger")
    def test_start_failure_logging(self, mock_logger, mock_process_manager_class):
        """Test failed start is logged."""
        mock_process_manager = MagicMock()
        mock_process_manager.start.return_value = False
        mock_process_manager_class.return_value = mock_process_manager

        server = FRPServer()
        server.configure()
        server._config_builder.build = MagicMock(return_value="/tmp/test.toml")

        success = server.start()

        assert success is False
        mock_logger.error.assert_called_once_with("Failed to start FRP server")

    def test_stop_without_process_manager(self):
        """Test stopping when no process manager exists."""
        server = FRPServer()
        success = server.stop()

        assert success is True  # Should return True when nothing to stop

    @patch("frp_wrapper.server.server.logger")
    def test_stop_with_process_manager(self, mock_logger):
        """Test stopping with process manager."""
        server = FRPServer()

        # Mock process manager
        mock_process_manager = MagicMock()
        mock_process_manager.stop.return_value = True
        server._process_manager = mock_process_manager

        success = server.stop()

        assert success is True
        mock_process_manager.stop.assert_called_once()
        mock_logger.info.assert_called_once_with("FRP server stopped")

    @patch("frp_wrapper.server.server.logger")
    def test_stop_failure_logging(self, mock_logger):
        """Test failed stop is logged as warning."""
        server = FRPServer()

        mock_process_manager = MagicMock()
        mock_process_manager.stop.return_value = False
        server._process_manager = mock_process_manager

        success = server.stop()

        assert success is False
        mock_logger.warning.assert_called_once_with(
            "Failed to stop FRP server gracefully"
        )

    def test_is_running_without_process_manager(self):
        """Test is_running when no process manager exists."""
        server = FRPServer()
        assert server.is_running() is False

    def test_is_running_with_process_manager(self):
        """Test is_running with process manager."""
        server = FRPServer()

        mock_process_manager = MagicMock()
        mock_process_manager.is_running.return_value = True
        server._process_manager = mock_process_manager

        assert server.is_running() is True
        mock_process_manager.is_running.assert_called_once()

    def test_get_status_without_process_manager(self):
        """Test get_status when no process manager exists."""
        server = FRPServer()
        status = server.get_status()

        assert status == {"running": False, "configured": False}

        # After configuration
        server.configure()
        status = server.get_status()

        assert status == {"running": False, "configured": True}

    def test_get_status_with_process_manager(self):
        """Test get_status with process manager."""
        server = FRPServer()

        mock_process_manager = MagicMock()
        mock_status = {
            "running": True,
            "pid": 12345,
            "binary_path": "/usr/local/bin/frps",
            "config_path": "/tmp/config.toml",
        }
        mock_process_manager.get_server_status.return_value = mock_status
        server._process_manager = mock_process_manager

        status = server.get_status()

        assert status == mock_status
        mock_process_manager.get_server_status.assert_called_once()

    @patch("frp_wrapper.server.server.logger")
    def test_context_manager_entry(self, mock_logger):
        """Test context manager entry."""
        server = FRPServer()

        with server as ctx:
            assert ctx is server

        # Check debug logging
        mock_logger.debug.assert_any_call("Entering FRPServer context")

    @patch("frp_wrapper.server.server.logger")
    def test_context_manager_exit(self, mock_logger):
        """Test context manager exit."""
        server = FRPServer()

        # Mock stop method
        server.stop = MagicMock(return_value=True)

        with server:
            pass

        # Verify stop was called
        server.stop.assert_called_once()

        # Check debug logging
        mock_logger.debug.assert_any_call("Exiting FRPServer context")

    @patch("frp_wrapper.server.server.logger")
    def test_context_manager_cleanup_config(self, mock_logger):
        """Test context manager cleans up config."""
        server = FRPServer()

        # Mock config builder
        mock_config_builder = MagicMock()
        server._config_builder = mock_config_builder

        with server:
            pass

        # Verify cleanup was called
        mock_config_builder.cleanup.assert_called_once()

    @patch("frp_wrapper.server.server.logger")
    def test_context_manager_error_handling(self, mock_logger):
        """Test context manager handles errors during exit."""
        server = FRPServer()

        # Mock stop to raise exception
        server.stop = MagicMock(side_effect=Exception("Stop error"))

        with server:
            pass  # Should not raise

        # Check error was logged
        mock_logger.error.assert_called_once()
        assert "Error during context exit" in mock_logger.error.call_args[0][0]
        assert "Stop error" in mock_logger.error.call_args[1]["error"]

    def test_context_manager_does_not_suppress_exceptions(self):
        """Test context manager does not suppress user exceptions."""
        server = FRPServer()

        with pytest.raises(RuntimeError):
            with server:
                raise RuntimeError("User error")

    def test_method_chaining(self):
        """Test method chaining works correctly."""
        server = (
            FRPServer()
            .configure(bind_port=8000, auth_token="token12345")
            .enable_dashboard(password="Admin123")
            .configure_logging(level=LogLevel.DEBUG)
        )

        assert server._config_builder._server_config.bind_port == 8000
        assert server._config_builder._server_config.auth_token == "token12345"
        assert server._config_builder._dashboard_config.enabled is True
        assert server._config_builder._server_config.log_level == LogLevel.DEBUG

    @patch("frp_wrapper.server.server.ServerProcessManager")
    def test_full_lifecycle(self, mock_process_manager_class):
        """Test full server lifecycle."""
        # Mock process manager
        mock_process_manager = MagicMock()
        mock_process_manager.start.return_value = True
        mock_process_manager.is_running.return_value = True
        mock_process_manager.stop.return_value = True
        mock_process_manager.get_server_status.return_value = {
            "running": True,
            "pid": 12345,
        }
        mock_process_manager_class.return_value = mock_process_manager

        # Create and configure server
        server = FRPServer()
        server.configure(bind_port=8000, subdomain_host="frp.example.com")
        server.enable_dashboard(password="Admin123")

        # Start server
        assert server.start() is True
        assert server.is_running() is True

        # Get status
        status = server.get_status()
        assert status["running"] is True
        assert status["pid"] == 12345

        # Stop server
        assert server.stop() is True
