"""Additional tests to improve tunnel_manager.py coverage."""

from unittest.mock import Mock, patch

import pytest

from frp_wrapper.tunnels.manager import (
    TunnelManager,
    TunnelManagerError,
    TunnelRegistry,
    TunnelRegistryError,
)
from frp_wrapper.tunnels.models import HTTPTunnel, TCPTunnel, TunnelConfig, TunnelStatus


class TestTunnelRegistryEdgeCases:
    """Test edge cases and error paths in TunnelRegistry."""

    def test_registry_max_tunnels_limit(self):
        """Test that registry enforces max tunnel limit."""
        registry = TunnelRegistry(max_tunnels=2)

        tunnel1 = HTTPTunnel(id="tunnel1", local_port=3000, path="app1")
        registry.add_tunnel(tunnel1)

        tunnel2 = HTTPTunnel(id="tunnel2", local_port=3001, path="app2")
        registry.add_tunnel(tunnel2)

        tunnel3 = HTTPTunnel(id="tunnel3", local_port=3002, path="app3")
        with pytest.raises(
            TunnelRegistryError, match="Maximum tunnel limit \\(2\\) reached"
        ):
            registry.add_tunnel(tunnel3)

    def test_registry_from_dict_with_unknown_tunnel_type(self):
        """Test from_dict handles unknown tunnel types gracefully."""
        data = {
            "max_tunnels": 10,
            "tunnels": [
                {
                    "id": "valid-http",
                    "tunnel_type": "http",
                    "local_port": 3000,
                    "path": "app",
                    "custom_domains": [],
                    "strip_path": True,
                    "websocket": True,
                    "status": "pending",
                    "created_at": "2023-01-01T00:00:00",
                    "connected_at": None,
                },
                {
                    "id": "unknown-type",
                    "tunnel_type": "unknown",  # This should be skipped
                    "local_port": 3001,
                },
            ],
        }

        registry = TunnelRegistry.from_dict(data)

        assert len(registry.tunnels) == 1
        assert "valid-http" in registry.tunnels
        assert "unknown-type" not in registry.tunnels


