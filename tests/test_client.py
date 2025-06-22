import os
from unittest.mock import Mock, patch

import pytest

from frp_wrapper.common.exceptions import (
    AuthenticationError,
    BinaryNotFoundError,
    ConnectionError,
)
from frp_wrapper.core.client import FRPClient


class TestFRPClient:
    def test_client_requires_server_address(self):
        """FRPClient should validate server address"""
        with pytest.raises(ValueError, match="Server address cannot be empty"):
            FRPClient("")

        with pytest.raises(ValueError, match="Server address cannot be empty"):
            FRPClient("   ")  # Whitespace only

    def test_client_validates_port(self):
        """FRPClient should validate port number"""
        with pytest.raises(ValueError, match="Server port must be between 1 and 65535"):
            FRPClient("example.com", port=0)

        with pytest.raises(ValueError, match="Server port must be between 1 and 65535"):
            FRPClient("example.com", port=65536)

    @patch("frp_wrapper.core.client.FRPClient.find_frp_binary")
    def test_client_initialization_success(self, mock_find_binary):
        """FRPClient should initialize successfully with valid parameters"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"

        client = FRPClient("example.com", port=7000, auth_token="secret123")

        assert client.server == "example.com"
        assert client.port == 7000
        assert client.auth_token == "secret123"
        assert not client.is_connected()
        mock_find_binary.assert_called_once()

    @patch("frp_wrapper.core.client.FRPClient.find_frp_binary")
    def test_client_auto_finds_binary(self, mock_find_binary):
        """FRPClient should automatically find FRP binary"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"

        client = FRPClient("example.com")

        assert client.binary_path == "/usr/local/bin/frpc"
        mock_find_binary.assert_called_once()

    def test_client_uses_custom_binary_path(self):
        """FRPClient should use provided binary path"""
        custom_path = "/custom/path/to/frpc"

        client = FRPClient("example.com", binary_path=custom_path)

        assert client.binary_path == custom_path

    @patch("frp_wrapper.core.client.FRPClient.find_frp_binary")
    def test_client_handles_missing_binary(self, mock_find_binary):
        """FRPClient should handle missing FRP binary"""
        mock_find_binary.side_effect = BinaryNotFoundError("frpc binary not found")

        with pytest.raises(BinaryNotFoundError):
            FRPClient("example.com")

    @patch("frp_wrapper.core.client.FRPClient.find_frp_binary")
    @patch("frp_wrapper.core.client.ProcessManager")
    @patch("frp_wrapper.core.client.ConfigBuilder")
    def test_client_connects_successfully(
        self, mock_config_builder, mock_process_manager, mock_find_binary
    ):
        """FRPClient should connect to server successfully"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"
        mock_config = Mock()
        mock_config_builder.return_value = mock_config
        mock_config.build.return_value = "/tmp/test.toml"

        mock_process = Mock()
        mock_process_manager.return_value = mock_process
        mock_process.start.return_value = True
        mock_process.wait_for_startup.return_value = True
        mock_process.is_running.return_value = True  # Add this for is_connected()

        client = FRPClient("example.com", auth_token="secret")
        result = client.connect()

        assert result is True
        assert client.is_connected()
        mock_config.add_server.assert_called_with("example.com", 7000, "secret")
        mock_process.start.assert_called_once()

    @patch("frp_wrapper.core.client.FRPClient.find_frp_binary")
    @patch("frp_wrapper.core.client.ProcessManager")
    @patch("frp_wrapper.core.client.ConfigBuilder")
    def test_client_connect_when_already_connected(
        self, mock_config_builder, mock_process_manager, mock_find_binary
    ):
        """FRPClient should return True when already connected"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"
        mock_config = Mock()
        mock_config_builder.return_value = mock_config
        mock_config.build.return_value = "/tmp/test.toml"

        mock_process = Mock()
        mock_process_manager.return_value = mock_process
        mock_process.start.return_value = True
        mock_process.wait_for_startup.return_value = True
        mock_process.is_running.return_value = True  # Add this for is_connected()

        client = FRPClient("example.com")
        client.connect()  # First connection

        result = client.connect()  # Second connection attempt

        assert result is True
        assert mock_process.start.call_count == 1  # Should only start once

    @patch("frp_wrapper.core.client.FRPClient.find_frp_binary")
    @patch("frp_wrapper.core.client.ProcessManager")
    @patch("frp_wrapper.core.client.ConfigBuilder")
    def test_client_handles_process_start_failure(
        self, mock_config_builder, mock_process_manager, mock_find_binary
    ):
        """FRPClient should handle process start failure"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"
        mock_config = Mock()
        mock_config_builder.return_value = mock_config
        mock_config.build.return_value = "/tmp/test.toml"

        mock_process = Mock()
        mock_process_manager.return_value = mock_process
        mock_process.start.return_value = False  # Process fails to start

        client = FRPClient("example.com")

        with pytest.raises(ConnectionError, match="Failed to start FRP process"):
            client.connect()

    @patch("frp_wrapper.core.client.FRPClient.find_frp_binary")
    @patch("frp_wrapper.core.client.ProcessManager")
    def test_client_handles_connection_failure(
        self, mock_process_manager, mock_find_binary
    ):
        """FRPClient should handle connection failures"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"
        mock_process = Mock()
        mock_process_manager.return_value = mock_process
        mock_process.start.side_effect = OSError("Connection refused")

        client = FRPClient("invalid.server.com")

        with pytest.raises(ConnectionError, match="Failed to connect"):
            client.connect()

        assert not client.is_connected()

    @patch("frp_wrapper.core.client.FRPClient.find_frp_binary")
    @patch("frp_wrapper.core.client.ProcessManager")
    def test_client_handles_authentication_failure(
        self, mock_process_manager, mock_find_binary
    ):
        """FRPClient should handle authentication failures"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"
        mock_process = Mock()
        mock_process_manager.return_value = mock_process
        mock_process.start.return_value = True
        mock_process.wait_for_startup.return_value = (
            False  # Startup failed = auth issue
        )

        client = FRPClient("example.com", auth_token="invalid_token")

        with pytest.raises(AuthenticationError, match="Authentication failed"):
            client.connect()

    @patch("frp_wrapper.core.client.FRPClient.find_frp_binary")
    @patch("frp_wrapper.core.client.ProcessManager")
    def test_client_disconnects_successfully(
        self, mock_process_manager, mock_find_binary
    ):
        """FRPClient should disconnect from server"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"
        mock_process = Mock()
        mock_process_manager.return_value = mock_process
        mock_process.start.return_value = True
        mock_process.wait_for_startup.return_value = True
        mock_process.is_running.return_value = True  # Add this for is_connected()
        mock_process.stop.return_value = True

        client = FRPClient("example.com")
        client.connect()

        result = client.disconnect()

        assert result is True
        assert not client.is_connected()
        mock_process.stop.assert_called_once()

    @patch("frp_wrapper.core.client.FRPClient.find_frp_binary")
    def test_client_disconnect_when_not_connected(self, mock_find_binary):
        """FRPClient should handle disconnect when not connected"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"

        client = FRPClient("example.com")

        result = client.disconnect()

        assert result is True
        assert not client.is_connected()

    @patch("frp_wrapper.core.client.FRPClient.find_frp_binary")
    @patch("frp_wrapper.core.client.ProcessManager")
    def test_client_disconnect_handles_exception(
        self, mock_process_manager, mock_find_binary
    ):
        """FRPClient should handle exceptions during disconnect"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"
        mock_process = Mock()
        mock_process_manager.return_value = mock_process
        mock_process.start.return_value = True
        mock_process.wait_for_startup.return_value = True
        mock_process.is_running.return_value = True  # Add this for is_connected()
        mock_process.stop.side_effect = Exception("Stop failed")

        client = FRPClient("example.com")
        client.connect()

        result = client.disconnect()

        assert result is False  # Should return False on exception
        assert not client.is_connected()  # Should still mark as disconnected

    @patch("frp_wrapper.core.client.FRPClient.find_frp_binary")
    @patch("frp_wrapper.core.client.ProcessManager")
    def test_client_context_manager(self, mock_process_manager, mock_find_binary):
        """FRPClient should work as context manager"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"
        mock_process = Mock()
        mock_process_manager.return_value = mock_process
        mock_process.start.return_value = True
        mock_process.wait_for_startup.return_value = True
        mock_process.is_running.return_value = True  # Add this for is_connected()
        mock_process.stop.return_value = True

        with FRPClient("example.com") as client:
            assert client.is_connected()
            mock_process.start.assert_called_once()

        mock_process.stop.assert_called_once()

    @patch("frp_wrapper.core.client.FRPClient.find_frp_binary")
    def test_client_context_manager_handles_exception(self, mock_find_binary):
        """FRPClient context manager should handle exceptions"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"

        with patch("frp_wrapper.core.client.ProcessManager") as mock_process_manager:
            mock_process = Mock()
            mock_process_manager.return_value = mock_process
            mock_process.start.return_value = True
            mock_process.wait_for_startup.return_value = True
            mock_process.is_running.return_value = True  # Add this for is_connected()
            mock_process.stop.return_value = True

            try:
                with FRPClient("example.com"):
                    raise ValueError("Test exception")
            except ValueError:
                pass  # Expected

            mock_process.stop.assert_called_once()

    @patch("frp_wrapper.core.client.FRPClient.find_frp_binary")
    def test_client_context_manager_handles_disconnect_exception(
        self, mock_find_binary
    ):
        """FRPClient context manager should handle disconnect exceptions"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"

        with patch("frp_wrapper.core.client.ProcessManager") as mock_process_manager:
            mock_process = Mock()
            mock_process_manager.return_value = mock_process
            mock_process.start.return_value = True
            mock_process.wait_for_startup.return_value = True
            mock_process.is_running.return_value = True  # Add this for is_connected()
            mock_process.stop.side_effect = Exception("Disconnect failed")

            with FRPClient("example.com"):
                pass  # Context should handle disconnect exception gracefully

            mock_process.stop.assert_called_once()

    @patch("shutil.which")
    def test_find_frp_binary_success(self, mock_which):
        """find_frp_binary should locate frpc binary"""
        mock_which.return_value = "/usr/local/bin/frpc"

        binary_path = FRPClient.find_frp_binary()

        assert binary_path == "/usr/local/bin/frpc"
        mock_which.assert_called_with("frpc")

    @patch("shutil.which")
    @patch("os.path.exists")
    @patch("os.access")
    def test_find_frp_binary_not_found(self, mock_access, mock_exists, mock_which):
        """find_frp_binary should raise exception if binary not found"""
        mock_which.return_value = None
        mock_exists.return_value = False
        mock_access.return_value = False

        with pytest.raises(BinaryNotFoundError, match="frpc binary not found"):
            FRPClient.find_frp_binary()

    @patch("os.path.exists")
    @patch("os.access")
    def test_find_frp_binary_custom_paths(self, mock_access, mock_exists):
        """find_frp_binary should check common installation paths"""
        with patch("shutil.which", return_value=None):  # Not in PATH
            mock_exists.side_effect = lambda path: path == "/opt/frp/frpc"
            mock_access.side_effect = lambda path, mode: path == "/opt/frp/frpc"

            binary_path = FRPClient.find_frp_binary()

            assert binary_path == "/opt/frp/frpc"


@pytest.mark.integration
class TestFRPClientIntegration:
    @patch("frp_wrapper.core.client.ProcessManager")
    @patch("frp_wrapper.core.client.FRPClient.find_frp_binary")
    def test_real_connection_no_server(self, mock_find_binary, mock_process_manager):
        """Test connection failure with no server"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"

        # Mock process manager to simulate connection failure
        mock_process = Mock()
        mock_process_manager.return_value = mock_process
        mock_process.start.return_value = True
        mock_process.wait_for_startup.return_value = False  # Startup fails
        mock_process.is_running.return_value = False  # Process died

        client = FRPClient("127.0.0.1", port=9999)  # Unlikely to have server

        with pytest.raises(ConnectionError):
            client.connect()

    @pytest.mark.skipif(
        not os.path.exists("/usr/local/bin/frpc"), reason="FRP binary not available"
    )
    def test_real_binary_detection(self):
        """Test real FRP binary detection"""
        binary_path = FRPClient.find_frp_binary()

        assert os.path.exists(binary_path)
        assert os.access(binary_path, os.X_OK)
        assert binary_path.endswith("frpc")
