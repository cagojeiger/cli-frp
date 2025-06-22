# Checkpoint 6: Server Tools with Pydantic (TDD Approach)

## Overview
TDD와 Pydantic v2를 활용하여 FRP 서버 설정, 배포, 관리를 자동화하는 도구를 구현합니다. Pydantic 기반 설정 검증과 완전한 테스트 커버리지를 제공합니다.

## Goals
- Pydantic 기반 FRP 서버 설정 모델
- SSL/TLS 인증서 자동 관리
- 서버 배포 및 프로세스 관리
- TDD 방식의 완전한 테스트 커버리지
- Production-ready 배포 스크립트

## Test-First Implementation with Pydantic

### 1. Server Configuration Models

```python
# src/frp_wrapper/server/config.py
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from pydantic import DirectoryPath, FilePath, IPvAnyAddress

class LogLevel(str, Enum):
    """FRP server log levels"""
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"

class AuthMethod(str, Enum):
    """Authentication methods"""
    TOKEN = "token"
    OIDC = "oidc"

class ServerConfig(BaseModel):
    """Pydantic model for FRP server configuration"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    # Basic server settings
    bind_addr: str = Field(default="0.0.0.0", description="Server bind address")
    bind_port: int = Field(default=7000, ge=1, le=65535, description="Control port")
    kcp_bind_port: Optional[int] = Field(None, ge=1, le=65535, description="KCP protocol port")

    # Virtual host ports
    vhost_http_port: int = Field(default=80, ge=1, le=65535, description="HTTP virtual host port")
    vhost_https_port: int = Field(default=443, ge=1, le=65535, description="HTTPS virtual host port")

    # Authentication
    auth_method: AuthMethod = Field(default=AuthMethod.TOKEN)
    auth_token: Optional[str] = Field(None, min_length=8, description="Authentication token")

    # Domain settings
    subdomain_host: Optional[str] = Field(None, description="Subdomain host for tunnels")
    custom_404_page: Optional[str] = Field(None, description="Custom 404 page path")

    # Logging
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_max_days: int = Field(default=3, ge=1, le=365, description="Log retention days")
    log_file: Optional[str] = Field(None, description="Log file path")

    # Performance
    max_pool_count: int = Field(default=5, ge=1, le=100, description="Maximum pool count")
    max_ports_per_client: int = Field(default=0, ge=0, description="Max ports per client (0=unlimited)")
    heartbeat_timeout: int = Field(default=90, ge=30, le=300, description="Heartbeat timeout seconds")

    @field_validator('auth_token')
    @classmethod
    def validate_auth_token(cls, v: Optional[str]) -> Optional[str]:
        """Validate auth token strength"""
        if v is not None:
            if len(v) < 8:
                raise ValueError("Auth token must be at least 8 characters")
            if v.isalnum() and len(set(v)) < 4:
                raise ValueError("Auth token should contain diverse characters")
        return v

    @field_validator('subdomain_host')
    @classmethod
    def validate_subdomain_host(cls, v: Optional[str]) -> Optional[str]:
        """Validate subdomain host format"""
        if v is not None:
            if not v or '.' not in v:
                raise ValueError("Subdomain host must be a valid domain")
            # Basic domain validation
            parts = v.split('.')
            for part in parts:
                if not part or not part.replace('-', '').isalnum():
                    raise ValueError(f"Invalid domain part: {part}")
        return v

    def to_toml(self) -> str:
        """Generate FRP server TOML configuration"""
        config_lines = []

        # Basic settings
        config_lines.append(f'bindAddr = "{self.bind_addr}"')
        config_lines.append(f'bindPort = {self.bind_port}')

        if self.kcp_bind_port:
            config_lines.append(f'kcpBindPort = {self.kcp_bind_port}')

        # Virtual host settings
        config_lines.append(f'vhostHTTPPort = {self.vhost_http_port}')
        config_lines.append(f'vhostHTTPSPort = {self.vhost_https_port}')

        # Authentication
        if self.auth_token:
            config_lines.append(f'auth.method = "{self.auth_method.value}"')
            config_lines.append(f'auth.token = "{self.auth_token}"')

        # Domain settings
        if self.subdomain_host:
            config_lines.append(f'subDomainHost = "{self.subdomain_host}"')

        if self.custom_404_page:
            config_lines.append(f'custom404Page = "{self.custom_404_page}"')

        # Logging
        config_lines.append(f'log.level = "{self.log_level.value}"')
        config_lines.append(f'log.maxDays = {self.log_max_days}')

        if self.log_file:
            config_lines.append(f'log.file = "{self.log_file}"')

        # Performance
        config_lines.append(f'maxPoolCount = {self.max_pool_count}')
        if self.max_ports_per_client > 0:
            config_lines.append(f'maxPortsPerClient = {self.max_ports_per_client}')
        config_lines.append(f'heartbeatTimeout = {self.heartbeat_timeout}')

        return '\n'.join(config_lines)

class DashboardConfig(BaseModel):
    """Pydantic model for FRP dashboard configuration"""

    model_config = ConfigDict(str_strip_whitespace=True)

    enabled: bool = Field(default=False, description="Enable web dashboard")
    port: int = Field(default=7500, ge=1, le=65535, description="Dashboard port")
    user: str = Field(default="admin", min_length=3, description="Dashboard username")
    password: str = Field(..., min_length=6, description="Dashboard password")
    assets_dir: Optional[str] = Field(None, description="Custom assets directory")

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate dashboard password strength"""
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")

        # Check for basic password strength
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError("Password should contain uppercase, lowercase, and numbers")

        return v

    def to_toml_section(self) -> str:
        """Generate dashboard TOML section"""
        if not self.enabled:
            return ""

        lines = [
            "",
            "[webServer]",
            f'addr = "0.0.0.0"',
            f'port = {self.port}',
            f'user = "{self.user}"',
            f'password = "{self.password}"'
        ]

        if self.assets_dir:
            lines.append(f'assetsDir = "{self.assets_dir}"')

        return '\n'.join(lines)

class SSLConfig(BaseModel):
    """Pydantic model for SSL/TLS configuration"""

    model_config = ConfigDict(str_strip_whitespace=True)

    enabled: bool = Field(default=False, description="Enable SSL/TLS")
    cert_file: Optional[str] = Field(None, description="SSL certificate file path")
    key_file: Optional[str] = Field(None, description="SSL private key file path")
    trusted_ca_file: Optional[str] = Field(None, description="Trusted CA file path")

    # Let's Encrypt settings
    use_letsencrypt: bool = Field(default=False, description="Use Let's Encrypt certificates")
    letsencrypt_email: Optional[str] = Field(None, description="Let's Encrypt email")
    letsencrypt_domains: List[str] = Field(default_factory=list, description="Domains for Let's Encrypt")

    @field_validator('letsencrypt_email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Basic email validation"""
        if v is not None:
            if '@' not in v or '.' not in v.split('@')[-1]:
                raise ValueError("Invalid email format")
        return v

    @model_validator(mode='after')
    def validate_ssl_files(self) -> 'SSLConfig':
        """Validate SSL configuration consistency"""
        if self.enabled and not self.use_letsencrypt:
            if not self.cert_file or not self.key_file:
                raise ValueError("SSL cert_file and key_file are required when SSL is enabled")

        if self.use_letsencrypt:
            if not self.letsencrypt_email:
                raise ValueError("Let's Encrypt email is required")
            if not self.letsencrypt_domains:
                raise ValueError("At least one domain is required for Let's Encrypt")

        return self

class CompleteServerConfig(BaseModel):
    """Complete FRP server configuration with all components"""

    model_config = ConfigDict(str_strip_whitespace=True)

    server: ServerConfig = Field(default_factory=ServerConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    ssl: SSLConfig = Field(default_factory=SSLConfig)

    # Metadata
    config_version: str = Field(default="1.0.0", description="Configuration version")
    created_at: datetime = Field(default_factory=datetime.now)
    description: Optional[str] = Field(None, description="Configuration description")

    def generate_toml(self) -> str:
        """Generate complete TOML configuration file"""
        toml_content = []

        # Add header comment
        toml_content.append(f"# FRP Server Configuration")
        toml_content.append(f"# Generated at: {self.created_at.isoformat()}")
        toml_content.append(f"# Version: {self.config_version}")
        if self.description:
            toml_content.append(f"# Description: {self.description}")
        toml_content.append("")

        # Main server configuration
        toml_content.append(self.server.to_toml())

        # Dashboard configuration
        dashboard_section = self.dashboard.to_toml_section()
        if dashboard_section:
            toml_content.append(dashboard_section)

        return '\n'.join(toml_content)

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save configuration to file"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            f.write(self.generate_toml())

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> 'CompleteServerConfig':
        """Load configuration from file"""
        # This would parse TOML and create the config
        # Implementation would use tomllib/tomli for parsing
        raise NotImplementedError("TOML parsing not implemented in this example")
```

