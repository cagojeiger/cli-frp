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
            max_pool_count=10,
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

    def test_auth_token_length_validation_exact(self):
        """Test exact auth token length validation (line 70)"""
        with pytest.raises(
            ValidationError, match="String should have at least 8 characters"
        ):
            ServerConfig(auth_token="1234567")  # Exactly 7 characters

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

    def test_subdomain_host_invalid_domain_part(self):
        """Test subdomain host validation with invalid domain part (line 85)"""
        with pytest.raises(ValidationError, match="Invalid domain part"):
            ServerConfig(
                subdomain_host="invalid..domain.com"
            )  # Empty part between dots

    def test_toml_generation(self):
        """Test TOML configuration generation"""
        config = ServerConfig(
            bind_port=7001,
            auth_token="SecureToken123!",
            subdomain_host="tunnel.example.com",
            log_level=LogLevel.DEBUG,
        )

        toml_content = config.to_toml()

        assert "bindPort = 7001" in toml_content
        assert 'auth.token = "SecureToken123!"' in toml_content
        assert 'subDomainHost = "tunnel.example.com"' in toml_content
        assert 'log.level = "debug"' in toml_content

    def test_toml_generation_with_optional_fields(self):
        """Test TOML generation with optional fields to cover missing lines"""
        config = ServerConfig(
            bind_port=7000,
            kcp_bind_port=7001,  # Line 96
            custom_404_page="/custom/404.html",  # Line 108
        )

        toml_content = config.to_toml()
        assert "kcpBindPort = 7001" in toml_content
        assert 'custom404Page = "/custom/404.html"' in toml_content


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
            password="SecureDashPass123!",
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

    def test_dashboard_password_length_validation_exact(self):
        """Test exact dashboard password length validation (line 146)"""
        with pytest.raises(
            ValidationError, match="String should have at least 8 characters"
        ):
            DashboardConfig(enabled=True, password="1234567")  # Exactly 7 characters

    def test_dashboard_port_validation(self):
        """Test dashboard port validation"""
        config = DashboardConfig(port=8080)
        assert config.port == 8080

        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            DashboardConfig(port=0)

        with pytest.raises(ValidationError, match="less than or equal to 65535"):
            DashboardConfig(port=70000)

    def test_dashboard_toml_generation_disabled(self):
        """Test dashboard TOML generation when disabled (line 152)"""
        config = DashboardConfig(enabled=False)
        toml_content = config.to_toml()
        assert toml_content == ""

    def test_dashboard_toml_generation_with_assets(self):
        """Test dashboard TOML generation with assets directory (line 162)"""
        config = DashboardConfig(
            enabled=True,
            port=7500,
            user="admin",
            password="AdminPass123",
            assets_dir="/custom/assets",
        )

        toml_content = config.to_toml()
        assert 'assetsDir = "/custom/assets"' in toml_content


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
            enabled=True, cert_file="/path/to/cert.pem", key_file="/path/to/key.pem"
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
            letsencrypt_domains=["tunnel.example.com", "api.example.com"],
        )

        assert config.enabled is True
        assert config.use_letsencrypt is True
        assert config.letsencrypt_email == "admin@example.com"
        assert len(config.letsencrypt_domains) == 2

    def test_ssl_config_validation(self):
        """Test SSL configuration validation"""
        with pytest.raises(
            ValidationError,
            match="Cannot use both manual certificates and Let's Encrypt",
        ):
            SSLConfig(
                enabled=True,
                cert_file="/path/to/cert.pem",
                key_file="/path/to/key.pem",
                use_letsencrypt=True,
                letsencrypt_email="admin@example.com",
            )

        with pytest.raises(ValidationError, match="Let's Encrypt email is required"):
            SSLConfig(enabled=True, use_letsencrypt=True)

        with pytest.raises(
            ValidationError, match="Both cert_file and key_file are required"
        ):
            SSLConfig(enabled=True, cert_file="/path/to/cert.pem")

    def test_ssl_config_letsencrypt_domains_validation(self):
        """Test SSL Let's Encrypt domains validation (line 209)"""
        with pytest.raises(ValidationError, match="At least one domain is required"):
            SSLConfig(
                enabled=True,
                use_letsencrypt=True,
                letsencrypt_email="admin@example.com",
                letsencrypt_domains=[],  # Empty domains list
            )

    def test_ssl_toml_generation_disabled(self):
        """Test SSL TOML generation when disabled (line 216)"""
        config = SSLConfig(enabled=False)
        toml_content = config.to_toml()
        assert toml_content == ""


