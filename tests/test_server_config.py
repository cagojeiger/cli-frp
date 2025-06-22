"""Tests for server configuration models.

Following TDD approach - tests written first to define expected behavior.
"""

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from frp_wrapper.server.config import (
    AuthMethod,
    CompleteServerConfig,
    DashboardConfig,
    LogLevel,
    ServerConfig,
    SSLConfig,
)


class TestServerConfig:
    """Test ServerConfig Pydantic model"""

    def test_server_config_defaults(self):
        """Test ServerConfig with default values"""
        config = ServerConfig()

        assert config.bind_addr == "0.0.0.0"
        assert config.bind_port == 7000
        assert config.vhost_http_port == 80
        assert config.vhost_https_port == 443
        assert config.auth_method == AuthMethod.TOKEN
        assert config.log_level == LogLevel.INFO
        assert config.max_pool_count == 5
        assert config.heartbeat_timeout == 90

    def test_server_config_custom_values(self):
        """Test ServerConfig with custom values"""
        config = ServerConfig(
            bind_addr="127.0.0.1",
            bind_port=7001,
            auth_token="SecureToken123!",
            subdomain_host="tunnel.example.com",
            log_level=LogLevel.DEBUG,
            max_pool_count=10
        )

        assert config.bind_addr == "127.0.0.1"
        assert config.bind_port == 7001
        assert config.auth_token == "SecureToken123!"
        assert config.subdomain_host == "tunnel.example.com"
        assert config.log_level == LogLevel.DEBUG
        assert config.max_pool_count == 10

    def test_server_config_port_validation(self):
        """Test port validation"""
        config = ServerConfig(bind_port=8000, vhost_http_port=8080)
        assert config.bind_port == 8000
        assert config.vhost_http_port == 8080

        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            ServerConfig(bind_port=0)

        with pytest.raises(ValidationError, match="less than or equal to 65535"):
            ServerConfig(bind_port=70000)

    def test_auth_token_validation(self):
        """Test auth token validation"""
        config = ServerConfig(auth_token="SecureToken123!")
        assert config.auth_token == "SecureToken123!"

        with pytest.raises(ValidationError, match="at least 8 characters"):
            ServerConfig(auth_token="short")

        with pytest.raises(ValidationError, match="diverse characters"):
            ServerConfig(auth_token="11111111")

    def test_subdomain_host_validation(self):
        """Test subdomain host validation"""
        config = ServerConfig(subdomain_host="tunnel.example.com")
        assert config.subdomain_host == "tunnel.example.com"

        config = ServerConfig(subdomain_host="sub.domain.co.uk")
        assert config.subdomain_host == "sub.domain.co.uk"

        with pytest.raises(ValidationError, match="valid domain"):
            ServerConfig(subdomain_host="invalid")

        with pytest.raises(ValidationError, match="valid domain"):
            ServerConfig(subdomain_host="")

    def test_toml_generation(self):
        """Test TOML configuration generation"""
        config = ServerConfig(
            bind_port=7001,
            auth_token="SecureToken123!",
            subdomain_host="tunnel.example.com",
            log_level=LogLevel.DEBUG
        )

        toml_content = config.to_toml()

        assert "bindPort = 7001" in toml_content
        assert 'auth.token = "SecureToken123!"' in toml_content
        assert 'subDomainHost = "tunnel.example.com"' in toml_content
        assert 'log.level = "debug"' in toml_content


class TestDashboardConfig:
    """Test DashboardConfig Pydantic model"""

    def test_dashboard_config_defaults(self):
        """Test DashboardConfig with defaults"""
        config = DashboardConfig()

        assert config.enabled is False
        assert config.port == 7500
        assert config.user == "admin"
        assert config.password is None

    def test_dashboard_config_enabled(self):
        """Test enabled dashboard configuration"""
        config = DashboardConfig(
            enabled=True,
            port=8080,
            user="dashboard_admin",
            password="SecureDashPass123!"
        )

        assert config.enabled is True
        assert config.port == 8080
        assert config.user == "dashboard_admin"
        assert config.password == "SecureDashPass123!"

    def test_dashboard_password_validation(self):
        """Test dashboard password validation"""
        config = DashboardConfig(enabled=True, password="SecurePass123!")
        assert config.password == "SecurePass123!"

        with pytest.raises(ValidationError, match="at least 8 characters"):
            DashboardConfig(enabled=True, password="short")

    def test_dashboard_port_validation(self):
        """Test dashboard port validation"""
        config = DashboardConfig(port=8080)
        assert config.port == 8080

        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            DashboardConfig(port=0)

        with pytest.raises(ValidationError, match="less than or equal to 65535"):
            DashboardConfig(port=70000)


