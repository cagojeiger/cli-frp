"""Tests for tunnel process management."""

from unittest.mock import Mock, patch

from frp_wrapper.client.tunnel import (
    HTTPTunnel,
    TCPTunnel,
    TunnelConfig,
    TunnelProcessManager,
)


class TestTunnelProcessManager:
    """Test TunnelProcessManager class."""

    def test_tunnel_process_manager_initialization(self):
        """Test TunnelProcessManager initialization."""
        config = TunnelConfig(server_host="test.example.com")
        manager = TunnelProcessManager(config, "/usr/bin/frpc")

        assert manager.config == config
        assert manager._frp_binary_path == "/usr/bin/frpc"
        assert manager._processes == {}

    @patch("frp_wrapper.client.tunnel.ProcessManager")
    @patch("frp_wrapper.client.tunnel.ConfigBuilder")
    def test_start_tunnel_process_http(self, mock_config_builder, mock_process_manager):
        """Test starting process for HTTP tunnel."""
        config = TunnelConfig(server_host="test.example.com", auth_token="secret")
        manager = TunnelProcessManager(config, "/usr/bin/frpc")

        tunnel = HTTPTunnel(id="test", local_port=3000, path="api")

        # Mock ConfigBuilder
        mock_builder_instance = Mock()
        mock_config_builder.return_value.__enter__.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = "/tmp/config.toml"

        # Mock ProcessManager
        mock_process_instance = Mock()
        mock_process_manager.return_value = mock_process_instance
        mock_process_instance.start.return_value = True
        mock_process_instance.wait_for_startup.return_value = True
        mock_process_instance.is_running.return_value = True

        result = manager.start_tunnel_process(tunnel)

        assert result is True
        assert "test" in manager._processes
        mock_builder_instance.add_server.assert_called_once_with(
            "test.example.com", token="secret"
        )
        mock_builder_instance.add_http_proxy.assert_called_once()

    @patch("frp_wrapper.client.tunnel.ProcessManager")
    @patch("frp_wrapper.client.tunnel.ConfigBuilder")
    def test_start_tunnel_process_tcp(self, mock_config_builder, mock_process_manager):
        """Test starting process for TCP tunnel."""
        config = TunnelConfig(server_host="test.example.com")
        manager = TunnelProcessManager(config, "/usr/bin/frpc")

        tunnel = TCPTunnel(id="test", local_port=3000, remote_port=8080)

        # Mock ConfigBuilder
        mock_builder_instance = Mock()
        mock_config_builder.return_value.__enter__.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = "/tmp/config.toml"

        # Mock ProcessManager
        mock_process_instance = Mock()
        mock_process_manager.return_value = mock_process_instance
        mock_process_instance.start.return_value = True
        mock_process_instance.wait_for_startup.return_value = True
        mock_process_instance.is_running.return_value = True

        result = manager.start_tunnel_process(tunnel)

        assert result is True
        assert "test" in manager._processes
        mock_builder_instance.add_tcp_proxy.assert_called_once()

    def test_stop_tunnel_process(self):
        """Test stopping tunnel process."""
        config = TunnelConfig(server_host="test.example.com")
        manager = TunnelProcessManager(config, "/usr/bin/frpc")

        # Add a mock process
        mock_process = Mock()
        mock_process.stop.return_value = True
        manager._processes["test"] = mock_process

        result = manager.stop_tunnel_process("test")

        assert result is True
        assert "test" not in manager._processes
        mock_process.stop.assert_called_once()

    def test_stop_tunnel_process_not_found(self):
        """Test stopping non-existent tunnel process."""
        config = TunnelConfig(server_host="test.example.com")
        manager = TunnelProcessManager(config, "/usr/bin/frpc")

        result = manager.stop_tunnel_process("nonexistent")

        assert result is True  # Should return True for non-existent processes

    def test_is_process_running(self):
        """Test checking if process is running."""
        config = TunnelConfig(server_host="test.example.com")
        manager = TunnelProcessManager(config, "/usr/bin/frpc")

        # Test non-existent process
        assert manager.is_process_running("nonexistent") is False

        # Test existing process
        mock_process = Mock()
        mock_process.is_running.return_value = True
        manager._processes["test"] = mock_process

        assert manager.is_process_running("test") is True

    def test_cleanup_all_processes(self):
        """Test cleaning up all processes."""
        config = TunnelConfig(server_host="test.example.com")
        manager = TunnelProcessManager(config, "/usr/bin/frpc")

        # Add mock processes
        mock_process1 = Mock()
        mock_process1.stop.return_value = True
        mock_process2 = Mock()
        mock_process2.stop.return_value = True

        manager._processes["test1"] = mock_process1
        manager._processes["test2"] = mock_process2

        result = manager.cleanup_all_processes()

        assert result is True
        assert len(manager._processes) == 0
        mock_process1.stop.assert_called_once()
        mock_process2.stop.assert_called_once()

    def test_get_running_process_count(self):
        """Test getting count of running processes."""
        config = TunnelConfig(server_host="test.example.com")
        manager = TunnelProcessManager(config, "/usr/bin/frpc")

        # No processes initially
        assert manager.get_running_process_count() == 0

        # Add some mock processes
        mock_process1 = Mock()
        mock_process1.is_running.return_value = True
        mock_process2 = Mock()
        mock_process2.is_running.return_value = False
        mock_process3 = Mock()
        mock_process3.is_running.return_value = True

        manager._processes["test1"] = mock_process1
        manager._processes["test2"] = mock_process2
        manager._processes["test3"] = mock_process3

        assert manager.get_running_process_count() == 2