class TestCompleteServerConfig:
    """Test CompleteServerConfig integration model"""

    def test_complete_config_creation(self):
        """Test creating complete server configuration"""
        config = CompleteServerConfig(
            server=ServerConfig(
                bind_port=7001,
                auth_token="SecureToken123!",
                subdomain_host="tunnel.example.com",
            ),
            dashboard=DashboardConfig(enabled=True, password="DashPass123!"),
            ssl=SSLConfig(
                enabled=True,
                use_letsencrypt=True,
                letsencrypt_email="admin@example.com",
                letsencrypt_domains=["tunnel.example.com"],
            ),
            description="Test server configuration",
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
                subdomain_host="tunnel.example.com",
            ),
            dashboard=DashboardConfig(enabled=True, port=7500, password="AdminPass123"),
            description="Production server",
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
            server=ServerConfig(bind_port=7001, auth_token="SecureToken123!"),
            dashboard=DashboardConfig(enabled=True, password="AdminPass123"),
            description="Test config file operations",
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            temp_path = Path(f.name)

        try:
            config.save_to_file(temp_path)

            assert temp_path.exists()
            content = temp_path.read_text()
            assert "bindPort = 7001" in content
            assert "[webServer]" in content

        finally:
            temp_path.unlink(missing_ok=True)

    def test_load_from_file_success(self):
        """Test successful configuration loading from TOML file."""
        toml_content = """
bindPort = 7000
bindAddr = "127.0.0.1"
vhostHTTPPort = 8080
vhostHTTPSPort = 8443
subDomainHost = "example.com"
maxPoolCount = 10
maxPortsPerClient = 5
tlsCertFile = "/path/to/cert.pem"
tlsKeyFile = "/path/to/key.pem"

[auth]
token = "TestToken123"

[webServer]
port = 7500
user = "admin"
password = "AdminPass123"
assetsDir = "/custom/assets"

[log]
level = "debug"
maxDays = 7
to = "/var/log/frps.log"

[transport]
heartbeatTimeout = 120
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            config = CompleteServerConfig.load_from_file(temp_path)

            assert config is not None
            assert f"Loaded from {temp_path.name}" in config.description

            assert config.server.bind_addr == "127.0.0.1"
            assert config.server.bind_port == 7000
            assert config.server.vhost_http_port == 8080
            assert config.server.vhost_https_port == 8443
            assert config.server.auth_token == "TestToken123"
            assert config.server.subdomain_host == "example.com"
            assert config.server.max_pool_count == 10
            assert config.server.max_ports_per_client == 5
            assert config.server.log_level == LogLevel.DEBUG
            assert config.server.log_max_days == 7
            assert config.server.log_file == "/var/log/frps.log"
            assert config.server.heartbeat_timeout == 120

            assert config.dashboard.enabled is True
            assert config.dashboard.port == 7500
            assert config.dashboard.user == "admin"
            assert config.dashboard.password == "AdminPass123"
            assert config.dashboard.assets_dir == "/custom/assets"

            assert config.ssl.enabled is True
            assert config.ssl.cert_file == "/path/to/cert.pem"
            assert config.ssl.key_file == "/path/to/key.pem"

        finally:
            temp_path.unlink(missing_ok=True)

    def test_load_from_file_minimal_config(self):
        """Test loading minimal TOML configuration."""
        toml_content = """
bindPort = 9000
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            config = CompleteServerConfig.load_from_file(temp_path)

            assert config.server.bind_port == 9000
            assert config.server.bind_addr == "0.0.0.0"  # Default
            assert config.server.vhost_http_port == 80  # Default
            assert config.server.auth_token is None  # Not specified
            assert config.dashboard.enabled is False  # No webServer section
            assert config.ssl.enabled is False  # No SSL config

        finally:
            temp_path.unlink(missing_ok=True)

    def test_load_from_file_dashboard_only(self):
        """Test loading configuration with only dashboard section."""
        toml_content = """
bindPort = 7000

[webServer]
port = 8080
user = "testuser"
password = "testpass"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            config = CompleteServerConfig.load_from_file(temp_path)

            assert config.server.bind_port == 7000
            assert config.dashboard.enabled is True
            assert config.dashboard.port == 8080
            assert config.dashboard.user == "testuser"
            assert config.dashboard.password == "testpass"
            assert config.ssl.enabled is False

        finally:
            temp_path.unlink(missing_ok=True)

    def test_load_from_file_ssl_only(self):
        """Test loading configuration with only SSL certificates."""
        toml_content = """