### 2. Enhanced Server Configuration Tests

```python
# tests/test_server_config.py
import pytest
import tempfile
from pathlib import Path
from pydantic import ValidationError

from frp_wrapper.server.config import (
    ServerConfig, DashboardConfig, SSLConfig, CompleteServerConfig,
    LogLevel, AuthMethod
)

class TestServerConfig:
    def test_server_config_defaults(self):
        """Test ServerConfig creation with default values"""
        config = ServerConfig()

        assert config.bind_addr == "0.0.0.0"
        assert config.bind_port == 7000
        assert config.vhost_http_port == 80
        assert config.vhost_https_port == 443
        assert config.auth_method == AuthMethod.TOKEN
        assert config.log_level == LogLevel.INFO
        assert config.max_pool_count == 5

    def test_server_config_validation_errors(self):
        """Test ServerConfig validation with invalid values"""
        # Invalid port
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            ServerConfig(bind_port=0)

        with pytest.raises(ValidationError, match="less than or equal to 65535"):
            ServerConfig(bind_port=65536)

        # Weak auth token
        with pytest.raises(ValidationError, match="at least 8 characters"):
            ServerConfig(auth_token="weak")

        # Invalid subdomain host
        with pytest.raises(ValidationError, match="valid domain"):
            ServerConfig(subdomain_host="invalid")

    def test_server_config_auth_token_validation(self):
        """Test auth token validation"""
        # Valid strong token
        config = ServerConfig(auth_token="StrongToken123!")
        assert config.auth_token == "StrongToken123!"

        # Weak token (too simple)
        with pytest.raises(ValidationError, match="diverse characters"):
            ServerConfig(auth_token="11111111")

        # Short token
        with pytest.raises(ValidationError, match="at least 8 characters"):
            ServerConfig(auth_token="short")

    def test_server_config_subdomain_validation(self):
        """Test subdomain host validation"""
        # Valid domains
        config = ServerConfig(subdomain_host="tunnel.example.com")
        assert config.subdomain_host == "tunnel.example.com"

        config = ServerConfig(subdomain_host="my-tunnel.example.org")
        assert config.subdomain_host == "my-tunnel.example.org"

        # Invalid domains
        with pytest.raises(ValidationError, match="valid domain"):
            ServerConfig(subdomain_host="invalid")

        with pytest.raises(ValidationError, match="valid domain"):
            ServerConfig(subdomain_host="")

    def test_server_config_toml_generation(self):
        """Test TOML configuration generation"""
        config = ServerConfig(
            bind_port=7001,
            vhost_http_port=8080,
            auth_token="SecureToken123",
            subdomain_host="tunnel.example.com",
            log_level=LogLevel.DEBUG
        )

        toml_content = config.to_toml()

        assert 'bindPort = 7001' in toml_content
        assert 'vhostHTTPPort = 8080' in toml_content
        assert 'auth.token = "SecureToken123"' in toml_content
        assert 'subDomainHost = "tunnel.example.com"' in toml_content
        assert 'log.level = "debug"' in toml_content

class TestDashboardConfig:
    def test_dashboard_config_creation(self):
        """Test DashboardConfig creation"""
        config = DashboardConfig(
            enabled=True,
            port=7500,
            user="admin",
            password="SecurePass123"
        )

        assert config.enabled is True
        assert config.port == 7500
        assert config.user == "admin"
        assert config.password == "SecurePass123"

    def test_dashboard_password_validation(self):
        """Test dashboard password validation"""
        # Valid strong password
        config = DashboardConfig(
            enabled=True,
            password="StrongPass123"
        )
        assert config.password == "StrongPass123"

        # Too short
        with pytest.raises(ValidationError, match="at least 6 characters"):
            DashboardConfig(enabled=True, password="short")

        # Too weak (no variety)
        with pytest.raises(ValidationError, match="uppercase, lowercase, and numbers"):
            DashboardConfig(enabled=True, password="alllowercase")

    def test_dashboard_toml_generation(self):
        """Test dashboard TOML section generation"""
        # Enabled dashboard
        config = DashboardConfig(
            enabled=True,
            port=7500,
            user="admin",
            password="SecurePass123"
        )

        toml_section = config.to_toml_section()

        assert "[webServer]" in toml_section
        assert 'port = 7500' in toml_section
        assert 'user = "admin"' in toml_section
        assert 'password = "SecurePass123"' in toml_section

        # Disabled dashboard
        config = DashboardConfig(enabled=False)
        toml_section = config.to_toml_section()
        assert toml_section == ""

class TestSSLConfig:
    def test_ssl_config_creation(self):
        """Test SSLConfig creation"""
        config = SSLConfig(
            enabled=True,
            cert_file="/etc/ssl/cert.pem",
            key_file="/etc/ssl/key.pem"
        )

        assert config.enabled is True
        assert config.cert_file == "/etc/ssl/cert.pem"
        assert config.key_file == "/etc/ssl/key.pem"

    def test_ssl_config_validation_errors(self):
        """Test SSL configuration validation"""
        # SSL enabled but missing files
        with pytest.raises(ValidationError, match="cert_file and key_file are required"):
            SSLConfig(enabled=True)

        # Let's Encrypt without email
        with pytest.raises(ValidationError, match="email is required"):
            SSLConfig(
                enabled=True,
                use_letsencrypt=True,
                letsencrypt_domains=["example.com"]
            )

        # Let's Encrypt without domains
        with pytest.raises(ValidationError, match="At least one domain is required"):
            SSLConfig(
                enabled=True,
                use_letsencrypt=True,
                letsencrypt_email="admin@example.com"
            )

    def test_ssl_letsencrypt_config(self):
        """Test Let's Encrypt SSL configuration"""
        config = SSLConfig(
            enabled=True,
            use_letsencrypt=True,
            letsencrypt_email="admin@example.com",
            letsencrypt_domains=["tunnel.example.com", "api.example.com"]
        )

        assert config.use_letsencrypt is True
        assert config.letsencrypt_email == "admin@example.com"
        assert len(config.letsencrypt_domains) == 2

    def test_ssl_email_validation(self):
        """Test email validation"""
        # Valid email
        config = SSLConfig(letsencrypt_email="admin@example.com")
        assert config.letsencrypt_email == "admin@example.com"

        # Invalid emails
        with pytest.raises(ValidationError, match="Invalid email format"):
            SSLConfig(letsencrypt_email="invalid-email")

        with pytest.raises(ValidationError, match="Invalid email format"):
            SSLConfig(letsencrypt_email="admin@invalid")

class TestCompleteServerConfig:
    def test_complete_config_creation(self):
        """Test CompleteServerConfig creation"""
        config = CompleteServerConfig(
            server=ServerConfig(
                bind_port=7001,
                auth_token="SecureToken123"
            ),
            dashboard=DashboardConfig(
                enabled=True,
                password="AdminPass123"
            ),
            ssl=SSLConfig(
                enabled=True,
                cert_file="/etc/ssl/cert.pem",
                key_file="/etc/ssl/key.pem"
            ),
            description="Test server configuration"
        )

        assert config.server.bind_port == 7001
        assert config.dashboard.enabled is True
        assert config.ssl.enabled is True
        assert config.description == "Test server configuration"

    def test_complete_config_toml_generation(self):
        """Test complete TOML generation"""
        config = CompleteServerConfig(
            server=ServerConfig(
                bind_port=7001,
                auth_token="SecureToken123",
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

        # Check header
        assert "# FRP Server Configuration" in toml_content
        assert "# Description: Production server" in toml_content

        # Check server config
        assert "bindPort = 7001" in toml_content
        assert 'auth.token = "SecureToken123"' in toml_content

        # Check dashboard config
        assert "[webServer]" in toml_content
        assert "port = 7500" in toml_content

    def test_config_file_operations(self):
        """Test saving and loading configuration files"""
        config = CompleteServerConfig(
            server=ServerConfig(
                bind_port=7001,
                auth_token="SecureToken123"
            ),
            dashboard=DashboardConfig(
                enabled=True,
                password="AdminPass123"
            ),
            description="Test config file operations"
        )

        # Test saving
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            temp_path = Path(f.name)

        try:
            config.save_to_file(temp_path)

            # Verify file was created and contains expected content
            assert temp_path.exists()
            content = temp_path.read_text()
            assert "bindPort = 7001" in content
            assert "[webServer]" in content

        finally:
            temp_path.unlink(missing_ok=True)

# Integration tests
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

        # Generate and validate TOML
        toml_content = config.generate_toml()

        # Verify all required sections are present
        assert "bindPort = 7000" in toml_content
        assert "vhostHTTPPort = 80" in toml_content
        assert "vhostHTTPSPort = 443" in toml_content
        assert 'auth.token = "ProductionSecureToken123!"' in toml_content
        assert 'subDomainHost = "tunnel.example.com"' in toml_content
        assert "[webServer]" in toml_content
        assert "port = 7500" in toml_content

        # Verify configuration is valid
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

        # Should have basic server config only
        assert "bindPort = 7000" in toml_content
        assert 'auth.token = "DevToken123"' in toml_content

        # Should not have dashboard or SSL
        assert "[webServer]" not in toml_content

    def test_config_validation_comprehensive(self):
        """Comprehensive validation test"""
        # Test all validation scenarios work together

        # Valid comprehensive config
        config = CompleteServerConfig(
            server=ServerConfig(
                bind_port=7000,
                vhost_http_port=80,
                vhost_https_port=443,
                auth_token="ComprehensiveToken123!",
                subdomain_host="tunnel.example.com",
                log_level=LogLevel.DEBUG,
                max_pool_count=10,
                heartbeat_timeout=120
            ),
            dashboard=DashboardConfig(
                enabled=True,
                port=7500,
                user="admin",
                password="ComprehensiveDashPass123!"
            ),
            ssl=SSLConfig(
                enabled=True,
                use_letsencrypt=True,
                letsencrypt_email="admin@example.com",
                letsencrypt_domains=["tunnel.example.com", "api.example.com"]
            )
        )

        # Should validate successfully
        assert config.server.auth_token == "ComprehensiveToken123!"
        assert config.dashboard.password == "ComprehensiveDashPass123!"
        assert len(config.ssl.letsencrypt_domains) == 2

        # Generate TOML and verify structure
        toml_content = config.generate_toml()
        lines = toml_content.split('\n')

        # Should have proper structure
        assert any('bindPort = 7000' in line for line in lines)
        assert any('[webServer]' in line for line in lines)
        assert any('log.level = "debug"' in line for line in lines)
```

