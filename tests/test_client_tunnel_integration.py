from unittest.mock import Mock, patch

import pytest

from frp_wrapper.client.client import FRPClient
from frp_wrapper.client.tunnel import (
    HTTPTunnel,
    TCPTunnel,
    TunnelManager,
    TunnelManagerError,
    TunnelStatus,
    TunnelType,
)


class TestFRPClientExposePathIntegration:
    """Test suite for FRPClient expose_path method integration."""

    @pytest.fixture
    def mock_client(self):
        """Create FRPClient with mocked dependencies."""
        with patch("frp_wrapper.client.client.FRPClient.find_frp_binary") as mock_find:
            mock_find.return_value = "/usr/local/bin/frpc"
            client = FRPClient("test.example.com", auth_token="test-token")
            # Replace tunnel_manager with a mock
            client.tunnel_manager = Mock(spec=TunnelManager)
            return client

    def test_expose_path_creates_http_tunnel(self, mock_client):
        """Test that expose_path creates and registers an HTTP tunnel."""
        expected_tunnel = HTTPTunnel(
            id="http-3000-myapp", local_port=3000, path="myapp"
        )
        mock_client.tunnel_manager.create_http_tunnel = Mock(
            return_value=expected_tunnel
        )

        tunnel = mock_client.expose_path(3000, "myapp")

        assert isinstance(tunnel, HTTPTunnel)
        assert tunnel.local_port == 3000
        assert tunnel.path == "myapp"
        assert tunnel.tunnel_type == TunnelType.HTTP

        # Check that create_http_tunnel was called with expected arguments
        call_args = mock_client.tunnel_manager.create_http_tunnel.call_args
        assert call_args[1]["local_port"] == 3000
        assert call_args[1]["path"] == "myapp"
        assert call_args[1]["custom_domains"] == []
        assert call_args[1]["strip_path"] is True
        assert call_args[1]["websocket"] is True
        # Check tunnel_id starts with expected pattern
        assert call_args[1]["tunnel_id"].startswith("http-3000-myapp-")

    def test_expose_path_with_custom_domains(self, mock_client):
        """Test expose_path with custom domains."""
        expected_tunnel = HTTPTunnel(
            id="http-8080-api",
            local_port=8080,
            path="api",
            custom_domains=["api.example.com", "api.test.com"],
        )
        mock_client.tunnel_manager.create_http_tunnel = Mock(
            return_value=expected_tunnel
        )

        tunnel = mock_client.expose_path(
            8080, "api", custom_domains=["api.example.com", "api.test.com"]
        )

        assert tunnel.custom_domains == ["api.example.com", "api.test.com"]
        # Check that create_http_tunnel was called with expected arguments
        call_args = mock_client.tunnel_manager.create_http_tunnel.call_args
        assert call_args[1]["local_port"] == 8080
        assert call_args[1]["path"] == "api"
        assert call_args[1]["custom_domains"] == ["api.example.com", "api.test.com"]
        assert call_args[1]["strip_path"] is True
        assert call_args[1]["websocket"] is True
        # Check tunnel_id starts with expected pattern
        assert call_args[1]["tunnel_id"].startswith("http-8080-api-")

    def test_expose_path_with_custom_options(self, mock_client):
        """Test expose_path with custom strip_path and websocket options."""
        expected_tunnel = HTTPTunnel(
            id="http-5000-webapp",
            local_port=5000,
            path="webapp",
            strip_path=False,
            websocket=False,
        )
        mock_client.tunnel_manager.create_http_tunnel = Mock(
            return_value=expected_tunnel
        )

        tunnel = mock_client.expose_path(
            5000, "webapp", strip_path=False, websocket=False
        )

        assert tunnel.strip_path is False
        assert tunnel.websocket is False
        # Check that create_http_tunnel was called with expected arguments
        call_args = mock_client.tunnel_manager.create_http_tunnel.call_args
        assert call_args[1]["local_port"] == 5000
        assert call_args[1]["path"] == "webapp"
        assert call_args[1]["custom_domains"] == []
        assert call_args[1]["strip_path"] is False
        assert call_args[1]["websocket"] is False
        # Check tunnel_id starts with expected pattern
        assert call_args[1]["tunnel_id"].startswith("http-5000-webapp-")

    def test_expose_path_generates_unique_tunnel_id(self, mock_client):
        """Test that expose_path generates unique tunnel IDs."""
        tunnel1 = HTTPTunnel(id="http-3000-app1", local_port=3000, path="app1")
        tunnel2 = HTTPTunnel(id="http-4000-app2", local_port=4000, path="app2")

        mock_client.tunnel_manager.create_http_tunnel = Mock(
            side_effect=[tunnel1, tunnel2]
        )

        result1 = mock_client.expose_path(3000, "app1")
        result2 = mock_client.expose_path(4000, "app2")

        assert result1.id == "http-3000-app1"
        assert result2.id == "http-4000-app2"
        assert result1.id != result2.id

    def test_expose_path_validates_port_range(self, mock_client):
        """Test that expose_path validates port range."""
        with pytest.raises(ValueError, match="Local port must be between 1 and 65535"):
            mock_client.expose_path(0, "invalid-port")

        with pytest.raises(ValueError, match="Local port must be between 1 and 65535"):
            mock_client.expose_path(65536, "invalid-port")

    def test_expose_path_validates_path_format(self, mock_client):
        """Test that expose_path validates path format."""
        with pytest.raises(ValueError, match="Path cannot be empty"):
            mock_client.expose_path(3000, "")

        with pytest.raises(ValueError, match="Path should not start with"):
            mock_client.expose_path(3000, "/invalid-path")

    def test_expose_path_handles_tunnel_manager_error(self, mock_client):
        """Test that expose_path handles TunnelManager errors properly."""
        mock_client.tunnel_manager.create_http_tunnel = Mock(
            side_effect=TunnelManagerError("Registry full")
        )

        with pytest.raises(TunnelManagerError, match="Registry full"):
            mock_client.expose_path(3000, "myapp")

    def test_expose_path_auto_starts_tunnel_if_connected(self, mock_client):
        """Test that expose_path auto-starts tunnel if client is connected."""
        mock_client._connected = True
        expected_tunnel = HTTPTunnel(
            id="http-3000-autostart", local_port=3000, path="autostart"
        )
        mock_client.tunnel_manager.create_http_tunnel = Mock(
            return_value=expected_tunnel
        )
        mock_client.tunnel_manager.start_tunnel = Mock(return_value=True)

        mock_client.expose_path(3000, "autostart", auto_start=True)

        mock_client.tunnel_manager.create_http_tunnel.assert_called_once()
        # Check that start_tunnel was called with the generated tunnel_id
        call_args = mock_client.tunnel_manager.create_http_tunnel.call_args
        tunnel_id = call_args[1]["tunnel_id"]
        assert tunnel_id.startswith("http-3000-autostart-")
        mock_client.tunnel_manager.start_tunnel.assert_called_once_with(tunnel_id)

    def test_expose_path_skips_auto_start_if_not_connected(self, mock_client):
        """Test that expose_path skips auto-start if client not connected."""
        mock_client._connected = False
        expected_tunnel = HTTPTunnel(
            id="http-3000-nostart", local_port=3000, path="nostart"
        )
        mock_client.tunnel_manager.create_http_tunnel = Mock(
            return_value=expected_tunnel
        )

        mock_client.expose_path(3000, "nostart", auto_start=True)

        mock_client.tunnel_manager.create_http_tunnel.assert_called_once()
        mock_client.tunnel_manager.start_tunnel.assert_not_called()

    def test_expose_path_returns_tunnel_with_correct_properties(self, mock_client):
        """Test that expose_path returns tunnel with all expected properties."""
        expected_tunnel = HTTPTunnel(
            id="http-8080-fulltest",
            local_port=8080,
            path="fulltest",
            custom_domains=["test.example.com"],
            strip_path=False,
            websocket=True,
        )
        mock_client.tunnel_manager.create_http_tunnel = Mock(
            return_value=expected_tunnel
        )

        tunnel = mock_client.expose_path(
            8080,
            "fulltest",
            custom_domains=["test.example.com"],
            strip_path=False,
            websocket=True,
        )

        assert tunnel.id == "http-8080-fulltest"
        assert tunnel.local_port == 8080
        assert tunnel.path == "fulltest"
        assert tunnel.custom_domains == ["test.example.com"]
        assert tunnel.strip_path is False
        assert tunnel.websocket is True
        assert tunnel.tunnel_type == TunnelType.HTTP
        assert tunnel.status == TunnelStatus.PENDING


