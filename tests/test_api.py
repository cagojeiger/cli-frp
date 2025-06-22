"""Tests for high-level API functions."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from frp_wrapper import managed_tcp_tunnel, managed_tunnel


class TestManagedTunnel:
    """Test managed_tunnel context manager."""

    @patch("frp_wrapper.api.FRPClient")
    def test_managed_tunnel_basic(self, mock_frp_client_class):
        """Test basic managed tunnel creation and cleanup."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_frp_client_class.return_value = mock_client

        mock_tunnel = Mock()
        mock_tunnel.id = "test-tunnel-id"
        mock_client.expose_path.return_value = mock_tunnel

        # Test context manager
        with managed_tunnel("example.com", 3000, "/myapp") as url:
            # Check URL format
            assert url == "https://example.com/myapp/"

            # Verify FRPClient was created with correct params
            mock_frp_client_class.assert_called_once_with(
                "example.com", auth_token=None
            )

            # Verify expose_path was called
            mock_client.expose_path.assert_called_once_with(
                local_port=3000,
                path="myapp",  # Leading slash removed
                custom_domains=["example.com"],
                auto_start=True,
            )

        # Verify cleanup (context manager exit)
        mock_client.__enter__.assert_called_once()
        mock_client.__exit__.assert_called_once()

    @patch("frp_wrapper.api.FRPClient")
    def test_managed_tunnel_with_auth(self, mock_frp_client_class):
        """Test managed tunnel with authentication."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_frp_client_class.return_value = mock_client

        mock_tunnel = Mock()
        mock_client.expose_path.return_value = mock_tunnel

        with managed_tunnel("example.com", 8080, "/api", auth_token="secret123") as url:
            assert url == "https://example.com/api/"

            # Verify auth token was passed
            mock_frp_client_class.assert_called_once_with(
                "example.com", auth_token="secret123"
            )

    @patch("frp_wrapper.api.FRPClient")
    def test_managed_tunnel_with_custom_domain(self, mock_frp_client_class):
        """Test managed tunnel with custom domain."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_frp_client_class.return_value = mock_client

        mock_tunnel = Mock()
        mock_client.expose_path.return_value = mock_tunnel

        with managed_tunnel(
            "frp.example.com", 3000, "/app", domain="app.example.com"
        ) as url:
            assert url == "https://app.example.com/app/"

            # Verify custom domain was used
            mock_client.expose_path.assert_called_once()
            call_args = mock_client.expose_path.call_args
            assert call_args.kwargs["custom_domains"] == ["app.example.com"]

    @patch("frp_wrapper.api.FRPClient")
    def test_managed_tunnel_exception_cleanup(self, mock_frp_client_class):
        """Test cleanup happens even with exception."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_frp_client_class.return_value = mock_client

        mock_tunnel = Mock()
        mock_client.expose_path.return_value = mock_tunnel

        with pytest.raises(ValueError, match="Test error"):
            with managed_tunnel("example.com", 3000, "/test"):
                # Raise exception inside context
                raise ValueError("Test error")

        # Verify cleanup still happened
        mock_client.__exit__.assert_called_once()


class TestManagedTCPTunnel:
    """Test managed_tcp_tunnel context manager."""

    @patch("frp_wrapper.api.FRPClient")
    def test_managed_tcp_tunnel_basic(self, mock_frp_client_class):
        """Test basic managed TCP tunnel creation."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_frp_client_class.return_value = mock_client

        mock_tunnel = Mock()
        mock_tunnel.id = "tcp-tunnel-id"
        mock_client.expose_tcp.return_value = mock_tunnel

        with managed_tcp_tunnel("example.com", 3306) as endpoint:
            assert endpoint == "example.com:3306"

            # Verify expose_tcp was called
            mock_client.expose_tcp.assert_called_once_with(
                local_port=3306,
                remote_port=3306,
                auto_start=True,
            )

    @patch("frp_wrapper.api.FRPClient")
    def test_managed_tcp_tunnel_custom_port(self, mock_frp_client_class):
        """Test TCP tunnel with different remote port."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_frp_client_class.return_value = mock_client

        mock_tunnel = Mock()
        mock_client.expose_tcp.return_value = mock_tunnel

        with managed_tcp_tunnel("example.com", 5432, 15432) as endpoint:
            assert endpoint == "example.com:15432"

            # Verify correct ports
            mock_client.expose_tcp.assert_called_once_with(
                local_port=5432,
                remote_port=15432,
                auto_start=True,
            )

    @patch("frp_wrapper.api.FRPClient")
    def test_managed_tcp_tunnel_with_auth(self, mock_frp_client_class):
        """Test TCP tunnel with authentication."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_frp_client_class.return_value = mock_client

        mock_tunnel = Mock()
        mock_client.expose_tcp.return_value = mock_tunnel

        with managed_tcp_tunnel("example.com", 22, auth_token="ssh-secret") as endpoint:
            assert endpoint == "example.com:22"

            # Verify auth token
            mock_frp_client_class.assert_called_once_with(
                "example.com", auth_token="ssh-secret"
            )


class TestTunnelGroup:
    """Test TunnelGroup functionality."""

    def test_tunnel_group_import(self):
        """Test that TunnelGroup can be imported."""
        from frp_wrapper import TunnelGroup, tunnel_group

        assert TunnelGroup is not None
        assert tunnel_group is not None

    def test_tunnel_group_context_import(self):
        """Test that tunnel_group_context can be imported."""
        from frp_wrapper import tunnel_group_context

        assert tunnel_group_context is not None

    @patch("frp_wrapper.api.FRPClient")
    def test_tunnel_group_context_usage(self, mock_frp_client_class):
        """Test tunnel_group_context functionality."""
        from frp_wrapper import tunnel_group_context

        # Setup mocks
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_frp_client_class.return_value = mock_client

        # Mock tunnel creation
        mock_tunnel = Mock()
        mock_tunnel.id = "test-tunnel"
        mock_client.expose_path.return_value = mock_tunnel
        mock_client.expose_tcp.return_value = mock_tunnel

        # Test the context manager
        with tunnel_group_context("example.com", auth_token="secret") as group:
            # Verify FRPClient was created
            mock_frp_client_class.assert_called_once_with(
                "example.com", auth_token="secret"
            )

            # Test adding tunnels
            group.add_http_tunnel(3000, "/web")
            group.add_tcp_tunnel(5432)

            # Verify tunnels were created
            assert len(group.tunnels) == 2
            mock_client.expose_path.assert_called_once()
            mock_client.expose_tcp.assert_called_once()