### 3. Server Management Implementation

```python
# src/frp_wrapper/server/manager.py
import logging
import subprocess
import time
import signal
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict

from .config import CompleteServerConfig

logger = logging.getLogger(__name__)

class ServerStatus(BaseModel):
    """Pydantic model for server status"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    running: bool = Field(..., description="Whether server is running")
    pid: Optional[int] = Field(None, description="Process ID")
    start_time: Optional[str] = Field(None, description="Start time")
    config_file: str = Field(..., description="Configuration file path")
    version: Optional[str] = Field(None, description="FRP server version")
    listening_ports: List[int] = Field(default_factory=list, description="Active listening ports")
    error_message: Optional[str] = Field(None, description="Error message if any")

class ServerManager:
    """TDD-driven FRP server management"""

    def __init__(self, binary_path: str = "/usr/local/bin/frps"):
        self.binary_path = binary_path
        self._validate_binary()

    def _validate_binary(self) -> None:
        """Validate FRP server binary exists and is executable"""
        binary = Path(self.binary_path)
        if not binary.exists():
            raise FileNotFoundError(f"FRP server binary not found: {self.binary_path}")
        if not binary.is_file():
            raise ValueError(f"FRP server binary is not a file: {self.binary_path}")
        if not binary.stat().st_mode & 0o111:
            raise PermissionError(f"FRP server binary is not executable: {self.binary_path}")

    def start_server(self, config: CompleteServerConfig, config_file: str) -> int:
        """Start FRP server with given configuration"""
        # Save configuration to file
        config.save_to_file(config_file)

        # Start server process
        try:
            cmd = [self.binary_path, "-c", config_file]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )

            # Wait a moment to ensure it started successfully
            time.sleep(2)

            if process.poll() is not None:
                # Process died immediately
                stdout, stderr = process.communicate()
                raise RuntimeError(f"Server failed to start: {stderr.decode()}")

            logger.info(f"FRP server started with PID {process.pid}")
            return process.pid

        except Exception as e:
            logger.error(f"Failed to start FRP server: {e}")
            raise

    def stop_server(self, pid: int, timeout: int = 10) -> bool:
        """Stop FRP server gracefully"""
        try:
            # Send SIGTERM for graceful shutdown
            process = subprocess.Popen(['kill', '-TERM', str(pid)])
            process.wait()

            # Wait for process to terminate
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # Check if process still exists
                    subprocess.check_output(['kill', '-0', str(pid)], stderr=subprocess.DEVNULL)
                    time.sleep(0.5)
                except subprocess.CalledProcessError:
                    # Process no longer exists
                    logger.info(f"FRP server (PID {pid}) stopped gracefully")
                    return True

            # Force kill if still running
            logger.warning(f"Force killing FRP server (PID {pid})")
            subprocess.run(['kill', '-KILL', str(pid)])
            return True

        except Exception as e:
            logger.error(f"Failed to stop FRP server: {e}")
            return False

    def get_server_status(self, config_file: str) -> ServerStatus:
        """Get current server status"""
        try:
            # Try to find FRP server process
            result = subprocess.run(
                ['pgrep', '-f', f'frps.*{config_file}'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0 and result.stdout.strip():
                pid = int(result.stdout.strip().split('\n')[0])

                # Get process start time
                ps_result = subprocess.run(
                    ['ps', '-o', 'lstart=', '-p', str(pid)],
                    capture_output=True,
                    text=True
                )
                start_time = ps_result.stdout.strip() if ps_result.returncode == 0 else None

                # Get listening ports
                listening_ports = self._get_listening_ports(pid)

                return ServerStatus(
                    running=True,
                    pid=pid,
                    start_time=start_time,
                    config_file=config_file,
                    listening_ports=listening_ports
                )
            else:
                return ServerStatus(
                    running=False,
                    config_file=config_file
                )

        except Exception as e:
            return ServerStatus(
                running=False,
                config_file=config_file,
                error_message=str(e)
            )

    def _get_listening_ports(self, pid: int) -> List[int]:
        """Get ports that the server process is listening on"""
        try:
            result = subprocess.run(
                ['netstat', '-tlnp'],
                capture_output=True,
                text=True
            )

            ports = []
            for line in result.stdout.split('\n'):
                if str(pid) in line and 'LISTEN' in line:
                    # Extract port from address like "0.0.0.0:7000"
                    parts = line.split()
                    if len(parts) >= 4:
                        addr_port = parts[3]
                        if ':' in addr_port:
                            port = addr_port.split(':')[-1]
                            try:
                                ports.append(int(port))
                            except ValueError:
                                pass

            return sorted(list(set(ports)))

        except Exception:
            return []

    def reload_config(self, pid: int, new_config: CompleteServerConfig, config_file: str) -> bool:
        """Reload server configuration"""
        try:
            # Save new configuration
            new_config.save_to_file(config_file)

            # Send SIGHUP to reload
            subprocess.run(['kill', '-HUP', str(pid)], check=True)

            logger.info(f"Reloaded configuration for FRP server (PID {pid})")
            return True

        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            return False

    def get_server_version(self) -> Optional[str]:
        """Get FRP server version"""
        try:
            result = subprocess.run(
                [self.binary_path, '--version'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Parse version from output
                for line in result.stdout.split('\n'):
                    if 'frp version' in line:
                        return line.split()[-1]

            return None

        except Exception:
            return None
```

