import os
from unittest.mock import Mock, patch

import pytest

from frp_wrapper.client import FRPClient
from frp_wrapper.exceptions import BinaryNotFoundError, ConnectionError


@pytest.mark.integration
class TestFRPClientIntegration:
    """Integration tests for FRPClient with real components."""

    def test_client_initialization_with_real_binary_detection(self):
        """Test client initialization with actual binary detection logic"""
        try:
            client = FRPClient("test.example.com")
            assert client.server == "test.example.com"
            assert client.port == 7000
            assert client.binary_path is not None
            assert os.path.exists(client.binary_path)
        except BinaryNotFoundError:
            pytest.skip("frpc binary not available for integration test")

    def test_config_builder_integration(self):
        """Test ConfigBuilder creates valid configuration files"""
        from frp_wrapper import ConfigBuilder

        with ConfigBuilder() as builder:
            builder.add_server("test.example.com", port=8000, token="test123")
            config_path = builder.build()

            assert os.path.exists(config_path)

            with open(config_path) as f:
                content = f.read()

            assert "[common]" in content
            assert 'server_addr = "test.example.com"' in content
            assert "server_port = 8000" in content
            assert 'token = "test123"' in content

    @patch("frp_wrapper.client.ProcessManager")
    @patch("frp_wrapper.client.FRPClient.find_frp_binary")
    def test_client_connection_failure_handling(
        self, mock_find_binary, mock_process_manager
    ):
        """Test client handles connection failures gracefully"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"

        # Mock process manager to simulate connection failure
        mock_process = Mock()
        mock_process_manager.return_value = mock_process
        mock_process.start.return_value = True
        mock_process.wait_for_startup.return_value = False  # Startup fails
        mock_process.is_running.return_value = False  # Process died

        client = FRPClient("invalid.nonexistent.server.com", port=9999)

        with pytest.raises(ConnectionError):
            client.connect()

        assert not client.is_connected()

    @patch("frp_wrapper.client.FRPClient.find_frp_binary")
    def test_client_context_manager_integration(self, mock_find_binary):
        """Test client context manager with mocked components"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"

        with patch("frp_wrapper.client.ProcessManager") as mock_pm:
            with patch("frp_wrapper.client.ConfigBuilder") as mock_cb:
                mock_process = Mock()
                mock_pm.return_value = mock_process
                mock_process.start.return_value = True
                mock_process.wait_for_startup.return_value = True
                mock_process.is_running.return_value = True
                mock_process.stop.return_value = True

                mock_config = Mock()
                mock_cb.return_value = mock_config
                mock_config.build.return_value = "/tmp/test.toml"

                with FRPClient("test.example.com") as client:
                    assert client.is_connected()
                    mock_process.start.assert_called_once()

                mock_process.stop.assert_called_once()

    def test_binary_detection_fallback_paths(self):
        """Test binary detection checks fallback paths"""
        with patch("shutil.which", return_value=None):  # Not in PATH
            with patch("os.path.exists") as mock_exists:
                with patch("os.access") as mock_access:

                    def exists_side_effect(path):
                        return path == "/opt/frp/frpc"

                    def access_side_effect(path, mode):
                        return path == "/opt/frp/frpc"

                    mock_exists.side_effect = exists_side_effect
                    mock_access.side_effect = access_side_effect

                    binary_path = FRPClient.find_frp_binary()
                    assert binary_path == "/opt/frp/frpc"

    def test_config_cleanup_on_exception(self):
        """Test configuration cleanup happens even on exceptions"""
        from frp_wrapper import ConfigBuilder

        config_path = None
        try:
            with ConfigBuilder() as builder:
                builder.add_server("test.example.com")
                config_path = builder.build()
                assert os.path.exists(config_path)
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        assert not os.path.exists(config_path)

    @patch("frp_wrapper.client.FRPClient.find_frp_binary")
    def test_multiple_connect_disconnect_cycles(self, mock_find_binary):
        """Test multiple connect/disconnect cycles work correctly"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"

        with patch("frp_wrapper.client.ProcessManager") as mock_pm:
            with patch("frp_wrapper.client.ConfigBuilder") as mock_cb:
                mock_process = Mock()
                mock_pm.return_value = mock_process
                mock_process.start.return_value = True
                mock_process.wait_for_startup.return_value = True
                mock_process.is_running.return_value = True
                mock_process.stop.return_value = True

                mock_config = Mock()
                mock_cb.return_value = mock_config
                mock_config.build.return_value = "/tmp/test.toml"

                client = FRPClient("test.example.com")

                assert client.connect()
                assert client.is_connected()
                assert client.disconnect()
                assert not client.is_connected()

                assert client.connect()
                assert client.is_connected()
                assert client.disconnect()
                assert not client.is_connected()

                assert mock_process.start.call_count == 2
                assert mock_process.stop.call_count == 2
