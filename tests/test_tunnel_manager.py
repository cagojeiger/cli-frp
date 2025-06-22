from unittest.mock import patch

import pytest

from frp_wrapper.tunnel import (
    HTTPTunnel,
    TCPTunnel,
    TunnelConfig,
    TunnelStatus,
    TunnelType,
)


class TestTunnelRegistry:
    """Test suite for TunnelRegistry component."""

    def test_tunnel_registry_creation(self):
        """Test TunnelRegistry can be created and initialized."""
        from frp_wrapper.tunnel_manager import TunnelRegistry

        registry = TunnelRegistry()
        assert registry is not None
        assert len(registry.list_tunnels()) == 0

    def test_tunnel_registry_add_tunnel(self):
        """Test adding tunnels to the registry."""
        from frp_wrapper.tunnel_manager import TunnelRegistry

        registry = TunnelRegistry()
        tunnel = HTTPTunnel(id="test-http", local_port=3000, path="myapp")

        registry.add_tunnel(tunnel)
        tunnels = registry.list_tunnels()

        assert len(tunnels) == 1
        assert tunnels[0].id == "test-http"

    def test_tunnel_registry_add_duplicate_id_raises_error(self):
        """Test that adding tunnel with duplicate ID raises error."""
        from frp_wrapper.tunnel_manager import TunnelRegistry, TunnelRegistryError

        registry = TunnelRegistry()
        tunnel1 = HTTPTunnel(id="duplicate", local_port=3000, path="app1")
        tunnel2 = HTTPTunnel(id="duplicate", local_port=4000, path="app2")

        registry.add_tunnel(tunnel1)

        with pytest.raises(TunnelRegistryError, match="already exists"):
            registry.add_tunnel(tunnel2)

    def test_tunnel_registry_remove_tunnel(self):
        """Test removing tunnels from the registry."""
        from frp_wrapper.tunnel_manager import TunnelRegistry

        registry = TunnelRegistry()
        tunnel = TCPTunnel(id="test-tcp", local_port=3000)

        registry.add_tunnel(tunnel)
        assert len(registry.list_tunnels()) == 1

        removed_tunnel = registry.remove_tunnel("test-tcp")
        assert removed_tunnel.id == "test-tcp"
        assert len(registry.list_tunnels()) == 0

    def test_tunnel_registry_remove_nonexistent_tunnel_raises_error(self):
        """Test that removing non-existent tunnel raises error."""
        from frp_wrapper.tunnel_manager import TunnelRegistry, TunnelRegistryError

        registry = TunnelRegistry()

        with pytest.raises(TunnelRegistryError, match="not found"):
            registry.remove_tunnel("nonexistent")

    def test_tunnel_registry_get_tunnel(self):
        """Test getting tunnel by ID from registry."""
        from frp_wrapper.tunnel_manager import TunnelRegistry

        registry = TunnelRegistry()
        tunnel = HTTPTunnel(id="test-get", local_port=3000, path="myapp")

        registry.add_tunnel(tunnel)
        retrieved_tunnel = registry.get_tunnel("test-get")

        assert retrieved_tunnel is not None
        assert retrieved_tunnel.id == "test-get"
        assert retrieved_tunnel.path == "myapp"

    def test_tunnel_registry_get_nonexistent_tunnel_returns_none(self):
        """Test that getting non-existent tunnel returns None."""
        from frp_wrapper.tunnel_manager import TunnelRegistry

        registry = TunnelRegistry()
        tunnel = registry.get_tunnel("nonexistent")

        assert tunnel is None

    def test_tunnel_registry_update_tunnel_status(self):
        """Test updating tunnel status in registry."""
        from frp_wrapper.tunnel_manager import TunnelRegistry

        registry = TunnelRegistry()
        tunnel = TCPTunnel(id="test-update", local_port=3000)

        registry.add_tunnel(tunnel)
        registry.update_tunnel_status("test-update", TunnelStatus.CONNECTED)

        updated_tunnel = registry.get_tunnel("test-update")
        assert updated_tunnel.status == TunnelStatus.CONNECTED
        assert updated_tunnel.connected_at is not None

    def test_tunnel_registry_update_nonexistent_tunnel_status_raises_error(self):
        """Test that updating status of non-existent tunnel raises error."""
        from frp_wrapper.tunnel_manager import TunnelRegistry, TunnelRegistryError

        registry = TunnelRegistry()

        with pytest.raises(TunnelRegistryError, match="not found"):
            registry.update_tunnel_status("nonexistent", TunnelStatus.CONNECTED)

    def test_tunnel_registry_list_tunnels_by_type(self):
        """Test listing tunnels filtered by type."""
        from frp_wrapper.tunnel_manager import TunnelRegistry

        registry = TunnelRegistry()
        http_tunnel = HTTPTunnel(id="http-1", local_port=3000, path="app1")
        tcp_tunnel = TCPTunnel(id="tcp-1", local_port=4000)

        registry.add_tunnel(http_tunnel)
        registry.add_tunnel(tcp_tunnel)

        http_tunnels = registry.list_tunnels(tunnel_type=TunnelType.HTTP)
        tcp_tunnels = registry.list_tunnels(tunnel_type=TunnelType.TCP)

        assert len(http_tunnels) == 1
        assert len(tcp_tunnels) == 1
        assert http_tunnels[0].tunnel_type == TunnelType.HTTP
        assert tcp_tunnels[0].tunnel_type == TunnelType.TCP

    def test_tunnel_registry_list_tunnels_by_status(self):
        """Test listing tunnels filtered by status."""
        from frp_wrapper.tunnel_manager import TunnelRegistry

        registry = TunnelRegistry()
        tunnel1 = HTTPTunnel(id="pending", local_port=3000, path="app1")
        tunnel2 = HTTPTunnel(id="connected", local_port=4000, path="app2")

        registry.add_tunnel(tunnel1)
        registry.add_tunnel(tunnel2)
        registry.update_tunnel_status("connected", TunnelStatus.CONNECTED)

        pending_tunnels = registry.list_tunnels(status=TunnelStatus.PENDING)
        connected_tunnels = registry.list_tunnels(status=TunnelStatus.CONNECTED)

        assert len(pending_tunnels) == 1
        assert len(connected_tunnels) == 1
        assert pending_tunnels[0].status == TunnelStatus.PENDING
        assert connected_tunnels[0].status == TunnelStatus.CONNECTED

    def test_tunnel_registry_validate_port_conflicts(self):
        """Test validation of port conflicts in registry."""
        from frp_wrapper.tunnel_manager import TunnelRegistry, TunnelRegistryError

        registry = TunnelRegistry()
        tunnel1 = TCPTunnel(id="tcp-1", local_port=3000)
        tunnel2 = TCPTunnel(id="tcp-2", local_port=3000)  # Same port

        registry.add_tunnel(tunnel1)

        with pytest.raises(TunnelRegistryError, match="port.*already in use"):
            registry.add_tunnel(tunnel2)

    def test_tunnel_registry_validate_http_path_conflicts(self):
        """Test validation of HTTP path conflicts in registry."""
        from frp_wrapper.tunnel_manager import TunnelRegistry, TunnelRegistryError

        registry = TunnelRegistry()
        tunnel1 = HTTPTunnel(id="http-1", local_port=3000, path="myapp")
        tunnel2 = HTTPTunnel(id="http-2", local_port=4000, path="myapp")  # Same path

        registry.add_tunnel(tunnel1)

        with pytest.raises(TunnelRegistryError, match="path.*already in use"):
            registry.add_tunnel(tunnel2)

    def test_tunnel_registry_clear_all_tunnels(self):
        """Test clearing all tunnels from registry."""
        from frp_wrapper.tunnel_manager import TunnelRegistry

        registry = TunnelRegistry()
        tunnel1 = HTTPTunnel(id="http-1", local_port=3000, path="app1")
        tunnel2 = TCPTunnel(id="tcp-1", local_port=4000)

        registry.add_tunnel(tunnel1)
        registry.add_tunnel(tunnel2)
        assert len(registry.list_tunnels()) == 2

        registry.clear()
        assert len(registry.list_tunnels()) == 0

    def test_tunnel_registry_serialization(self):
        """Test registry serialization to dict."""
        from frp_wrapper.tunnel_manager import TunnelRegistry

        registry = TunnelRegistry()
        tunnel = HTTPTunnel(id="serialize-test", local_port=3000, path="myapp")

        registry.add_tunnel(tunnel)
        data = registry.to_dict()

        assert "tunnels" in data
        assert len(data["tunnels"]) == 1
        assert data["tunnels"][0]["id"] == "serialize-test"

    def test_tunnel_registry_deserialization(self):
        """Test registry deserialization from dict."""
        from frp_wrapper.tunnel_manager import TunnelRegistry

        data = {
            "tunnels": [
                {
                    "id": "deserialize-test",
                    "tunnel_type": "http",
                    "local_port": 3000,
                    "path": "myapp",
                    "custom_domains": [],
                    "strip_path": True,
                    "websocket": True,
                }
            ]
        }

        registry = TunnelRegistry.from_dict(data)
        tunnels = registry.list_tunnels()

        assert len(tunnels) == 1
        assert tunnels[0].id == "deserialize-test"
        assert tunnels[0].path == "myapp"


