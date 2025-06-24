"""Tests for FRP server configuration builder."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from frp_wrapper.server.config import LogLevel, ServerConfigBuilder


class TestServerConfigBuilder:
    """Test ServerConfigBuilder functionality."""

    def test_builder_initialization(self):
        """Test ServerConfigBuilder initialization."""
        builder = ServerConfigBuilder()
        assert builder._server_config is not None
        assert builder._dashboard_config is None  # Should be None initially
        assert builder._config_path is None

    def test_configure_basic(self):
        """Test basic server configuration."""
        builder = ServerConfigBuilder()
        result = builder.configure_basic(
            bind_port=8000, bind_addr="127.0.0.1", auth_token="secure-token-12345"
        )

        # Should return self for chaining
        assert result is builder

        # Check configuration
        assert builder._server_config.bind_port == 8000
        assert builder._server_config.bind_addr == "127.0.0.1"
        assert builder._server_config.auth_token == "secure-token-12345"

    def test_configure_vhost(self):
        """Test virtual host configuration."""
        builder = ServerConfigBuilder()
        result = builder.configure_vhost(
            http_port=8080, https_port=8443, subdomain_host="frp.example.com"
        )

        assert result is builder
        assert builder._server_config.vhost_http_port == 8080
        assert builder._server_config.vhost_https_port == 8443
        assert builder._server_config.subdomain_host == "frp.example.com"

    def test_enable_dashboard(self):
        """Test dashboard configuration."""
        builder = ServerConfigBuilder()
        result = builder.enable_dashboard(
            port=8500, user="superadmin", password="SuperSecure123"
        )

        assert result is builder
        assert builder._dashboard_config.enabled is True
        assert builder._dashboard_config.port == 8500
        assert builder._dashboard_config.user == "superadmin"
        assert builder._dashboard_config.password == "SuperSecure123"

    def test_configure_logging(self):
        """Test logging configuration."""
        builder = ServerConfigBuilder()
        result = builder.configure_logging(
            level=LogLevel.DEBUG, file_path="/var/log/frps.log", max_days=7
        )

        assert result is builder
        assert builder._server_config.log_level == LogLevel.DEBUG
        assert builder._server_config.log_file == "/var/log/frps.log"
        assert builder._server_config.log_max_days == 7

    def test_method_chaining(self):
        """Test method chaining."""
        builder = (
            ServerConfigBuilder()
            .configure_basic(bind_port=8000, auth_token="token12345")
            .configure_vhost(http_port=8080, subdomain_host="frp.example.com")
            .enable_dashboard(password="Admin123")
            .configure_logging(level=LogLevel.WARN)
        )

        assert builder._server_config.bind_port == 8000
        assert builder._server_config.auth_token == "token12345"
        assert builder._server_config.vhost_http_port == 8080
        assert builder._server_config.subdomain_host == "frp.example.com"
        assert builder._dashboard_config.enabled is True
        assert builder._server_config.log_level == LogLevel.WARN

    def test_build_basic_config(self):
        """Test building basic configuration file."""
        builder = ServerConfigBuilder()
        builder.configure_basic(bind_port=8000)

        config_path = builder.build()

        try:
            # Verify file exists
            assert os.path.exists(config_path)
            assert config_path.endswith(".toml")
            assert "frps_config_" in config_path

            # Verify content
            with open(config_path) as f:
                content = f.read()

            assert "# FRP Server Configuration" in content
            assert "# Generated at:" in content
            assert 'bindAddr = "0.0.0.0"' in content
            assert "bindPort = 8000" in content

        finally:
            # Cleanup
            if os.path.exists(config_path):
                os.unlink(config_path)

    def test_build_with_dashboard(self):
        """Test building configuration with dashboard."""
        builder = ServerConfigBuilder()
        builder.configure_basic(bind_port=8000, auth_token="token12345")
        builder.enable_dashboard(password="Admin123")

        config_path = builder.build()

        try:
            with open(config_path) as f:
                content = f.read()

            # Check server config
            assert "bindPort = 8000" in content
            assert 'auth.token = "token12345"' in content

            # Check dashboard config
            assert "[webServer]" in content
            assert "port = 7500" in content
            assert 'password = "Admin123"' in content

        finally:
            if os.path.exists(config_path):
                os.unlink(config_path)

    def test_build_error_handling(self):
        """Test error handling during build."""
        builder = ServerConfigBuilder()

        # Mock file creation to fail
        with patch("tempfile.mkstemp", side_effect=OSError("Mock error")):
            with pytest.raises(OSError) as exc_info:
                builder.build()
            assert "Mock error" in str(exc_info.value)

    def test_cleanup(self):
        """Test configuration file cleanup."""
        builder = ServerConfigBuilder()
        config_path = builder.build()

        assert os.path.exists(config_path)
        builder.cleanup()
        assert not os.path.exists(config_path)
        assert builder._config_path is None

        # Cleanup should be idempotent
        builder.cleanup()  # Should not raise

    def test_context_manager(self):
        """Test ServerConfigBuilder as context manager."""
        with ServerConfigBuilder() as builder:
            builder.configure_basic(bind_port=8000)
            config_path = builder.build()
            assert os.path.exists(config_path)

        # File should be cleaned up after context
        assert not os.path.exists(config_path)

    def test_context_manager_with_exception(self):
        """Test context manager cleanup on exception."""
        config_path = None

        try:
            with ServerConfigBuilder() as builder:
                builder.configure_basic(bind_port=8000)
                config_path = builder.build()
                assert os.path.exists(config_path)
                raise RuntimeError("Test exception")
        except RuntimeError:
            pass

        # File should still be cleaned up
        if config_path:
            assert not os.path.exists(config_path)

    def test_validation_in_builder(self):
        """Test that validation errors propagate through builder."""
        builder = ServerConfigBuilder()

        # Invalid port
        with pytest.raises(ValidationError):
            builder.configure_basic(bind_port=99999)

        # Invalid auth token
        with pytest.raises(ValidationError):
            builder.configure_basic(auth_token="short")

        # Invalid dashboard password
        with pytest.raises(ValidationError):
            builder.enable_dashboard(password="weak")
