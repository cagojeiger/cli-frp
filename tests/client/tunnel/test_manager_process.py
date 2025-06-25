"""Tests for TunnelManager process management methods."""

from unittest.mock import Mock, patch

import pytest

from frp_wrapper.client.config import ConfigBuilder
from frp_wrapper.client.tunnel import (
    HTTPTunnel,
    TCPTunnel,
    TunnelConfig,
    TunnelManager,
    TunnelStatus,
)
from frp_wrapper.common.process import ProcessManager


class TestTunnelManagerProcessManagement:
    """Test suite for TunnelManager process management methods."""

    @pytest.fixture
    def tunnel_config(self):
        """Create test tunnel configuration."""
        return TunnelConfig(
            server_host="test.example.com", auth_token="test-token", max_tunnels=5
        )

    @pytest.fixture
    def tunnel_manager(self, tunnel_config):
        """Create TunnelManager with mocked FRP binary."""
        with patch("frp_wrapper.client.tunnel.manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/frpc"
            manager = TunnelManager(tunnel_config)
            return manager

    @pytest.fixture
    def http_tunnel(self):
        """Create test HTTP tunnel."""
        return HTTPTunnel(
            id="test-http",
            local_port=3000,
            path="myapp",
            custom_domains=["test.example.com"],
        )

    @pytest.fixture
    def tcp_tunnel(self):
        """Create test TCP tunnel."""
        return TCPTunnel(id="test-tcp", local_port=4000, remote_port=8080)

    def test_start_tunnel_process_http_tunnel_success(
        self, tunnel_manager, http_tunnel
    ):
        """Test successful FRP process start for HTTP tunnel."""
        tunnel_manager.registry.add_tunnel(http_tunnel)

        with (
            patch(
                "frp_wrapper.client.tunnel.process.ConfigBuilder"
            ) as mock_config_builder,
            patch(
                "frp_wrapper.client.tunnel.process.ProcessManager"
            ) as mock_process_manager,
        ):
            # Setup mocks
            mock_builder = Mock(spec=ConfigBuilder)
            mock_config_builder.return_value.__enter__.return_value = mock_builder
            mock_builder.build.return_value = "/tmp/test_config.toml"

            mock_process = Mock(spec=ProcessManager)
            mock_process_manager.return_value = mock_process
            mock_process.start.return_value = True
            mock_process.wait_for_startup.return_value = True
            mock_process.is_running.return_value = True

            # Execute
            result = tunnel_manager._process_manager.start_tunnel_process(http_tunnel)

            # Verify
            assert result is True
            mock_builder.add_server.assert_called_once_with(
                "test.example.com", token="test-token"
            )
            mock_builder.add_http_proxy.assert_called_once_with(
                name="test-http",
                local_port=3000,
                locations=["/myapp"],
                custom_domains=["test.example.com"],
            )
            mock_process.start.assert_called_once()
            mock_process.wait_for_startup.assert_called_once_with(timeout=10)
            assert tunnel_manager._processes["test-http"] == mock_process

    def test_start_tunnel_process_tcp_tunnel_success(self, tunnel_manager, tcp_tunnel):
        """Test successful FRP process start for TCP tunnel."""
        tunnel_manager.registry.add_tunnel(tcp_tunnel)

        with (
            patch(
                "frp_wrapper.client.tunnel.process.ConfigBuilder"
            ) as mock_config_builder,
            patch(
                "frp_wrapper.client.tunnel.process.ProcessManager"
            ) as mock_process_manager,
        ):
            # Setup mocks
            mock_builder = Mock(spec=ConfigBuilder)
            mock_config_builder.return_value.__enter__.return_value = mock_builder
            mock_builder.build.return_value = "/tmp/test_config.toml"

            mock_process = Mock(spec=ProcessManager)
            mock_process_manager.return_value = mock_process
            mock_process.start.return_value = True
            mock_process.wait_for_startup.return_value = True
            mock_process.is_running.return_value = True

            # Execute
            result = tunnel_manager._process_manager.start_tunnel_process(tcp_tunnel)

            # Verify
            assert result is True
            mock_builder.add_server.assert_called_once_with(
                "test.example.com", token="test-token"
            )
            mock_builder.add_tcp_proxy.assert_called_once_with(
                name="test-tcp", local_port=4000, remote_port=8080
            )
            mock_process.start.assert_called_once()
            mock_process.wait_for_startup.assert_called_once_with(timeout=10)
            assert tunnel_manager._processes["test-tcp"] == mock_process

    def test_start_tunnel_process_start_failure(self, tunnel_manager, http_tunnel):
        """Test FRP process start failure."""
        tunnel_manager.registry.add_tunnel(http_tunnel)

        with (
            patch(
                "frp_wrapper.client.tunnel.process.ConfigBuilder"
            ) as mock_config_builder,
            patch(
                "frp_wrapper.client.tunnel.process.ProcessManager"
            ) as mock_process_manager,
        ):
            # Setup mocks
            mock_builder = Mock(spec=ConfigBuilder)
            mock_config_builder.return_value.__enter__.return_value = mock_builder
            mock_builder.build.return_value = "/tmp/test_config.toml"

            mock_process = Mock(spec=ProcessManager)
            mock_process_manager.return_value = mock_process
            mock_process.start.return_value = False  # Process start fails

            # Execute
            result = tunnel_manager._process_manager.start_tunnel_process(http_tunnel)

            # Verify
            assert result is False
            assert "test-http" not in tunnel_manager._process_manager._processes

    def test_start_tunnel_process_startup_failure(self, tunnel_manager, http_tunnel):
        """Test FRP process startup failure after start."""
        tunnel_manager.registry.add_tunnel(http_tunnel)

        with (
            patch(
                "frp_wrapper.client.tunnel.process.ConfigBuilder"
            ) as mock_config_builder,
            patch(
                "frp_wrapper.client.tunnel.process.ProcessManager"
            ) as mock_process_manager,
        ):
            # Setup mocks
            mock_builder = Mock(spec=ConfigBuilder)
            mock_config_builder.return_value.__enter__.return_value = mock_builder
            mock_builder.build.return_value = "/tmp/test_config.toml"

            mock_process = Mock(spec=ProcessManager)
            mock_process_manager.return_value = mock_process
            mock_process.start.return_value = True
            mock_process.wait_for_startup.return_value = False  # Startup fails
            mock_process.is_running.return_value = False

            # Execute
            result = tunnel_manager._process_manager.start_tunnel_process(http_tunnel)

            # Verify
            assert result is False
            mock_process.stop.assert_called_once()  # Should cleanup failed process
            assert "test-http" not in tunnel_manager._process_manager._processes

    def test_start_tunnel_process_running_check_failure(
        self, tunnel_manager, http_tunnel
    ):
        """Test FRP process running check failure."""
        tunnel_manager.registry.add_tunnel(http_tunnel)

        with (
            patch(
                "frp_wrapper.client.tunnel.process.ConfigBuilder"
            ) as mock_config_builder,
            patch(
                "frp_wrapper.client.tunnel.process.ProcessManager"
            ) as mock_process_manager,
        ):
            # Setup mocks
            mock_builder = Mock(spec=ConfigBuilder)
            mock_config_builder.return_value.__enter__.return_value = mock_builder
            mock_builder.build.return_value = "/tmp/test_config.toml"

            mock_process = Mock(spec=ProcessManager)
            mock_process_manager.return_value = mock_process
            mock_process.start.return_value = True
            mock_process.wait_for_startup.return_value = True
            mock_process.is_running.return_value = False  # Not running after startup

            # Execute
            result = tunnel_manager._process_manager.start_tunnel_process(http_tunnel)

            # Verify
            assert result is False
            mock_process.stop.assert_called_once()
            assert "test-http" not in tunnel_manager._process_manager._processes

    def test_start_tunnel_process_exception_handling(self, tunnel_manager, http_tunnel):
        """Test exception handling in start_tunnel_process."""
        tunnel_manager.registry.add_tunnel(http_tunnel)

        with patch(
            "frp_wrapper.client.tunnel.process.ConfigBuilder"
        ) as mock_config_builder:
            # Setup ConfigBuilder to raise exception
            mock_config_builder.side_effect = Exception("Config error")

            # Execute
            result = tunnel_manager._process_manager.start_tunnel_process(http_tunnel)

            # Verify
            assert result is False
            assert "test-http" not in tunnel_manager._process_manager._processes

    def test_start_tunnel_process_unsupported_tunnel_type(self, tunnel_manager):
        """Test start_tunnel_process with unsupported tunnel type."""
        # Create a mock tunnel with invalid type
        invalid_tunnel = Mock()
        invalid_tunnel.id = "invalid-tunnel"
        invalid_tunnel.local_port = 3000

        # Make isinstance checks fail for both HTTPTunnel and TCPTunnel
        with patch("frp_wrapper.client.tunnel.isinstance", return_value=False):
            result = tunnel_manager._process_manager.start_tunnel_process(
                invalid_tunnel
            )

            assert result is False

    def test_stop_tunnel_process_success(self, tunnel_manager):
        """Test successful FRP process stop."""
        # Setup a mock process in the processes dict
        mock_process = Mock(spec=ProcessManager)
        mock_process.stop.return_value = True
        tunnel_manager._process_manager._processes["test-tunnel"] = mock_process

        # Execute
        result = tunnel_manager._process_manager.stop_tunnel_process("test-tunnel")

        # Verify
        assert result is True
        mock_process.stop.assert_called_once()
        assert "test-tunnel" not in tunnel_manager._processes

    def test_stop_tunnel_process_stop_failure(self, tunnel_manager):
        """Test FRP process stop failure."""
        # Setup a mock process in the processes dict
        mock_process = Mock(spec=ProcessManager)
        mock_process.stop.return_value = False  # Stop fails
        tunnel_manager._process_manager._processes["test-tunnel"] = mock_process

        # Execute
        result = tunnel_manager._process_manager.stop_tunnel_process("test-tunnel")

        # Verify
        assert result is False
        mock_process.stop.assert_called_once()
        # Process should still be removed from dict even if stop fails
        assert "test-tunnel" not in tunnel_manager._processes

    def test_stop_tunnel_process_no_process_found(self, tunnel_manager):
        """Test stopping FRP process when no process is found."""
        # Execute with tunnel that has no process
        result = tunnel_manager._process_manager.stop_tunnel_process(
            "nonexistent-tunnel"
        )

        # Verify - should return True (considered successful)
        assert result is True

    def test_stop_tunnel_process_exception_handling(self, tunnel_manager):
        """Test exception handling in stop_tunnel_process."""
        # Setup a mock process that raises exception on stop
        mock_process = Mock(spec=ProcessManager)
        mock_process.stop.side_effect = Exception("Stop error")
        tunnel_manager._process_manager._processes["test-tunnel"] = mock_process

        # Execute
        result = tunnel_manager._process_manager.stop_tunnel_process("test-tunnel")

        # Verify
        assert result is False
        # Process should still be removed from dict even on exception
        assert "test-tunnel" not in tunnel_manager._processes

    def test_process_management_integration(self, tunnel_manager, http_tunnel):
        """Test integration between start_tunnel and process management."""
        tunnel_manager.registry.add_tunnel(http_tunnel)

        with patch.object(
            tunnel_manager._process_manager, "start_tunnel_process"
        ) as mock_start:
            mock_start.return_value = True

            # Start tunnel
            result = tunnel_manager.start_tunnel("test-http")

            # Verify
            assert result is True
            mock_start.assert_called_once_with(http_tunnel)

            # Check tunnel status was updated
            updated_tunnel = tunnel_manager.registry.get_tunnel("test-http")
            assert updated_tunnel.status == TunnelStatus.CONNECTED

    def test_process_management_start_tunnel_process_failure(
        self, tunnel_manager, http_tunnel
    ):
        """Test start_tunnel when process start fails."""
        tunnel_manager.registry.add_tunnel(http_tunnel)

        with patch.object(
            tunnel_manager._process_manager, "start_tunnel_process"
        ) as mock_start:
            mock_start.return_value = False  # Process start fails

            # Start tunnel
            result = tunnel_manager.start_tunnel("test-http")

            # Verify
            assert result is False
            mock_start.assert_called_once_with(http_tunnel)

            # Check tunnel status was updated to ERROR
            updated_tunnel = tunnel_manager.registry.get_tunnel("test-http")
            assert updated_tunnel.status == TunnelStatus.ERROR

    def test_process_management_stop_tunnel_integration(
        self, tunnel_manager, http_tunnel
    ):
        """Test integration between stop_tunnel and process management."""
        # Add tunnel and set as connected
        connected_tunnel = http_tunnel.with_status(TunnelStatus.CONNECTED)
        tunnel_manager.registry.add_tunnel(connected_tunnel)

        with patch.object(
            tunnel_manager._process_manager, "stop_tunnel_process"
        ) as mock_stop:
            mock_stop.return_value = True

            # Stop tunnel
            result = tunnel_manager.stop_tunnel("test-http")

            # Verify
            assert result is True
            mock_stop.assert_called_once_with("test-http")

            # Check tunnel status was updated
            updated_tunnel = tunnel_manager.registry.get_tunnel("test-http")
            assert updated_tunnel.status == TunnelStatus.DISCONNECTED