class TestFRPClientExposeTCPIntegration:
    """Test suite for FRPClient expose_tcp method integration."""

    @pytest.fixture
    def mock_client(self):
        """Create FRPClient with mocked dependencies."""
        with patch("frp_wrapper.client.client.FRPClient.find_frp_binary") as mock_find:
            mock_find.return_value = "/usr/local/bin/frpc"
            client = FRPClient("test.example.com", auth_token="test-token")
            # Replace tunnel_manager with a mock
            client.tunnel_manager = Mock(spec=TunnelManager)
            return client

    def test_expose_tcp_creates_tcp_tunnel(self, mock_client):
        """Test that expose_tcp creates and registers a TCP tunnel."""
        expected_tunnel = TCPTunnel(id="tcp-3000", local_port=3000)
        mock_client.tunnel_manager.create_tcp_tunnel = Mock(
            return_value=expected_tunnel
        )

        tunnel = mock_client.expose_tcp(3000)

        assert isinstance(tunnel, TCPTunnel)
        assert tunnel.local_port == 3000
        assert tunnel.tunnel_type == TunnelType.TCP

        call_args = mock_client.tunnel_manager.create_tcp_tunnel.call_args[1]
        assert call_args["local_port"] == 3000
        assert call_args["remote_port"] is None
        assert call_args["tunnel_id"].startswith("tcp-3000-")

    def test_expose_tcp_with_remote_port(self, mock_client):
        """Test expose_tcp with specified remote port."""
        expected_tunnel = TCPTunnel(
            id="tcp-3000-8080", local_port=3000, remote_port=8080
        )
        mock_client.tunnel_manager.create_tcp_tunnel = Mock(
            return_value=expected_tunnel
        )

        tunnel = mock_client.expose_tcp(3000, remote_port=8080)

        assert tunnel.remote_port == 8080
        # Check that create_tcp_tunnel was called with expected arguments
        call_args = mock_client.tunnel_manager.create_tcp_tunnel.call_args
        assert call_args[1]["local_port"] == 3000
        assert call_args[1]["remote_port"] == 8080
        # Check tunnel_id starts with expected pattern
        assert call_args[1]["tunnel_id"].startswith("tcp-3000-8080-")

    def test_expose_tcp_generates_unique_tunnel_id(self, mock_client):
        """Test that expose_tcp generates unique tunnel IDs."""
        tunnel1 = TCPTunnel(id="tcp-3000", local_port=3000)
        tunnel2 = TCPTunnel(id="tcp-4000", local_port=4000)

        mock_client.tunnel_manager.create_tcp_tunnel = Mock(
            side_effect=[tunnel1, tunnel2]
        )

        result1 = mock_client.expose_tcp(3000)
        result2 = mock_client.expose_tcp(4000)

        assert result1.id == "tcp-3000"
        assert result2.id == "tcp-4000"
        assert result1.id != result2.id

    def test_expose_tcp_with_remote_port_in_id(self, mock_client):
        """Test that expose_tcp includes remote port in tunnel ID when specified."""
        tunnel = TCPTunnel(id="tcp-3000-9000", local_port=3000, remote_port=9000)
        mock_client.tunnel_manager.create_tcp_tunnel = Mock(return_value=tunnel)

        result = mock_client.expose_tcp(3000, remote_port=9000)

        assert result.id == "tcp-3000-9000"
        # Check that create_tcp_tunnel was called with expected arguments
        call_args = mock_client.tunnel_manager.create_tcp_tunnel.call_args
        assert call_args[1]["local_port"] == 3000
        assert call_args[1]["remote_port"] == 9000
        # Check tunnel_id starts with expected pattern
        assert call_args[1]["tunnel_id"].startswith("tcp-3000-9000-")

    def test_expose_tcp_validates_port_range(self, mock_client):
        """Test that expose_tcp validates port range."""
        with pytest.raises(ValueError, match="Local port must be between 1 and 65535"):
            mock_client.expose_tcp(0)

        with pytest.raises(ValueError, match="Local port must be between 1 and 65535"):
            mock_client.expose_tcp(65536)

        with pytest.raises(ValueError, match="Remote port must be between 1 and 65535"):
            mock_client.expose_tcp(3000, remote_port=0)

        with pytest.raises(ValueError, match="Remote port must be between 1 and 65535"):
            mock_client.expose_tcp(3000, remote_port=65536)

    def test_expose_tcp_handles_tunnel_manager_error(self, mock_client):
        """Test that expose_tcp handles TunnelManager errors properly."""
        mock_client.tunnel_manager.create_tcp_tunnel = Mock(
            side_effect=TunnelManagerError("Port conflict")
        )

        with pytest.raises(TunnelManagerError, match="Port conflict"):
            mock_client.expose_tcp(3000)

    def test_expose_tcp_auto_starts_tunnel_if_connected(self, mock_client):
        """Test that expose_tcp auto-starts tunnel if client is connected."""
        mock_client._connected = True
        expected_tunnel = TCPTunnel(id="tcp-3000-1234", local_port=3000)
        mock_client.tunnel_manager.create_tcp_tunnel = Mock(
            return_value=expected_tunnel
        )
        mock_client.tunnel_manager.start_tunnel = Mock(return_value=True)

        mock_client.expose_tcp(3000, auto_start=True)

        mock_client.tunnel_manager.create_tcp_tunnel.assert_called_once()
        call_args = mock_client.tunnel_manager.create_tcp_tunnel.call_args[1]
        tunnel_id = call_args["tunnel_id"]
        mock_client.tunnel_manager.start_tunnel.assert_called_once_with(tunnel_id)

    def test_expose_tcp_skips_auto_start_if_not_connected(self, mock_client):
        """Test that expose_tcp skips auto-start if client not connected."""
        mock_client._connected = False
        expected_tunnel = TCPTunnel(id="tcp-3000-nostart", local_port=3000)
        mock_client.tunnel_manager.create_tcp_tunnel = Mock(
            return_value=expected_tunnel
        )

        mock_client.expose_tcp(3000, auto_start=True)

        mock_client.tunnel_manager.create_tcp_tunnel.assert_called_once()
        mock_client.tunnel_manager.start_tunnel.assert_not_called()

    def test_expose_tcp_returns_tunnel_with_correct_properties(self, mock_client):
        """Test that expose_tcp returns tunnel with all expected properties."""
        expected_tunnel = TCPTunnel(
            id="tcp-8080-9090", local_port=8080, remote_port=9090
        )
        mock_client.tunnel_manager.create_tcp_tunnel = Mock(
            return_value=expected_tunnel
        )

        tunnel = mock_client.expose_tcp(8080, remote_port=9090)

        assert tunnel.id == "tcp-8080-9090"
        assert tunnel.local_port == 8080
        assert tunnel.remote_port == 9090
        assert tunnel.tunnel_type == TunnelType.TCP
        assert tunnel.status == TunnelStatus.PENDING