## Implementation Timeline (TDD + Pydantic)

### Day 1: Server Configuration Models
1. **Write configuration tests**: ServerConfig, DashboardConfig, SSLConfig validation
2. **Implement Pydantic models**: Configuration classes with comprehensive validation
3. **Write TOML generation tests**: Configuration export functionality
4. **Implement TOML generation**: Native FRP server configuration format

### Day 2: Server Management
1. **Write server manager tests**: Start, stop, status operations
2. **Implement ServerManager**: Process management with proper error handling
3. **Write status monitoring tests**: Process monitoring and port detection
4. **Implement monitoring**: Real-time server status and health checks

### Day 3: Integration & Tools
1. **Write integration tests**: End-to-end server management scenarios
2. **SSL/TLS management**: Certificate handling and Let's Encrypt integration
3. **Deployment scripts**: Automated installation and setup
4. **Production testing**: Real FRP server deployment scenarios

## File Structure
```
src/frp_wrapper/
├── __init__.py
├── server/
│   ├── __init__.py
│   ├── config.py          # Pydantic configuration models
│   ├── manager.py         # Server management
│   ├── ssl.py             # SSL/TLS management
│   └── installer.py       # Installation utilities

scripts/
├── install-frp-server.sh  # Server installation script
├── setup-ssl.sh          # SSL setup script
└── frps.toml.template     # Configuration template

tests/
├── __init__.py
├── test_server_config.py   # Configuration model tests
├── test_server_manager.py  # Server management tests
├── test_ssl_manager.py     # SSL management tests
└── test_server_integration.py  # Integration tests
```

## Success Criteria
- [ ] 100% test coverage for all server tools
- [ ] All Pydantic validation scenarios tested
- [ ] Production-ready configuration generation
- [ ] Robust server process management
- [ ] SSL/TLS certificate automation
- [ ] Complete deployment automation
- [ ] Real FRP server integration tested

## Key Pydantic Benefits for Server Tools
1. **Configuration Validation**: Comprehensive server settings validation
2. **Type Safety**: Full IDE support for server configurations
3. **TOML Generation**: Native FRP server configuration format
4. **Documentation**: Self-documenting configuration options
5. **Error Messages**: Clear validation error messages for admins
6. **Versioning**: Configuration schema versioning and migration

This approach provides production-ready server management tools with comprehensive validation, excellent developer experience, and robust error handling suitable for enterprise deployments.
