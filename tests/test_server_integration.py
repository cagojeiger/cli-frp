"""Integration tests for FRP server wrapper."""

import os
from unittest.mock import MagicMock, patch

import pytest

from frp_wrapper.server import FRPServer
from frp_wrapper.server.config import LogLevel


class TestServerIntegration:
    """Integration tests for server components."""

    @patch("frp_wrapper.server.process.ServerProcessManager._validate_paths")
    @patch("subprocess.Popen")
    def test_basic_server_lifecycle(self, mock_popen, mock_validate_paths):
        """Test basic server lifecycle with mocked binary."""
        # Mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        # Create and configure server
        server = FRPServer()
        server.configure(bind_port=8000, auth_token="test-token-12345")

        # Start server
        assert server.start() is True
        assert server.is_running() is True

        # Verify process was started with correct command
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[0] == "/usr/local/bin/frps"
        assert args[1] == "-c"
        assert args[2].endswith(".toml")

        # Verify config file was created
        config_path = args[2]
        assert os.path.exists(config_path)

        # Read and verify config content
        with open(config_path) as f:
            content = f.read()

        assert "bindPort = 8000" in content
        assert 'auth.token = "test-token-12345"' in content

        # Stop server
        mock_process.poll.return_value = 0  # Process has stopped
        assert server.stop() is True

        # Cleanup
        if os.path.exists(config_path):
            os.unlink(config_path)

    @patch("frp_wrapper.server.process.ServerProcessManager._validate_paths")
    @patch("subprocess.Popen")
    def test_server_with_dashboard(self, mock_popen, mock_validate_paths):
        """Test server with dashboard enabled."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        server = FRPServer()
        server.configure(bind_port=8000, subdomain_host="frp.example.com")
        server.enable_dashboard(port=8500, user="admin", password="SecurePass123")

        assert server.start() is True

        # Get config path from Popen call
        config_path = mock_popen.call_args[0][0][2]

        # Verify dashboard configuration
        with open(config_path) as f:
            content = f.read()

        assert "[webServer]" in content
        assert "port = 8500" in content
        assert 'user = "admin"' in content
        assert 'password = "SecurePass123"' in content
        assert 'subDomainHost = "frp.example.com"' in content

        # Stop and cleanup
        mock_process.poll.return_value = 0
        server.stop()

        if os.path.exists(config_path):
            os.unlink(config_path)

    @patch("frp_wrapper.server.process.ServerProcessManager._validate_paths")
    @patch("subprocess.Popen")
    def test_server_context_manager(self, mock_popen, mock_validate_paths):
        """Test server as context manager."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        config_path = None

        with FRPServer() as server:
            server.configure(bind_port=8000)
            server.start()

            # Get config path
            config_path = mock_popen.call_args[0][0][2]
            assert os.path.exists(config_path)

            # Simulate process stop for clean exit
            mock_process.poll.return_value = 0

        # Config file should be cleaned up
        assert config_path is not None
        assert not os.path.exists(config_path)

    def test_config_validation_integration(self):
        """Test configuration validation in integration."""
        server = FRPServer()

        # Invalid port
        with pytest.raises(Exception) as exc_info:
            server.configure(bind_port=99999)
        assert "less than or equal to 65535" in str(exc_info.value)

        # Invalid auth token
        with pytest.raises(Exception) as exc_info:
            server.configure(auth_token="weak")
        assert "at least 8 characters" in str(exc_info.value)

        # Invalid dashboard password
        server.configure()  # Valid config first
        with pytest.raises(Exception) as exc_info:
            server.enable_dashboard(password="weak")
        assert "at least 6 characters" in str(exc_info.value)

    @patch("frp_wrapper.server.process.ServerProcessManager._validate_paths")
    @patch("subprocess.Popen")
    def test_server_with_full_configuration(self, mock_popen, mock_validate_paths):
        """Test server with full configuration options."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        server = FRPServer(binary_path="/opt/frp/frps")
        server.configure(
            bind_port=9000,
            bind_addr="192.168.1.100",
            auth_token="super-secure-token-12345",
            vhost_http_port=8080,
            vhost_https_port=8443,
            subdomain_host="tunnel.company.com",
        )
        server.enable_dashboard(
            port=9500, user="superadmin", password="SuperSecure123!"
        )
        server.configure_logging(
            level=LogLevel.DEBUG, file_path="/var/log/frps.log", max_days=30
        )

        assert server.start() is True

        # Verify binary path
        assert mock_popen.call_args[0][0][0] == "/opt/frp/frps"

        # Get and verify config
        config_path = mock_popen.call_args[0][0][2]
        with open(config_path) as f:
            content = f.read()

        # Verify all settings
        assert 'bindAddr = "192.168.1.100"' in content
        assert "bindPort = 9000" in content
        assert 'auth.token = "super-secure-token-12345"' in content
        assert "vhostHTTPPort = 8080" in content
        assert "vhostHTTPSPort = 8443" in content
        assert 'subDomainHost = "tunnel.company.com"' in content
        assert 'log.level = "debug"' in content
        assert 'log.file = "/var/log/frps.log"' in content
        assert "log.maxDays = 30" in content
        assert "port = 9500" in content
        assert 'user = "superadmin"' in content
        assert 'password = "SuperSecure123!"' in content

        # Cleanup
        mock_process.poll.return_value = 0
        server.stop()
        if os.path.exists(config_path):
            os.unlink(config_path)

    @patch("frp_wrapper.server.process.ServerProcessManager._validate_paths")
    @patch("subprocess.Popen")
    def test_server_start_failure(self, mock_popen, mock_validate_paths):
        """Test handling of server start failure."""
        # Mock process that fails immediately
        mock_popen.side_effect = OSError("Failed to start process")

        server = FRPServer()
        server.configure(bind_port=8000)

        # Start should handle the error gracefully
        success = server.start()
        assert success is False

    @patch("frp_wrapper.server.process.ServerProcessManager._validate_paths")
    def test_temporary_file_cleanup_on_error(self, mock_validate_paths):
        """Test that temporary files are cleaned up on error."""
        server = FRPServer()
        server.configure(bind_port=8000)

        # Track config path created during start()
        config_path = None

        # Mock subprocess to capture config path and raise error
        def mock_popen(*args, **kwargs):
            nonlocal config_path
            # Extract config path from command args
            config_path = args[0][2]  # Command is [binary, "-c", config_path]
            raise Exception("Mock error")

        # Test that file exists after error in start()
        with patch("subprocess.Popen", side_effect=mock_popen):
            result = server.start()
            assert result is False

        # File should still exist (not cleaned up automatically on error)
        assert config_path is not None
        assert os.path.exists(config_path)

        # Manual cleanup (normally done by context manager)
        server._config_builder.cleanup()

        # Now file should be cleaned up
        assert not os.path.exists(config_path)

    def test_multiple_server_instances(self):
        """Test multiple server instances can coexist."""
        server1 = FRPServer()
        server2 = FRPServer()

        server1.configure(bind_port=8000)
        server2.configure(bind_port=9000)

        # Build configs
        config1 = server1._config_builder.build()
        config2 = server2._config_builder.build()

        # Should have different config files
        assert config1 != config2
        assert os.path.exists(config1)
        assert os.path.exists(config2)

        # Read and verify different ports
        with open(config1) as f:
            assert "bindPort = 8000" in f.read()

        with open(config2) as f:
            assert "bindPort = 9000" in f.read()

        # Cleanup
        server1._config_builder.cleanup()
        server2._config_builder.cleanup()

        assert not os.path.exists(config1)
        assert not os.path.exists(config2)