class TestTunnelManager:
    """Test suite for TunnelManager component."""

    def test_tunnel_manager_creation(self):
        """Test TunnelManager can be created and initialized."""
        from frp_wrapper.tunnel_manager import TunnelManager

        config = TunnelConfig(server_host="test.example.com")
        manager = TunnelManager(config, frp_binary_path="/usr/bin/frpc")
        assert manager is not None
        assert manager.registry is not None
        assert manager.config.server_host == "test.example.com"

    def test_tunnel_manager_create_http_tunnel(self):
        """Test creating HTTP tunnel through manager."""
        from frp_wrapper.tunnel_manager import TunnelManager

        config = TunnelConfig(
            server_host="test.example.com", default_domain="example.com"
        )
        manager = TunnelManager(config, frp_binary_path="/usr/bin/frpc")
        tunnel = manager.create_http_tunnel(
            tunnel_id="http-manager-test",
            local_port=3000,
            path="myapp",
        )

        assert tunnel.id == "http-manager-test"
        assert tunnel.tunnel_type == TunnelType.HTTP
        assert tunnel.path == "myapp"
        assert tunnel.custom_domains == ["example.com"]  # From default_domain

        registry_tunnel = manager.registry.get_tunnel("http-manager-test")
        assert registry_tunnel is not None

    def test_tunnel_manager_create_tcp_tunnel(self):
        """Test creating TCP tunnel through manager."""
        from frp_wrapper.tunnel_manager import TunnelManager

        config = TunnelConfig(server_host="test.example.com")
        manager = TunnelManager(config, frp_binary_path="/usr/bin/frpc")
        tunnel = manager.create_tcp_tunnel(
            tunnel_id="tcp-manager-test", local_port=3000, remote_port=8080
        )

        assert tunnel.id == "tcp-manager-test"
        assert tunnel.tunnel_type == TunnelType.TCP
        assert tunnel.remote_port == 8080

        registry_tunnel = manager.registry.get_tunnel("tcp-manager-test")
        assert registry_tunnel is not None

    def test_tunnel_manager_start_tunnel(self):
        """Test starting tunnel through manager."""
        from frp_wrapper.tunnel import TunnelConfig
        from frp_wrapper.tunnel_manager import TunnelManager

        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)
        manager.create_http_tunnel(
            tunnel_id="start-test", local_port=3000, path="myapp"
        )

        with patch.object(manager, "_start_frp_process") as mock_start:
            mock_start.return_value = True

            result = manager.start_tunnel("start-test")
            assert result is True

            updated_tunnel = manager.registry.get_tunnel("start-test")
            assert updated_tunnel.status == TunnelStatus.CONNECTED

    def test_tunnel_manager_start_nonexistent_tunnel_raises_error(self):
        """Test that starting non-existent tunnel raises error."""
        from frp_wrapper.tunnel_manager import TunnelManager, TunnelManagerError

        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)

        with pytest.raises(TunnelManagerError, match="not found"):
            manager.start_tunnel("nonexistent")

    def test_tunnel_manager_stop_tunnel(self):
        """Test stopping tunnel through manager."""
        from frp_wrapper.tunnel_manager import TunnelManager

        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)
        manager.create_tcp_tunnel(tunnel_id="stop-test", local_port=3000)

        with patch.object(manager, "_start_frp_process") as mock_start:
            mock_start.return_value = True
            manager.start_tunnel("stop-test")

        with patch.object(manager, "_stop_frp_process") as mock_stop:
            mock_stop.return_value = True

            result = manager.stop_tunnel("stop-test")
            assert result is True

            updated_tunnel = manager.registry.get_tunnel("stop-test")
            assert updated_tunnel.status == TunnelStatus.DISCONNECTED

    def test_tunnel_manager_remove_tunnel(self):
        """Test removing tunnel through manager."""
        from frp_wrapper.tunnel_manager import TunnelManager

        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)
        manager.create_http_tunnel(
            tunnel_id="remove-test", local_port=3000, path="myapp"
        )

        removed_tunnel = manager.remove_tunnel("remove-test")
        assert removed_tunnel.id == "remove-test"

        registry_tunnel = manager.registry.get_tunnel("remove-test")
        assert registry_tunnel is None

    def test_tunnel_manager_list_active_tunnels(self):
        """Test listing only active tunnels."""
        from frp_wrapper.tunnel_manager import TunnelManager

        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)
        manager.create_http_tunnel("active-1", 3000, "app1")
        manager.create_http_tunnel("inactive-1", 4000, "app2")

        with patch.object(manager, "_start_frp_process") as mock_start:
            mock_start.return_value = True
            manager.start_tunnel("active-1")

        active_tunnels = manager.list_active_tunnels()
        assert len(active_tunnels) == 1
        assert active_tunnels[0].id == "active-1"
        assert active_tunnels[0].status == TunnelStatus.CONNECTED

    def test_tunnel_manager_get_tunnel_info(self):
        """Test getting detailed tunnel information."""
        from frp_wrapper.tunnel_manager import TunnelManager

        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)
        manager.create_http_tunnel(
            tunnel_id="info-test",
            local_port=3000,
            path="myapp",
            custom_domains=["example.com"],
        )

        info = manager.get_tunnel_info("info-test")

        assert info["id"] == "info-test"
        assert info["type"] == "http"
        assert info["local_port"] == 3000
        assert info["path"] == "myapp"
        assert info["status"] == "pending"

    def test_tunnel_manager_shutdown_all_tunnels(self):
        """Test shutting down all active tunnels."""
        from frp_wrapper.tunnel_manager import TunnelManager

        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)
        manager.create_http_tunnel("shutdown-1", 3000, "app1")
        manager.create_tcp_tunnel("shutdown-2", 4000)

        with patch.object(manager, "_start_frp_process") as mock_start:
            mock_start.return_value = True
            manager.start_tunnel("shutdown-1")
            manager.start_tunnel("shutdown-2")

        with patch.object(manager, "_stop_frp_process") as mock_stop:
            mock_stop.return_value = True

            result = manager.shutdown_all()
            assert result is True

            active_tunnels = manager.list_active_tunnels()
            assert len(active_tunnels) == 0

    def test_tunnel_manager_integration_with_registry(self):
        """Test that manager properly integrates with registry."""
        from frp_wrapper.tunnel_manager import TunnelManager

        config = TunnelConfig(server_host="test.example.com")
        with patch("frp_wrapper.tunnel_manager.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/frpc"
            manager = TunnelManager(config)

        tunnel = manager.create_http_tunnel("integration-test", 3000, "myapp")

        registry_tunnel = manager.registry.get_tunnel("integration-test")
        assert registry_tunnel is not None
        assert registry_tunnel.id == tunnel.id

        manager.registry.update_tunnel_status(
            "integration-test", TunnelStatus.CONNECTED
        )

        info = manager.get_tunnel_info("integration-test")
        assert info["status"] == "connected"
