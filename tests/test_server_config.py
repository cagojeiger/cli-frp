"""Tests for FRP server configuration models and builder."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from frp_wrapper.server.config import (
    AuthMethod,
    DashboardConfig,
    LogLevel,
    ServerConfig,
    ServerConfigBuilder,
)


class TestServerConfig:
    """Test ServerConfig model validation and serialization."""

    def test_server_config_defaults(self):
        """Test ServerConfig with default values."""
        config = ServerConfig()

        assert config.bind_addr == "0.0.0.0"
        assert config.bind_port == 7000
        assert config.vhost_http_port == 80
        assert config.vhost_https_port == 443
        assert config.auth_method == AuthMethod.TOKEN
        assert config.auth_token is None
        assert config.subdomain_host is None
        assert config.log_level == LogLevel.INFO
        assert config.log_max_days == 3
        assert config.max_pool_count == 5
        assert config.max_ports_per_client == 0
        assert config.heartbeat_timeout == 90

    def test_server_config_custom_values(self):
        """Test ServerConfig with custom values."""
        config = ServerConfig(
            bind_addr="127.0.0.1",
            bind_port=8000,
            kcp_bind_port=8001,
            vhost_http_port=8080,
            vhost_https_port=8443,
            auth_token="secure-token-12345",
            subdomain_host="frp.example.com",
            log_level=LogLevel.DEBUG,
            log_file="/var/log/frps.log",
            log_max_days=7,
            max_pool_count=10,
            max_ports_per_client=5,
            heartbeat_timeout=120,
        )

        assert config.bind_addr == "127.0.0.1"
        assert config.bind_port == 8000
        assert config.kcp_bind_port == 8001
        assert config.vhost_http_port == 8080
        assert config.vhost_https_port == 8443
        assert config.auth_token == "secure-token-12345"
        assert config.subdomain_host == "frp.example.com"
        assert config.log_level == LogLevel.DEBUG
        assert config.log_file == "/var/log/frps.log"
        assert config.log_max_days == 7
        assert config.max_pool_count == 10
        assert config.max_ports_per_client == 5
        assert config.heartbeat_timeout == 120

    def test_port_validation(self):
        """Test port range validation."""
        # Valid ports
        config = ServerConfig(bind_port=1, vhost_http_port=65535)
        assert config.bind_port == 1
        assert config.vhost_http_port == 65535

        # Invalid ports
        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(bind_port=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(bind_port=65536)
        assert "less than or equal to 65535" in str(exc_info.value)

    def test_auth_token_validation(self):
        """Test auth token validation."""
        # Valid tokens
        config = ServerConfig(auth_token="complex-TOKEN-123")
        assert config.auth_token == "complex-TOKEN-123"

        # Too short
        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(auth_token="short")
        assert "at least 8 characters" in str(exc_info.value)

        # Too simple (all same characters)
        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(auth_token="aaaaaaaa")
        assert "diverse characters" in str(exc_info.value)

        # Simple but with minimal diversity
        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(auth_token="11111112")
        assert "diverse characters" in str(exc_info.value)

    def test_subdomain_host_validation(self):
        """Test subdomain host validation."""
        # Valid domains
        config = ServerConfig(subdomain_host="frp.example.com")
        assert config.subdomain_host == "frp.example.com"

        config = ServerConfig(subdomain_host="sub.domain.example.com")
        assert config.subdomain_host == "sub.domain.example.com"

        # Invalid domains
        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(subdomain_host="no-dots")
        assert "must be a valid domain" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(subdomain_host="")
        assert "must be a valid domain" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(subdomain_host="invalid..domain")
        assert "Invalid domain part" in str(exc_info.value)

    def test_log_configuration(self):
        """Test logging configuration validation."""
        # Valid log settings
        config = ServerConfig(
            log_level=LogLevel.TRACE, log_max_days=365, log_file="/var/log/frps.log"
        )
        assert config.log_level == LogLevel.TRACE
        assert config.log_max_days == 365

        # Invalid log retention days
        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(log_max_days=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(log_max_days=366)
        assert "less than or equal to 365" in str(exc_info.value)

    def test_performance_settings(self):
        """Test performance settings validation."""
        # Valid settings
        config = ServerConfig(
            max_pool_count=50, max_ports_per_client=10, heartbeat_timeout=180
        )
        assert config.max_pool_count == 50
        assert config.max_ports_per_client == 10
        assert config.heartbeat_timeout == 180

        # Invalid settings
        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(max_pool_count=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(heartbeat_timeout=20)
        assert "greater than or equal to 30" in str(exc_info.value)

    def test_to_toml_basic(self):
        """Test basic TOML generation."""
        config = ServerConfig()
        toml = config.to_toml()

        assert 'bindAddr = "0.0.0.0"' in toml
        assert "bindPort = 7000" in toml
        assert "vhostHTTPPort = 80" in toml
        assert "vhostHTTPSPort = 443" in toml
        assert 'log.level = "info"' in toml
        assert "log.maxDays = 3" in toml
        assert "maxPoolCount = 5" in toml
        assert "heartbeatTimeout = 90" in toml

        # Should not include optional fields
        assert "kcpBindPort" not in toml
        assert "auth.token" not in toml
        assert "subDomainHost" not in toml

    def test_to_toml_with_auth(self):
        """Test TOML generation with authentication."""
        config = ServerConfig(auth_token="secure-token-12345")
        toml = config.to_toml()

        assert 'auth.method = "token"' in toml
        assert 'auth.token = "secure-token-12345"' in toml

    def test_to_toml_full(self):
        """Test TOML generation with all options."""
        config = ServerConfig(
            bind_addr="127.0.0.1",
            bind_port=8000,
            kcp_bind_port=8001,
            vhost_http_port=8080,
            vhost_https_port=8443,
            auth_token="secure-token-12345",
            subdomain_host="frp.example.com",
            custom_404_page="/path/to/404.html",
            log_level=LogLevel.DEBUG,
            log_file="/var/log/frps.log",
            log_max_days=7,
            max_pool_count=10,
            max_ports_per_client=5,
            heartbeat_timeout=120,
        )
        toml = config.to_toml()

        # Check all fields are present
        assert 'bindAddr = "127.0.0.1"' in toml
        assert "bindPort = 8000" in toml
        assert "kcpBindPort = 8001" in toml
        assert "vhostHTTPPort = 8080" in toml
        assert "vhostHTTPSPort = 8443" in toml
        assert 'auth.method = "token"' in toml
        assert 'auth.token = "secure-token-12345"' in toml
        assert 'subDomainHost = "frp.example.com"' in toml
        assert 'custom404Page = "/path/to/404.html"' in toml
        assert 'log.level = "debug"' in toml
        assert 'log.file = "/var/log/frps.log"' in toml
        assert "log.maxDays = 7" in toml
        assert "maxPoolCount = 10" in toml
        assert "maxPortsPerClient = 5" in toml
        assert "heartbeatTimeout = 120" in toml


class TestDashboardConfig:
    """Test DashboardConfig model validation."""

    def test_dashboard_config_defaults(self):
        """Test DashboardConfig with default values."""
        config = DashboardConfig(password="Admin123")

        assert config.enabled is False
        assert config.port == 7500
        assert config.user == "admin"
        assert config.password == "Admin123"
        assert config.assets_dir is None

    def test_dashboard_config_custom(self):
        """Test DashboardConfig with custom values."""
        config = DashboardConfig(
            enabled=True,
            port=8500,
            user="superadmin",
            password="SuperSecure123",
            assets_dir="/path/to/assets",
        )

        assert config.enabled is True
        assert config.port == 8500
        assert config.user == "superadmin"
        assert config.password == "SuperSecure123"
        assert config.assets_dir == "/path/to/assets"

    def test_password_validation(self):
        """Test password strength validation."""
        # Valid passwords
        DashboardConfig(password="Admin123")
        DashboardConfig(password="SuperSecure123!")

        # Too short
        with pytest.raises(ValidationError) as exc_info:
            DashboardConfig(password="Abc1")
        assert "at least 6 characters" in str(exc_info.value)

        # Missing uppercase
        with pytest.raises(ValidationError) as exc_info:
            DashboardConfig(password="admin123")
        assert "uppercase, lowercase, and numbers" in str(exc_info.value)

        # Missing lowercase
        with pytest.raises(ValidationError) as exc_info:
            DashboardConfig(password="ADMIN123")
        assert "uppercase, lowercase, and numbers" in str(exc_info.value)

        # Missing numbers
        with pytest.raises(ValidationError) as exc_info:
            DashboardConfig(password="AdminPass")
        assert "uppercase, lowercase, and numbers" in str(exc_info.value)

    def test_user_validation(self):
        """Test username validation."""
        # Valid usernames
        config = DashboardConfig(user="adm", password="Admin123")
        assert config.user == "adm"

        # Too short
        with pytest.raises(ValidationError) as exc_info:
            DashboardConfig(user="ab", password="Admin123")
        assert "at least 3 characters" in str(exc_info.value)

    def test_to_toml_section_disabled(self):
        """Test TOML generation when dashboard is disabled."""
        config = DashboardConfig(password="Admin123")
        toml = config.to_toml_section()

        assert toml == ""  # Empty when disabled

    def test_to_toml_section_enabled(self):
        """Test TOML generation when dashboard is enabled."""
        config = DashboardConfig(
            enabled=True, port=8500, user="superadmin", password="SuperSecure123"
        )
        toml = config.to_toml_section()

        assert "[webServer]" in toml
        assert 'addr = "0.0.0.0"' in toml
        assert "port = 8500" in toml
        assert 'user = "superadmin"' in toml
        assert 'password = "SuperSecure123"' in toml

        # Should not include assets_dir when None
        assert "assetsDir" not in toml

    def test_to_toml_section_with_assets(self):
        """Test TOML generation with custom assets directory."""
        config = DashboardConfig(
            enabled=True, password="Admin123", assets_dir="/custom/assets"
        )
        toml = config.to_toml_section()

        assert 'assetsDir = "/custom/assets"' in toml


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