class TestSSLConfig:
    """Test SSLConfig Pydantic model"""

    def test_ssl_config_defaults(self):
        """Test SSLConfig with defaults"""
        config = SSLConfig()

        assert config.enabled is False
        assert config.use_letsencrypt is False
        assert config.cert_file is None
        assert config.key_file is None

    def test_ssl_config_manual_certs(self):
        """Test SSL with manual certificate files"""
        config = SSLConfig(
            enabled=True,
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem"
        )

        assert config.enabled is True
        assert config.cert_file == "/path/to/cert.pem"
        assert config.key_file == "/path/to/key.pem"
        assert config.use_letsencrypt is False

    def test_ssl_config_letsencrypt(self):
        """Test SSL with Let's Encrypt"""
        config = SSLConfig(
            enabled=True,
            use_letsencrypt=True,
            letsencrypt_email="admin@example.com",
            letsencrypt_domains=["tunnel.example.com", "api.example.com"]
        )

        assert config.enabled is True
        assert config.use_letsencrypt is True
        assert config.letsencrypt_email == "admin@example.com"
        assert len(config.letsencrypt_domains) == 2

    def test_ssl_config_validation(self):
        """Test SSL configuration validation"""
        with pytest.raises(ValidationError, match="Cannot use both manual certificates and Let's Encrypt"):
            SSLConfig(
                enabled=True,
                cert_file="/path/to/cert.pem",
                key_file="/path/to/key.pem",
                use_letsencrypt=True,
                letsencrypt_email="admin@example.com"
            )

        with pytest.raises(ValidationError, match="Let's Encrypt email is required"):
            SSLConfig(
                enabled=True,
                use_letsencrypt=True
            )

        with pytest.raises(ValidationError, match="Both cert_file and key_file are required"):
            SSLConfig(
                enabled=True,
                cert_file="/path/to/cert.pem"
            )


class TestCompleteServerConfig:
    """Test CompleteServerConfig integration model"""

    def test_complete_config_creation(self):
        """Test creating complete server configuration"""
        config = CompleteServerConfig(
            server=ServerConfig(
                bind_port=7001,
                auth_token="SecureToken123!",
                subdomain_host="tunnel.example.com"
            ),
            dashboard=DashboardConfig(
                enabled=True,
                password="DashPass123!"
            ),
            ssl=SSLConfig(
                enabled=True,
                use_letsencrypt=True,
                letsencrypt_email="admin@example.com",
                letsencrypt_domains=["tunnel.example.com"]
            ),
            description="Test server configuration"
        )

        assert config.server.bind_port == 7001
        assert config.dashboard.enabled is True
        assert config.ssl.use_letsencrypt is True
        assert config.description == "Test server configuration"

    def test_complete_config_toml_generation(self):
        """Test complete TOML generation"""
        config = CompleteServerConfig(
            server=ServerConfig(
                bind_port=7001,
                auth_token="SecureToken123!",
                subdomain_host="tunnel.example.com"
            ),
            dashboard=DashboardConfig(
                enabled=True,
                port=7500,
                password="AdminPass123"
            ),
            description="Production server"
        )

        toml_content = config.generate_toml()

        assert "# FRP Server Configuration" in toml_content
        assert "# Description: Production server" in toml_content

        assert "bindPort = 7001" in toml_content
        assert 'auth.token = "SecureToken123!"' in toml_content

        assert "[webServer]" in toml_content
        assert "port = 7500" in toml_content

    def test_config_file_operations(self):
        """Test saving and loading configuration files"""
        config = CompleteServerConfig(
            server=ServerConfig(
                bind_port=7001,
                auth_token="SecureToken123!"
            ),
            dashboard=DashboardConfig(
                enabled=True,
                password="AdminPass123"
            ),
            description="Test config file operations"
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            temp_path = Path(f.name)

        try:
            config.save_to_file(temp_path)

            assert temp_path.exists()
            content = temp_path.read_text()
            assert "bindPort = 7001" in content
            assert "[webServer]" in content

        finally:
            temp_path.unlink(missing_ok=True)


class TestServerConfigIntegration:
    def test_production_config_example(self):
        """Test creating a production-ready configuration"""
        config = CompleteServerConfig(
            server=ServerConfig(
                bind_port=7000,
                vhost_http_port=80,
                vhost_https_port=443,
                auth_token="ProductionSecureToken123!",
                subdomain_host="tunnel.example.com",
                log_level=LogLevel.INFO,
                log_file="/var/log/frp/frps.log",
                max_ports_per_client=10,
                heartbeat_timeout=90
            ),
            dashboard=DashboardConfig(
                enabled=True,
                port=7500,
                user="admin",
                password="SecureDashboardPass123!"
            ),
            ssl=SSLConfig(
                enabled=True,
                use_letsencrypt=True,
                letsencrypt_email="admin@example.com",
                letsencrypt_domains=["tunnel.example.com"]
            ),
            description="Production FRP server configuration"
        )

        toml_content = config.generate_toml()

        assert "bindPort = 7000" in toml_content
        assert "vhostHTTPPort = 80" in toml_content
        assert "vhostHTTPSPort = 443" in toml_content
        assert 'auth.token = "ProductionSecureToken123!"' in toml_content
        assert 'subDomainHost = "tunnel.example.com"' in toml_content
        assert "[webServer]" in toml_content
        assert "port = 7500" in toml_content

        assert config.server.bind_port == 7000
        assert config.dashboard.enabled is True
        assert config.ssl.use_letsencrypt is True

    def test_minimal_config_example(self):
        """Test creating a minimal development configuration"""
        config = CompleteServerConfig(
            server=ServerConfig(
                bind_port=7000,
                auth_token="DevToken123"
            ),
            dashboard=DashboardConfig(enabled=False),
            ssl=SSLConfig(enabled=False),
            description="Development configuration"
        )

        toml_content = config.generate_toml()

        assert "bindPort = 7000" in toml_content
        assert 'auth.token = "DevToken123"' in toml_content

        assert "[webServer]" not in toml_content
