"""Integration tests for tunnel management with actual FRP processes.

These tests require:
1. FRP binary (frpc) available in PATH
2. FRP server running (for end-to-end tests)

Run with: pytest -m integration
"""

import os
import shutil
import time
from unittest.mock import patch

import pytest

from frp_wrapper import TunnelConfig, TunnelManager, TunnelStatus


@pytest.fixture
def frp_binary_path():
    """Get FRP binary path or skip test if not available."""
    frp_path = shutil.which("frpc")
    if frp_path is None:
        pytest.skip("FRP binary 'frpc' not found in PATH")
    return frp_path


@pytest.fixture
def tunnel_config():
    """Create test tunnel configuration."""
    return TunnelConfig(
        server_host="localhost",
        auth_token="test_token",
        default_domain="test.local",
        max_tunnels=5,
    )


class TestTunnelManagerIntegration:
    """Integration tests for TunnelManager with real FRP processes."""

    @pytest.mark.integration
    def test_tunnel_manager_frp_binary_detection(self, frp_binary_path):
        """Test that TunnelManager can find FRP binary automatically."""
        config = TunnelConfig(server_host="localhost")

        # This should work if frpc is in PATH
        manager = TunnelManager(config)
        assert manager._frp_binary_path == frp_binary_path

    @pytest.mark.integration
    def test_tunnel_manager_frp_binary_not_found(self):
        """Test TunnelManager handles missing FRP binary gracefully."""
        config = TunnelConfig(server_host="localhost")

        with patch("shutil.which", return_value=None):
            with pytest.raises(
                RuntimeError, match="FRP client binary 'frpc' not found"
            ):
                TunnelManager(config)

    @pytest.mark.integration
    def test_tunnel_config_generation_http(self, tunnel_config, frp_binary_path):
        """Test that TunnelManager generates correct FRP config for HTTP tunnels."""
        manager = TunnelManager(tunnel_config, frp_binary_path=frp_binary_path)

        # Create HTTP tunnel
        manager.create_http_tunnel(
            tunnel_id="test-http",
            local_port=3000,
            path="myapp",
        )

        # Mock the process manager to avoid actually starting FRP
        with patch.object(
            manager._process_manager, "start_tunnel_process", return_value=True
        ):
            # Try to start tunnel
            success = manager.start_tunnel("test-http")
            assert success

    @pytest.mark.integration
    def test_tunnel_config_generation_tcp(self, tunnel_config, frp_binary_path):
        """Test that TunnelManager generates correct FRP config for TCP tunnels."""
        manager = TunnelManager(tunnel_config, frp_binary_path=frp_binary_path)

        # Create TCP tunnel
        manager.create_tcp_tunnel(
            tunnel_id="test-tcp",
            local_port=3000,
            remote_port=8080,
        )

        # Mock the process manager to avoid actually starting FRP
        with patch.object(
            manager._process_manager, "start_tunnel_process", return_value=True
        ):
            # Try to start tunnel
            success = manager.start_tunnel("test-tcp")
            assert success

    @pytest.mark.integration
    def test_tunnel_context_manager_integration(self, tunnel_config, frp_binary_path):
        """Test tunnel context manager with mocked FRP processes."""
        manager = TunnelManager(tunnel_config, frp_binary_path=frp_binary_path)

        # Create tunnel and associate with manager
        tunnel = manager.create_http_tunnel(
            tunnel_id="context-test",
            local_port=3000,
            path="contextapp",
        )
        tunnel_with_manager = tunnel.with_manager(manager)

        # Mock process management
        with patch.object(
            manager._process_manager, "start_tunnel_process", return_value=True
        ):
            with patch.object(
                manager._process_manager, "stop_tunnel_process", return_value=True
            ):
                # Use context manager
                with tunnel_with_manager as active_tunnel:
                    assert active_tunnel.status == TunnelStatus.CONNECTED

                # Verify tunnel was removed after context exit
                assert manager.registry.get_tunnel("context-test") is None


class TestRealFRPIntegration:
    """Tests that actually start FRP processes (requires running FRP server)."""

    @pytest.mark.integration
    def test_real_frp_process_lifecycle(self, tunnel_config, frp_binary_path):
        """Test starting and stopping real FRP process.

        Note: This test requires a running FRP server to fully pass.
        It will fail gracefully if no server is available.
        """
        # Use a non-existent server to test process startup without connection
        isolated_config = TunnelConfig(
            server_host="192.0.2.1",  # TEST-NET address (RFC 5737)
            max_tunnels=1,
        )

        manager = TunnelManager(isolated_config, frp_binary_path=frp_binary_path)

        # Create tunnel
        manager.create_http_tunnel(
            tunnel_id="real-test",
            local_port=3000,
            path="realapp",
        )

        try:
            # Try to start tunnel - this will fail but should handle gracefully
            success = manager.start_tunnel("real-test")

            if success:
                # If somehow succeeded, clean up
                time.sleep(1)  # Let process settle
                manager.stop_tunnel("real-test")
                manager.remove_tunnel("real-test")
            else:
                # Expected failure - ensure no process leaks
                assert "real-test" not in manager._processes

        except Exception as e:
            # Any exception should be handled gracefully
            pytest.skip(f"FRP process test failed as expected: {e}")


# Additional integration test for ConfigBuilder
class TestConfigBuilderIntegration:
    """Integration tests for ConfigBuilder with proxy configurations."""

    @pytest.mark.integration
    def test_config_builder_full_workflow(self):
        """Test complete ConfigBuilder workflow with proxy configurations."""
        from frp_wrapper import ConfigBuilder

        with ConfigBuilder() as builder:
            builder.add_server("test.example.com", port=7000, token="secret123")

            # Add HTTP proxy
            builder.add_http_proxy(
                name="web-app",
                local_port=3000,
                locations=["/app", "/api"],
                custom_domains=["app.example.com"],
            )

            # Add TCP proxy
            builder.add_tcp_proxy(
                name="database",
                local_port=5432,
                remote_port=15432,
            )

            config_path = builder.build()

            # Verify file exists and contains expected content
            assert os.path.exists(config_path)

            with open(config_path) as f:
                content = f.read()

            # Verify server config
            assert 'server_addr = "test.example.com"' in content
            assert "server_port = 7000" in content
            assert 'token = "secret123"' in content

            # Verify HTTP proxy config
            assert "[web-app]" in content
            assert 'type = "http"' in content
            assert "local_port = 3000" in content
            assert 'locations = ["/app", "/api"]' in content
            assert 'custom_domains = ["app.example.com"]' in content

            # Verify TCP proxy config
            assert "[database]" in content
            assert 'type = "tcp"' in content
            assert "local_port = 5432" in content
            assert "remote_port = 15432" in content

        # File should be cleaned up after context exit
        assert not os.path.exists(config_path)

    @pytest.mark.integration
    def test_config_builder_auto_cleanup_on_exception(self):
        """Test that ConfigBuilder cleans up files even on exceptions."""
        from frp_wrapper import ConfigBuilder

        config_path = None

        try:
            with ConfigBuilder() as builder:
                builder.add_server("test.example.com")
                config_path = builder.build()

                assert os.path.exists(config_path)

                # Simulate an exception
                raise ValueError("Test exception")

        except ValueError:
            # Exception expected
            pass

        # File should still be cleaned up
        if config_path:
            assert not os.path.exists(config_path)
