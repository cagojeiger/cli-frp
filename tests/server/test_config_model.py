"""Tests for FRP server configuration model."""

import pytest
from pydantic import ValidationError

from frp_wrapper.server.config import AuthMethod, LogLevel, ServerConfig


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