class TestTunnelManagerErrorPaths:
    """Test error handling paths in TunnelManager."""

    def test_start_tunnel_already_connected(self):
        """Test starting a tunnel that's already connected."""
        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)
        tunnel = HTTPTunnel(
            id="test", local_port=3000, path="app", status=TunnelStatus.CONNECTED
        )
        manager.registry.tunnels["test"] = tunnel

        result = manager.start_tunnel("test")
        assert result is True

    def test_start_tunnel_process_failure(self):
        """Test start_tunnel when FRP process fails to start."""
        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)
        tunnel = HTTPTunnel(id="test", local_port=3000, path="app")
        manager.registry.add_tunnel(tunnel)

        with patch.object(
            manager._process_manager, "start_tunnel_process", return_value=False
        ):
            result = manager.start_tunnel("test")
            assert result is False

            updated_tunnel = manager.registry.get_tunnel("test")
            assert updated_tunnel is not None
            assert updated_tunnel.status == TunnelStatus.ERROR

    def test_start_tunnel_process_exception(self):
        """Test start_tunnel when FRP process raises exception."""
        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)
        tunnel = HTTPTunnel(id="test", local_port=3000, path="app")
        manager.registry.add_tunnel(tunnel)

        with patch.object(
            manager._process_manager,
            "start_tunnel_process",
            side_effect=Exception("Process error"),
        ):
            with pytest.raises(
                TunnelManagerError, match="Failed to start tunnel: Process error"
            ):
                manager.start_tunnel("test")

            updated_tunnel = manager.registry.get_tunnel("test")
            assert updated_tunnel is not None
            assert updated_tunnel.status == TunnelStatus.ERROR

    def test_stop_tunnel_not_connected(self):
        """Test stopping a tunnel that's not connected."""
        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)
        tunnel = HTTPTunnel(
            id="test", local_port=3000, path="app", status=TunnelStatus.PENDING
        )
        manager.registry.tunnels["test"] = tunnel

        result = manager.stop_tunnel("test")
        assert result is True

    def test_stop_tunnel_process_failure(self):
        """Test stop_tunnel when FRP process fails to stop."""
        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)
        tunnel = HTTPTunnel(
            id="test", local_port=3000, path="app", status=TunnelStatus.CONNECTED
        )
        manager.registry.tunnels["test"] = tunnel

        with patch.object(
            manager._process_manager, "stop_tunnel_process", return_value=False
        ):
            result = manager.stop_tunnel("test")
            assert result is False

    def test_stop_tunnel_process_exception(self):
        """Test stop_tunnel when FRP process raises exception."""
        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)
        tunnel = HTTPTunnel(
            id="test", local_port=3000, path="app", status=TunnelStatus.CONNECTED
        )
        manager.registry.tunnels["test"] = tunnel

        with patch.object(
            manager._process_manager,
            "stop_tunnel_process",
            side_effect=Exception("Stop error"),
        ):
            with pytest.raises(
                TunnelManagerError, match="Failed to stop tunnel: Stop error"
            ):
                manager.stop_tunnel("test")

    def test_remove_tunnel_with_connected_status(self):
        """Test removing a tunnel that's currently connected."""
        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)
        tunnel = HTTPTunnel(
            id="test", local_port=3000, path="app", status=TunnelStatus.CONNECTED
        )
        manager.registry.tunnels["test"] = tunnel
        manager._process_manager._processes["test"] = Mock()  # Simulate process handle

        with patch.object(manager, "stop_tunnel") as mock_stop:
            removed_tunnel = manager.remove_tunnel("test")

            mock_stop.assert_called_once_with("test")
            assert removed_tunnel.id == "test"
            assert "test" not in manager._process_manager._processes

    def test_remove_tunnel_with_process_handle(self):
        """Test removing tunnel cleans up process handle."""
        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)
        tunnel = HTTPTunnel(id="test", local_port=3000, path="app")
        manager.registry.add_tunnel(tunnel)
        manager._process_manager._processes["test"] = Mock()  # Simulate process handle

        removed_tunnel = manager.remove_tunnel("test")

        assert removed_tunnel.id == "test"
        assert "test" not in manager._process_manager._processes

    def test_get_tunnel_info_tcp_tunnel(self):
        """Test get_tunnel_info for TCP tunnel type."""
        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)
        tunnel = TCPTunnel(
            id="test", local_port=3000, remote_port=8080, status=TunnelStatus.CONNECTED
        )
        manager.registry.add_tunnel(tunnel)

        info = manager.get_tunnel_info("test")

        assert info["type"] == "tcp"
        assert info["remote_port"] == 8080
        assert "endpoint" in info
        assert "path" not in info  # HTTP-specific field

    def test_shutdown_all_with_errors(self):
        """Test shutdown_all when some tunnels fail to stop."""
        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)

        tunnel1 = HTTPTunnel(
            id="tunnel1", local_port=3000, path="app1", status=TunnelStatus.CONNECTED
        )
        tunnel2 = HTTPTunnel(
            id="tunnel2", local_port=3001, path="app2", status=TunnelStatus.CONNECTED
        )
        manager.registry.tunnels["tunnel1"] = tunnel1
        manager.registry.tunnels["tunnel2"] = tunnel2

        def mock_stop_tunnel(tunnel_id):
            if tunnel_id == "tunnel1":
                return True
            elif tunnel_id == "tunnel2":
                raise Exception("Stop failed")

        with patch.object(manager, "stop_tunnel", side_effect=mock_stop_tunnel):
            result = manager.shutdown_all()

            assert result is False

    def test_shutdown_all_stop_returns_false(self):
        """Test shutdown_all when stop_tunnel returns False."""
        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)

        tunnel = HTTPTunnel(
            id="test", local_port=3000, path="app", status=TunnelStatus.CONNECTED
        )
        manager.registry.tunnels["test"] = tunnel

        with patch.object(manager, "stop_tunnel", return_value=False):
            result = manager.shutdown_all()

            assert result is False

    def test_stop_tunnel_not_found_error(self):
        """Test stop_tunnel when tunnel is not found."""
        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)

        with pytest.raises(TunnelManagerError, match="Tunnel 'nonexistent' not found"):
            manager.stop_tunnel("nonexistent")

    def test_get_tunnel_info_not_found_error(self):
        """Test get_tunnel_info when tunnel is not found."""
        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)

        with pytest.raises(TunnelManagerError, match="Tunnel 'nonexistent' not found"):
            manager.get_tunnel_info("nonexistent")
