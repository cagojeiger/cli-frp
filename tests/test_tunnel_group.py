import pytest
from unittest.mock import Mock, patch

from frp_wrapper.common.context_config import TunnelGroupConfig
from frp_wrapper.common.exceptions import TunnelError
from frp_wrapper.tunnels.group import TunnelGroup, tunnel_group
from frp_wrapper.tunnels.models import HTTPTunnel, TCPTunnel

class TestTunnelGroup:
    @pytest.fixture
    def mock_client(self):
        """Create mock client for TunnelGroup tests"""
        client = Mock()
        return client

    @pytest.fixture
    def mock_http_tunnel(self):
        """Create mock HTTP tunnel"""
        tunnel = Mock(spec=HTTPTunnel)
        tunnel.tunnel_id = "http-test-123"
        tunnel.manager = Mock()
        return tunnel

    @pytest.fixture
    def mock_tcp_tunnel(self):
        """Create mock TCP tunnel"""
        tunnel = Mock(spec=TCPTunnel)
        tunnel.tunnel_id = "tcp-test-456"
        tunnel.manager = Mock()
        return tunnel

    def test_tunnel_group_creation(self, mock_client):
        """Test TunnelGroup creation with Pydantic config"""
        config = TunnelGroupConfig(group_name="test-group")
        group = TunnelGroup(mock_client, config)

        assert group.config.group_name == "test-group"
        assert group.config.max_tunnels == 10
        assert len(group.tunnels) == 0

    def test_tunnel_group_creation_with_defaults(self, mock_client):
        """Test TunnelGroup creation with default config"""
        group = TunnelGroup(mock_client)

        assert group.config.group_name == "default"
        assert group.config.max_tunnels == 10
        assert len(group.tunnels) == 0

    def test_tunnel_group_add_http_tunnel(self, mock_client, mock_http_tunnel):
        """Test adding HTTP tunnel to group"""
        config = TunnelGroupConfig(group_name="test-group", max_tunnels=3)
        group = TunnelGroup(mock_client, config)

        mock_client.expose_path.return_value = mock_http_tunnel

        result = group.add_http_tunnel(3000, "app")

        assert result == group  # Should return self for chaining
        assert len(group.tunnels) == 1
        assert group.tunnels[0] == mock_http_tunnel
        mock_client.expose_path.assert_called_once_with(3000, "app")

    def test_tunnel_group_add_tcp_tunnel(self, mock_client, mock_tcp_tunnel):
        """Test adding TCP tunnel to group"""
        config = TunnelGroupConfig(group_name="test-group", max_tunnels=3)
        group = TunnelGroup(mock_client, config)

        mock_client.expose_tcp.return_value = mock_tcp_tunnel

        result = group.add_tcp_tunnel(3001)

        assert result == group  # Should return self for chaining
        assert len(group.tunnels) == 1
        assert group.tunnels[0] == mock_tcp_tunnel
        mock_client.expose_tcp.assert_called_once_with(3001)

    def test_tunnel_group_max_tunnels_limit(self, mock_client):
        """Test TunnelGroup respects max tunnels limit"""
        config = TunnelGroupConfig(group_name="test-group", max_tunnels=2)
        group = TunnelGroup(mock_client, config)

        mock_client.expose_path.return_value = Mock(tunnel_id="tunnel1")
        mock_client.expose_tcp.return_value = Mock(tunnel_id="tunnel2")

        group.add_http_tunnel(3000, "app1")
        group.add_tcp_tunnel(3001)

        with pytest.raises(TunnelError, match="Maximum tunnels"):
            group.add_http_tunnel(3002, "app3")

    def test_tunnel_group_chaining(self, mock_client):
        """Test TunnelGroup method chaining"""
        config = TunnelGroupConfig(group_name="test-group", max_tunnels=5)
        group = TunnelGroup(mock_client, config)

        mock_client.expose_path.return_value = Mock(tunnel_id="http1")
        mock_client.expose_tcp.return_value = Mock(tunnel_id="tcp1")

        result = (group
                  .add_http_tunnel(3000, "app1")
                  .add_tcp_tunnel(3001)
                  .add_http_tunnel(3002, "app2"))

        assert result == group
        assert len(group.tunnels) == 3

    def test_tunnel_group_start_all(self, mock_client, mock_http_tunnel, mock_tcp_tunnel):
        """Test starting all tunnels in group"""
        group = TunnelGroup(mock_client)
        group.tunnels = [mock_http_tunnel, mock_tcp_tunnel]

        mock_http_tunnel.manager.start_tunnel.return_value = True
        mock_tcp_tunnel.manager.start_tunnel.return_value = True

        result = group.start_all()

        assert result is True
        mock_http_tunnel.manager.start_tunnel.assert_called_once_with("http-test-123")
        mock_tcp_tunnel.manager.start_tunnel.assert_called_once_with("tcp-test-456")

    def test_tunnel_group_start_all_with_failures(self, mock_client, mock_http_tunnel):
        """Test starting all tunnels with some failures"""
        group = TunnelGroup(mock_client)
        group.tunnels = [mock_http_tunnel]

        mock_http_tunnel.manager.start_tunnel.side_effect = Exception("Start failed")

        result = group.start_all()

        assert result is False

    def test_tunnel_group_stop_all_lifo(self, mock_client):
        """Test stopping all tunnels in LIFO order"""
        config = TunnelGroupConfig(group_name="test", cleanup_order="lifo")
        group = TunnelGroup(mock_client, config)

        tunnel1 = Mock(tunnel_id="tunnel1", manager=Mock())
        tunnel2 = Mock(tunnel_id="tunnel2", manager=Mock())
        tunnel3 = Mock(tunnel_id="tunnel3", manager=Mock())
        
        group.tunnels = [tunnel1, tunnel2, tunnel3]

        result = group.stop_all()

        assert result is True
        assert tunnel3.manager.stop_tunnel.call_count == 1
        assert tunnel2.manager.stop_tunnel.call_count == 1
        assert tunnel1.manager.stop_tunnel.call_count == 1

    def test_tunnel_group_stop_all_fifo(self, mock_client):
        """Test stopping all tunnels in FIFO order"""
        config = TunnelGroupConfig(group_name="test", cleanup_order="fifo")
        group = TunnelGroup(mock_client, config)

        tunnel1 = Mock(tunnel_id="tunnel1", manager=Mock())
        tunnel2 = Mock(tunnel_id="tunnel2", manager=Mock())
        
        group.tunnels = [tunnel1, tunnel2]

        result = group.stop_all()

        assert result is True
        tunnel1.manager.stop_tunnel.assert_called_once()
        tunnel2.manager.stop_tunnel.assert_called_once()

    def test_tunnel_group_context_manager(self, mock_client):
        """Test TunnelGroup as context manager"""
        config = TunnelGroupConfig(group_name="test-group", cleanup_order="lifo")
        group = TunnelGroup(mock_client, config)

        mock_tunnel = Mock(tunnel_id="test-tunnel", manager=Mock())
        group.tunnels = [mock_tunnel]

        group._resource_tracker.register_resource(
            mock_tunnel.tunnel_id, mock_tunnel, lambda: group._cleanup_tunnel(mock_tunnel)
        )

        with group as ctx:
            assert ctx == group

        mock_tunnel.manager.stop_tunnel.assert_called_once_with("test-tunnel")
        mock_tunnel.manager.remove_tunnel.assert_called_once_with("test-tunnel")

    def test_tunnel_group_context_manager_with_errors(self, mock_client):
        """Test TunnelGroup context manager with cleanup errors"""
        group = TunnelGroup(mock_client)

        mock_tunnel = Mock(tunnel_id="test-tunnel", manager=Mock())
        mock_tunnel.manager.stop_tunnel.side_effect = Exception("Cleanup failed")
        
        group._resource_tracker.register_resource(
            mock_tunnel.tunnel_id, mock_tunnel, lambda: group._cleanup_tunnel(mock_tunnel)
        )

        with group:
            pass

    def test_tunnel_group_len_and_iter(self, mock_client):
        """Test TunnelGroup __len__ and __iter__"""
        group = TunnelGroup(mock_client)
        
        tunnel1 = Mock()
        tunnel2 = Mock()
        group.tunnels = [tunnel1, tunnel2]

        assert len(group) == 2
        assert list(group) == [tunnel1, tunnel2]

    def test_cleanup_tunnel_method(self, mock_client):
        """Test _cleanup_tunnel method"""
        group = TunnelGroup(mock_client)
        
        mock_tunnel = Mock()
        mock_tunnel.tunnel_id = "test-tunnel"
        mock_tunnel.manager = Mock()

        group._cleanup_tunnel(mock_tunnel)

        mock_tunnel.manager.stop_tunnel.assert_called_once_with("test-tunnel")
        mock_tunnel.manager.remove_tunnel.assert_called_once_with("test-tunnel")

    def test_cleanup_tunnel_method_no_manager(self, mock_client):
        """Test _cleanup_tunnel method with no manager"""
        group = TunnelGroup(mock_client)
        
        mock_tunnel = Mock()
        mock_tunnel.tunnel_id = "test-tunnel"
        del mock_tunnel.manager  # Remove manager attribute

        group._cleanup_tunnel(mock_tunnel)

    def test_cleanup_tunnel_method_with_exception(self, mock_client):
        """Test _cleanup_tunnel method with exception"""
        group = TunnelGroup(mock_client)
        
        mock_tunnel = Mock()
        mock_tunnel.tunnel_id = "test-tunnel"
        mock_tunnel.manager = Mock()
        mock_tunnel.manager.stop_tunnel.side_effect = Exception("Stop failed")

        group._cleanup_tunnel(mock_tunnel)

class TestTunnelGroupFunction:
    def test_tunnel_group_function(self):
        """Test tunnel_group convenience function"""
        mock_client = Mock()
        
        with tunnel_group(mock_client, group_name="test", max_tunnels=5) as group:
            assert isinstance(group, TunnelGroup)
            assert group.config.group_name == "test"
            assert group.config.max_tunnels == 5

    def test_tunnel_group_function_with_defaults(self):
        """Test tunnel_group function with default values"""
        mock_client = Mock()
        
        with tunnel_group(mock_client) as group:
            assert isinstance(group, TunnelGroup)
            assert group.config.group_name == "default"
            assert group.config.max_tunnels == 10