bindPort = 7000
tlsCertFile = "/ssl/cert.pem"
tlsKeyFile = "/ssl/key.pem"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            config = CompleteServerConfig.load_from_file(temp_path)

            assert config.server.bind_port == 7000
            assert config.dashboard.enabled is False
            assert config.ssl.enabled is True
            assert config.ssl.cert_file == "/ssl/cert.pem"
            assert config.ssl.key_file == "/ssl/key.pem"

        finally:
            temp_path.unlink(missing_ok=True)

    def test_load_from_file_not_found(self):
        """Test loading from non-existent file."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            CompleteServerConfig.load_from_file("/nonexistent/file.toml")

    def test_load_from_file_invalid_toml(self):
        """Test loading from invalid TOML file."""
        invalid_toml = """
bindPort = 7000
[invalid section without closing bracket
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(invalid_toml)
            temp_path = Path(f.name)

        try:
            with pytest.raises(
                (ValueError, TypeError)
            ):  # tomllib will raise various parsing errors
                CompleteServerConfig.load_from_file(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_load_from_file_nested_config_sections(self):
        """Test loading configuration with nested sections."""
        toml_content = """
bindPort = 7000

[auth]
token = "NestedToken123"

[log]
level = "warn"
maxDays = 14
to = "/custom/log/path.log"

[transport]
heartbeatTimeout = 180
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            config = CompleteServerConfig.load_from_file(temp_path)

            assert config.server.auth_token == "NestedToken123"
            assert config.server.log_level == LogLevel.WARN
            assert config.server.log_max_days == 14
            assert config.server.log_file == "/custom/log/path.log"
            assert config.server.heartbeat_timeout == 180

        finally:
            temp_path.unlink(missing_ok=True)

    def test_load_from_file_string_path(self):
        """Test loading from file using string path instead of Path object."""
        toml_content = """
bindPort = 8000
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path_str = f.name

        try:
            config = CompleteServerConfig.load_from_file(temp_path_str)
            assert config.server.bind_port == 8000
        finally:
            Path(temp_path_str).unlink(missing_ok=True)

    def test_load_save_roundtrip(self):
        """Test that loading and saving configuration preserves data."""
        original_config = CompleteServerConfig(
            server=ServerConfig(
                bind_port=7000,
                auth_token="RoundtripTest123",
                subdomain_host="test.example.com",
                log_level=LogLevel.DEBUG,
            ),
            dashboard=DashboardConfig(enabled=True, port=7500, password="DashPass123"),
            ssl=SSLConfig(
                enabled=True, cert_file="/test/cert.pem", key_file="/test/key.pem"
            ),
            description="Roundtrip test",
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            temp_path = Path(f.name)

        try:
            original_config.save_to_file(temp_path)

            loaded_config = CompleteServerConfig.load_from_file(temp_path)

            assert loaded_config.server.bind_port == 7000
            assert loaded_config.server.auth_token == "RoundtripTest123"
            assert loaded_config.server.subdomain_host == "test.example.com"
            assert loaded_config.server.log_level == LogLevel.DEBUG
            assert loaded_config.dashboard.enabled is True
            assert loaded_config.dashboard.port == 7500
            assert loaded_config.ssl.enabled is True
            assert loaded_config.ssl.cert_file == "/test/cert.pem"

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
                heartbeat_timeout=90,
            ),
            dashboard=DashboardConfig(
                enabled=True,
                port=7500,
                user="admin",
                password="SecureDashboardPass123!",
            ),
            ssl=SSLConfig(
                enabled=True,
                use_letsencrypt=True,
                letsencrypt_email="admin@example.com",
                letsencrypt_domains=["tunnel.example.com"],
            ),
            description="Production FRP server configuration",
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
            server=ServerConfig(bind_port=7000, auth_token="DevToken123"),
            dashboard=DashboardConfig(enabled=False),
            ssl=SSLConfig(enabled=False),
            description="Development configuration",
        )

        toml_content = config.generate_toml()

        assert "bindPort = 7000" in toml_content
        assert 'auth.token = "DevToken123"' in toml_content

        assert "[webServer]" not in toml_content