class TestFRPClientTunnelLifecycleIntegration:
    """Test suite for FRPClient tunnel lifecycle management integration."""

    @pytest.fixture
    def mock_client(self):
        """Create FRPClient with mocked dependencies."""
        with patch("frp_wrapper.client.client.FRPClient.find_frp_binary") as mock_find:
            mock_find.return_value = "/usr/local/bin/frpc"
            client = FRPClient("test.example.com", auth_token="test-token")
            # Replace tunnel_manager with a mock
            client.tunnel_manager = Mock(spec=TunnelManager)
            return client

    def test_client_tunnel_manager_integration(self, mock_client):
        """Test that FRPClient properly integrates with TunnelManager."""
        assert mock_client.tunnel_manager is not None

        http_tunnel = HTTPTunnel(id="test-http", local_port=3000, path="test")
        tcp_tunnel = TCPTunnel(id="test-tcp", local_port=4000)

        mock_client.tunnel_manager.create_http_tunnel = Mock(return_value=http_tunnel)
        mock_client.tunnel_manager.create_tcp_tunnel = Mock(return_value=tcp_tunnel)

        result_http = mock_client.expose_path(3000, "test")
        result_tcp = mock_client.expose_tcp(4000)

        assert result_http == http_tunnel
        assert result_tcp == tcp_tunnel
        mock_client.tunnel_manager.create_http_tunnel.assert_called_once()
        mock_client.tunnel_manager.create_tcp_tunnel.assert_called_once()

    def test_client_lists_active_tunnels(self, mock_client):
        """Test that client can list active tunnels through tunnel manager."""
        active_tunnels = [
            HTTPTunnel(
                id="active-http",
                local_port=3000,
                path="app",
                status=TunnelStatus.CONNECTED,
            ),
            TCPTunnel(id="active-tcp", local_port=4000, status=TunnelStatus.CONNECTED),
        ]
        mock_client.tunnel_manager.list_active_tunnels = Mock(
            return_value=active_tunnels
        )

        result = mock_client.list_active_tunnels()

        assert len(result) == 2
        assert result == active_tunnels
        mock_client.tunnel_manager.list_active_tunnels.assert_called_once()

    def test_client_gets_tunnel_info(self, mock_client):
        """Test that client can get tunnel info through tunnel manager."""
        tunnel_info = {
            "id": "test-tunnel",
            "type": "http",
            "local_port": 3000,
            "path": "myapp",
            "status": "connected",
        }
        mock_client.tunnel_manager.get_tunnel_info = Mock(return_value=tunnel_info)

        result = mock_client.get_tunnel_info("test-tunnel")

        assert result == tunnel_info
        mock_client.tunnel_manager.get_tunnel_info.assert_called_once_with(
            "test-tunnel"
        )

    def test_client_starts_tunnel(self, mock_client):
        """Test that client can start tunnels through tunnel manager."""
        mock_client.tunnel_manager.start_tunnel = Mock(return_value=True)

        result = mock_client.start_tunnel("test-tunnel")

        assert result is True
        mock_client.tunnel_manager.start_tunnel.assert_called_once_with("test-tunnel")

    def test_client_stops_tunnel(self, mock_client):
        """Test that client can stop tunnels through tunnel manager."""
        mock_client.tunnel_manager.stop_tunnel = Mock(return_value=True)

        result = mock_client.stop_tunnel("test-tunnel")

        assert result is True
        mock_client.tunnel_manager.stop_tunnel.assert_called_once_with("test-tunnel")

    def test_client_removes_tunnel(self, mock_client):
        """Test that client can remove tunnels through tunnel manager."""
        removed_tunnel = HTTPTunnel(id="removed", local_port=3000, path="removed")
        mock_client.tunnel_manager.remove_tunnel = Mock(return_value=removed_tunnel)

        result = mock_client.remove_tunnel("removed")

        assert result == removed_tunnel
        mock_client.tunnel_manager.remove_tunnel.assert_called_once_with("removed")

    def test_client_shutdown_all_tunnels(self, mock_client):
        """Test that client can shutdown all tunnels through tunnel manager."""
        mock_client.tunnel_manager.shutdown_all = Mock(return_value=True)

        result = mock_client.shutdown_all_tunnels()

        assert result is True
        mock_client.tunnel_manager.shutdown_all.assert_called_once()
