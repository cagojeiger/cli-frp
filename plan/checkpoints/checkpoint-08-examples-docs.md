# Checkpoint 8: Examples & Documentation with Pydantic (TDD Approach)

## Overview
TDD와 Pydantic v2를 활용한 완전한 예제 코드와 문서를 작성합니다. 실용적인 사용 사례와 프로덕션 품질의 문서를 제공하여 사용자가 쉽게 시작할 수 있도록 합니다.

## Goals
- Pydantic 기반 설정 모델을 활용한 실용적 예제
- 완전한 API 문서 및 사용자 가이드
- TDD 방식으로 검증된 예제 코드
- 프로덕션 배포를 위한 종합 가이드
- 패키지 배포 준비

## Test-First Implementation with Pydantic

### 1. Pydantic Configuration Models for Examples

```python
# examples/config/models.py
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic import HttpUrl, FilePath

class ExampleEnvironment(str, Enum):
    """Example environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class TunnelType(str, Enum):
    """Tunnel types for examples"""
    HTTP = "http"
    TCP = "tcp"
    WEBSOCKET = "websocket"

class ExampleTunnelConfig(BaseModel):
    """Pydantic model for example tunnel configuration"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    name: str = Field(..., min_length=1, max_length=50, description="Tunnel name")
    type: TunnelType = Field(..., description="Tunnel type")
    local_port: int = Field(..., ge=1, le=65535, description="Local port")
    path: Optional[str] = Field(None, description="HTTP path for routing")
    remote_port: Optional[int] = Field(None, ge=1, le=65535, description="Remote TCP port")

    # HTTP specific options
    websocket_support: bool = Field(default=True, description="Enable WebSocket support")
    strip_path: bool = Field(default=True, description="Strip path from requests")
    custom_headers: Dict[str, str] = Field(default_factory=dict, description="Custom headers")

    # Security options
    basic_auth: Optional[str] = Field(None, description="Basic authentication (user:pass)")
    allowed_origins: List[str] = Field(default_factory=list, description="CORS allowed origins")

    @field_validator('path')
    @classmethod
    def validate_path_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate HTTP path format"""
        if v is not None:
            if v.startswith('/'):
                raise ValueError("Path should not start with '/'")
            if not v.replace('-', '').replace('_', '').replace('/', '').isalnum():
                raise ValueError("Path contains invalid characters")
        return v

    @field_validator('basic_auth')
    @classmethod
    def validate_basic_auth_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate basic auth format"""
        if v is not None and ':' not in v:
            raise ValueError("Basic auth must be in format 'username:password'")
        return v

class ExampleConfig(BaseModel):
    """Complete configuration for examples"""

    model_config = ConfigDict(str_strip_whitespace=True)

    # Environment settings
    environment: ExampleEnvironment = Field(default=ExampleEnvironment.DEVELOPMENT)
    project_name: str = Field(..., min_length=1, description="Project name")
    description: Optional[str] = Field(None, description="Project description")

    # Server settings
    server_host: str = Field(..., description="FRP server host")
    server_port: int = Field(default=7000, ge=1, le=65535, description="FRP server port")
    auth_token: Optional[str] = Field(None, min_length=8, description="Authentication token")

    # Tunnels configuration
    tunnels: List[ExampleTunnelConfig] = Field(..., min_items=1, description="Tunnel configurations")

    # Monitoring settings
    enable_monitoring: bool = Field(default=True, description="Enable monitoring")
    monitoring_port: int = Field(default=9999, ge=1, le=65535, description="Monitoring dashboard port")
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # Runtime settings
    auto_reconnect: bool = Field(default=True, description="Enable auto-reconnection")
    reconnect_interval: int = Field(default=30, ge=5, le=300, description="Reconnect interval in seconds")

    @field_validator('tunnels')
    @classmethod
    def validate_tunnel_names_unique(cls, v: List[ExampleTunnelConfig]) -> List[ExampleTunnelConfig]:
        """Ensure tunnel names are unique"""
        names = [tunnel.name for tunnel in v]
        if len(names) != len(set(names)):
            raise ValueError("Tunnel names must be unique")
        return v

    @field_validator('tunnels')
    @classmethod
    def validate_ports_unique(cls, v: List[ExampleTunnelConfig]) -> List[ExampleTunnelConfig]:
        """Ensure local ports are unique"""
        ports = [tunnel.local_port for tunnel in v]
        if len(ports) != len(set(ports)):
            raise ValueError("Local ports must be unique")
        return v

    def get_tunnel_by_name(self, name: str) -> Optional[ExampleTunnelConfig]:
        """Get tunnel configuration by name"""
        for tunnel in self.tunnels:
            if tunnel.name == name:
                return tunnel
        return None

    def get_http_tunnels(self) -> List[ExampleTunnelConfig]:
        """Get all HTTP tunnel configurations"""
        return [t for t in self.tunnels if t.type == TunnelType.HTTP]

    def get_tcp_tunnels(self) -> List[ExampleTunnelConfig]:
        """Get all TCP tunnel configurations"""
        return [t for t in self.tunnels if t.type == TunnelType.TCP]

class ExampleMetadata(BaseModel):
    """Metadata for example files"""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., min_length=1, description="Example title")
    description: str = Field(..., min_length=10, description="Detailed description")
    difficulty: str = Field(..., pattern="^(beginner|intermediate|advanced)$", description="Difficulty level")
    tags: List[str] = Field(..., min_items=1, description="Example tags")
    requirements: List[str] = Field(default_factory=list, description="Required dependencies")
    estimated_time: int = Field(..., ge=1, le=60, description="Estimated completion time in minutes")

    # Tutorial metadata
    tutorial_steps: List[str] = Field(default_factory=list, description="Tutorial step descriptions")
    troubleshooting: Dict[str, str] = Field(default_factory=dict, description="Common issues and solutions")

    # Links and references
    related_docs: List[str] = Field(default_factory=list, description="Related documentation links")
    external_links: List[HttpUrl] = Field(default_factory=list, description="External reference links")

class DocumentationConfig(BaseModel):
    """Configuration for documentation generation"""

    model_config = ConfigDict(str_strip_whitespace=True)

    # Documentation settings
    project_name: str = Field(..., description="Project name for documentation")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+", description="Project version")
    author: str = Field(..., description="Project author")
    description: str = Field(..., description="Project description")

    # Output settings
    output_dir: str = Field(default="docs", description="Documentation output directory")
    api_docs_dir: str = Field(default="api", description="API documentation subdirectory")
    examples_docs_dir: str = Field(default="examples", description="Examples documentation subdirectory")

    # Content settings
    include_api_reference: bool = Field(default=True, description="Include API reference")
    include_examples: bool = Field(default=True, description="Include examples documentation")
    include_tutorials: bool = Field(default=True, description="Include tutorials")

    # Generation settings
    auto_generate: bool = Field(default=True, description="Auto-generate from docstrings")
    validate_links: bool = Field(default=True, description="Validate external links")
    generate_toc: bool = Field(default=True, description="Generate table of contents")
```

### 2. Example Test Framework

```python
# tests/test_examples.py
import pytest
import tempfile
import subprocess
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import Mock, patch

from examples.config.models import (
    ExampleConfig, ExampleTunnelConfig, ExampleMetadata, TunnelType,
    ExampleEnvironment, DocumentationConfig
)
from frp_wrapper.client import FRPClient

class TestExampleConfigurations:
    def test_example_tunnel_config_validation(self):
        """Test ExampleTunnelConfig validation"""
        # Valid HTTP tunnel
        http_tunnel = ExampleTunnelConfig(
            name="web-app",
            type=TunnelType.HTTP,
            local_port=3000,
            path="myapp",
            websocket_support=True,
            custom_headers={"X-App": "MyApp"}
        )

        assert http_tunnel.name == "web-app"
        assert http_tunnel.type == TunnelType.HTTP
        assert http_tunnel.path == "myapp"
        assert http_tunnel.websocket_support is True

        # Valid TCP tunnel
        tcp_tunnel = ExampleTunnelConfig(
            name="ssh-tunnel",
            type=TunnelType.TCP,
            local_port=22,
            remote_port=2222
        )

        assert tcp_tunnel.name == "ssh-tunnel"
        assert tcp_tunnel.type == TunnelType.TCP
        assert tcp_tunnel.remote_port == 2222

    def test_example_tunnel_config_validation_errors(self):
        """Test ExampleTunnelConfig validation errors"""
        # Invalid path format
        with pytest.raises(ValueError, match="should not start with"):
            ExampleTunnelConfig(
                name="test",
                type=TunnelType.HTTP,
                local_port=3000,
                path="/invalid-path"
            )

        # Invalid basic auth format
        with pytest.raises(ValueError, match="username:password"):
            ExampleTunnelConfig(
                name="test",
                type=TunnelType.HTTP,
                local_port=3000,
                basic_auth="invalid_format"
            )

        # Invalid port range
        with pytest.raises(ValueError):
            ExampleTunnelConfig(
                name="test",
                type=TunnelType.TCP,
                local_port=70000  # Invalid port
            )

class TestExampleConfig:
    def test_example_config_creation(self):
        """Test ExampleConfig creation with multiple tunnels"""
        tunnels = [
            ExampleTunnelConfig(
                name="frontend",
                type=TunnelType.HTTP,
                local_port=3000,
                path="app"
            ),
            ExampleTunnelConfig(
                name="api",
                type=TunnelType.HTTP,
                local_port=8000,
                path="api",
                strip_path=False
            ),
            ExampleTunnelConfig(
                name="ssh",
                type=TunnelType.TCP,
                local_port=22,
                remote_port=2222
            )
        ]

        config = ExampleConfig(
            project_name="multi-service-example",
            server_host="tunnel.example.com",
            auth_token="example_token_123",
            tunnels=tunnels,
            environment=ExampleEnvironment.DEVELOPMENT
        )

        assert config.project_name == "multi-service-example"
        assert len(config.tunnels) == 3
        assert config.environment == ExampleEnvironment.DEVELOPMENT

    def test_example_config_validation_errors(self):
        """Test ExampleConfig validation errors"""
        # Duplicate tunnel names
        with pytest.raises(ValueError, match="names must be unique"):
            ExampleConfig(
                project_name="test",
                server_host="example.com",
                tunnels=[
                    ExampleTunnelConfig(name="app", type=TunnelType.HTTP, local_port=3000),
                    ExampleTunnelConfig(name="app", type=TunnelType.HTTP, local_port=3001)
                ]
            )

        # Duplicate ports
        with pytest.raises(ValueError, match="ports must be unique"):
            ExampleConfig(
                project_name="test",
                server_host="example.com",
                tunnels=[
                    ExampleTunnelConfig(name="app1", type=TunnelType.HTTP, local_port=3000),
                    ExampleTunnelConfig(name="app2", type=TunnelType.HTTP, local_port=3000)
                ]
            )

    def test_example_config_helper_methods(self):
        """Test ExampleConfig helper methods"""
        config = ExampleConfig(
            project_name="test",
            server_host="example.com",
            tunnels=[
                ExampleTunnelConfig(name="web", type=TunnelType.HTTP, local_port=3000, path="web"),
                ExampleTunnelConfig(name="api", type=TunnelType.HTTP, local_port=8000, path="api"),
                ExampleTunnelConfig(name="ssh", type=TunnelType.TCP, local_port=22)
            ]
        )

        # Test get_tunnel_by_name
        web_tunnel = config.get_tunnel_by_name("web")
        assert web_tunnel is not None
        assert web_tunnel.path == "web"

        # Test get_http_tunnels
        http_tunnels = config.get_http_tunnels()
        assert len(http_tunnels) == 2
        assert all(t.type == TunnelType.HTTP for t in http_tunnels)

        # Test get_tcp_tunnels
        tcp_tunnels = config.get_tcp_tunnels()
        assert len(tcp_tunnels) == 1
        assert tcp_tunnels[0].name == "ssh"

class TestExampleMetadata:
    def test_example_metadata_creation(self):
        """Test ExampleMetadata creation"""
        metadata = ExampleMetadata(
            title="Basic HTTP Tunnel Example",
            description="This example demonstrates how to create a basic HTTP tunnel using the FRP Python Wrapper.",
            difficulty="beginner",
            tags=["http", "tunnel", "basic"],
            estimated_time=10,
            tutorial_steps=[
                "Install the FRP Python Wrapper",
                "Configure the tunnel settings",
                "Create and start the tunnel",
                "Test the connection"
            ],
            troubleshooting={
                "Connection refused": "Check if the FRP server is running and accessible",
                "Authentication failed": "Verify your auth token is correct"
            }
        )

        assert metadata.title == "Basic HTTP Tunnel Example"
        assert metadata.difficulty == "beginner"
        assert len(metadata.tags) == 3
        assert len(metadata.tutorial_steps) == 4

    def test_example_metadata_validation_errors(self):
        """Test ExampleMetadata validation errors"""
        # Invalid difficulty level
        with pytest.raises(ValueError, match="String should match pattern"):
            ExampleMetadata(
                title="Test",
                description="Test description that is long enough",
                difficulty="expert",  # Invalid
                tags=["test"],
                estimated_time=10
            )

        # Description too short
        with pytest.raises(ValueError, match="at least 10 characters"):
            ExampleMetadata(
                title="Test",
                description="Short",  # Too short
                difficulty="beginner",
                tags=["test"],
                estimated_time=10
            )

class TestDocumentationConfig:
    def test_documentation_config_creation(self):
        """Test DocumentationConfig creation"""
        config = DocumentationConfig(
            project_name="FRP Python Wrapper",
            version="1.0.0",
            author="Example Author",
            description="A Python wrapper for FRP tunneling",
            output_dir="build/docs",
            include_api_reference=True,
            auto_generate=True
        )

        assert config.project_name == "FRP Python Wrapper"
        assert config.version == "1.0.0"
        assert config.output_dir == "build/docs"
        assert config.include_api_reference is True

    def test_documentation_config_version_validation(self):
        """Test version format validation"""
        # Valid version
        config = DocumentationConfig(
            project_name="Test",
            version="1.2.3",
            author="Test",
            description="Test"
        )
        assert config.version == "1.2.3"

        # Invalid version format
        with pytest.raises(ValueError, match="String should match pattern"):
            DocumentationConfig(
                project_name="Test",
                version="v1.0",  # Invalid format
                author="Test",
                description="Test"
            )

class TestExampleExecution:
    """Test framework for validating example execution"""

    @pytest.fixture
    def example_config_file(self):
        """Create temporary example config file"""
        config = ExampleConfig(
            project_name="test-project",
            server_host="localhost",
            auth_token="test_token_12345678",
            tunnels=[
                ExampleTunnelConfig(
                    name="test-web",
                    type=TunnelType.HTTP,
                    local_port=3000,
                    path="test"
                )
            ]
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(config.model_dump_json(indent=2))
            return f.name

    @patch('frp_wrapper.client.FRPClient')
    def test_basic_example_execution(self, mock_client_class, example_config_file):
        """Test basic example execution with mocked client"""
        # Mock the FRPClient
        mock_client = Mock()
        mock_client.connect.return_value = True
        mock_client.is_connected.return_value = True
        mock_client_class.return_value = mock_client

        # Mock tunnel
        mock_tunnel = Mock()
        mock_tunnel.id = "test-tunnel"
        mock_tunnel.url = "https://example.com/test/"
        mock_client.expose_path.return_value = mock_tunnel

        # Load config and simulate example execution
        config = ExampleConfig.model_validate_json(Path(example_config_file).read_text())

        # Simulate the example execution
        with mock_client as client:
            for tunnel_config in config.tunnels:
                if tunnel_config.type == TunnelType.HTTP:
                    tunnel = client.expose_path(
                        tunnel_config.local_port,
                        tunnel_config.path
                    )
                    assert tunnel.url == "https://example.com/test/"

        # Verify client methods were called
        mock_client.connect.assert_called_once()
        mock_client.expose_path.assert_called_once_with(3000, "test")

    def test_example_config_file_generation(self):
        """Test generating example configuration files"""
        # Development environment config
        dev_config = ExampleConfig(
            environment=ExampleEnvironment.DEVELOPMENT,
            project_name="dev-environment",
            server_host="dev.tunnel.example.com",
            auth_token="dev_token_123456789",
            tunnels=[
                ExampleTunnelConfig(
                    name="react-app",
                    type=TunnelType.HTTP,
                    local_port=3000,
                    path="dev",
                    websocket_support=True,
                    custom_headers={"X-Environment": "Development"}
                ),
                ExampleTunnelConfig(
                    name="api-server",
                    type=TunnelType.HTTP,
                    local_port=8000,
                    path="api",
                    strip_path=False
                )
            ],
            log_level="DEBUG"
        )

        # Production environment config
        prod_config = ExampleConfig(
            environment=ExampleEnvironment.PRODUCTION,
            project_name="production-app",
            server_host="tunnel.example.com",
            auth_token="prod_secure_token_123456789",
            tunnels=[
                ExampleTunnelConfig(
                    name="web-app",
                    type=TunnelType.HTTP,
                    local_port=80,
                    path="app",
                    basic_auth="admin:secure_password_123"
                ),
                ExampleTunnelConfig(
                    name="admin-panel",
                    type=TunnelType.HTTP,
                    local_port=8080,
                    path="admin",
                    basic_auth="admin:admin_password_456"
                )
            ],
            auto_reconnect=True,
            log_level="WARNING"
        )

        # Verify configs are valid
        assert dev_config.environment == ExampleEnvironment.DEVELOPMENT
        assert len(dev_config.tunnels) == 2
        assert prod_config.environment == ExampleEnvironment.PRODUCTION
        assert prod_config.auto_reconnect is True

        # Test serialization
        dev_json = dev_config.model_dump_json(indent=2)
        prod_json = prod_config.model_dump_json(indent=2)

        # Verify we can deserialize
        restored_dev = ExampleConfig.model_validate_json(dev_json)
        restored_prod = ExampleConfig.model_validate_json(prod_json)

        assert restored_dev.project_name == "dev-environment"
        assert restored_prod.project_name == "production-app"

class TestDocumentationGeneration:
    def test_api_documentation_structure(self):
        """Test API documentation structure validation"""
        doc_config = DocumentationConfig(
            project_name="FRP Python Wrapper",
            version="1.0.0",
            author="Test Author",
            description="Test Description",
            include_api_reference=True,
            include_examples=True,
            include_tutorials=True
        )

        # Verify configuration is valid
        assert doc_config.include_api_reference is True
        assert doc_config.include_examples is True
        assert doc_config.include_tutorials is True

        # Test documentation paths
        assert doc_config.output_dir == "docs"
        assert doc_config.api_docs_dir == "api"
        assert doc_config.examples_docs_dir == "examples"

    def test_example_metadata_validation(self):
        """Test comprehensive example metadata validation"""
        complete_metadata = ExampleMetadata(
            title="Complete Multi-Service Example",
            description="A comprehensive example showing how to set up multiple services with HTTP tunnels, TCP tunnels, monitoring, and production deployment patterns.",
            difficulty="advanced",
            tags=["http", "tcp", "monitoring", "production", "multi-service"],
            requirements=["flask", "fastapi", "uvicorn", "requests"],
            estimated_time=45,
            tutorial_steps=[
                "Set up the development environment",
                "Configure multiple service tunnels",
                "Enable monitoring and logging",
                "Test the complete setup",
                "Deploy to production environment"
            ],
            troubleshooting={
                "Port conflicts": "Ensure all local ports are unique and not in use",
                "SSL certificate errors": "Check domain configuration and certificate validity",
                "Performance issues": "Monitor connection metrics and adjust timeouts",
                "Authentication failures": "Verify auth tokens and server configuration"
            },
            related_docs=["api-reference.md", "deployment-guide.md", "monitoring.md"],
            external_links=["https://github.com/fatedier/frp"]
        )

        # Verify all fields are properly set
        assert complete_metadata.difficulty == "advanced"
        assert len(complete_metadata.tags) == 5
        assert len(complete_metadata.requirements) == 4
        assert len(complete_metadata.tutorial_steps) == 5
        assert len(complete_metadata.troubleshooting) == 4
        assert len(complete_metadata.external_links) == 1

        # Test serialization and deserialization
        metadata_json = complete_metadata.model_dump_json(indent=2)
        restored_metadata = ExampleMetadata.model_validate_json(metadata_json)

        assert restored_metadata.title == complete_metadata.title
        assert restored_metadata.estimated_time == 45

# Integration tests
class TestExampleIntegration:
    def test_complete_example_workflow(self):
        """Test complete example workflow from config to execution"""
        # 1. Create comprehensive example configuration
        example_config = ExampleConfig(
            environment=ExampleEnvironment.DEVELOPMENT,
            project_name="integration-test",
            description="Integration test example",
            server_host="localhost",
            server_port=7000,
            auth_token="integration_test_token_123",
            tunnels=[
                ExampleTunnelConfig(
                    name="web-frontend",
                    type=TunnelType.HTTP,
                    local_port=3000,
                    path="frontend",
                    websocket_support=True,
                    custom_headers={"X-Service": "Frontend"}
                ),
                ExampleTunnelConfig(
                    name="api-backend",
                    type=TunnelType.HTTP,
                    local_port=8000,
                    path="api",
                    strip_path=False,
                    basic_auth="api:secure123"
                ),
                ExampleTunnelConfig(
                    name="database-tunnel",
                    type=TunnelType.TCP,
                    local_port=5432,
                    remote_port=15432
                )
            ],
            enable_monitoring=True,
            monitoring_port=9999,
            auto_reconnect=True,
            reconnect_interval=30
        )

        # 2. Create example metadata
        example_metadata = ExampleMetadata(
            title="Multi-Service Integration Example",
            description="Demonstrates setting up multiple HTTP and TCP tunnels with monitoring for a complete web application stack.",
            difficulty="intermediate",
            tags=["integration", "multi-service", "http", "tcp", "monitoring"],
            estimated_time=30,
            tutorial_steps=[
                "Configure the example settings",
                "Start the FRP client and tunnels",
                "Test HTTP services access",
                "Test TCP tunnel connectivity",
                "Monitor tunnel performance"
            ],
            troubleshooting={
                "Connection timeout": "Check server accessibility and network connectivity",
                "Authentication error": "Verify auth token configuration",
                "Port binding error": "Ensure local ports are available"
            }
        )

        # 3. Validate complete configuration
        assert len(example_config.tunnels) == 3
        assert example_config.get_http_tunnels().__len__() == 2
        assert example_config.get_tcp_tunnels().__len__() == 1

        # 4. Test configuration serialization
        config_json = example_config.model_dump_json(indent=2)
        metadata_json = example_metadata.model_dump_json(indent=2)

        # 5. Test deserialization
        restored_config = ExampleConfig.model_validate_json(config_json)
        restored_metadata = ExampleMetadata.model_validate_json(metadata_json)

        assert restored_config.project_name == "integration-test"
        assert restored_metadata.difficulty == "intermediate"

        # 6. Verify tunnel configurations are properly structured
        web_tunnel = restored_config.get_tunnel_by_name("web-frontend")
        api_tunnel = restored_config.get_tunnel_by_name("api-backend")
        db_tunnel = restored_config.get_tunnel_by_name("database-tunnel")

        assert web_tunnel.websocket_support is True
        assert api_tunnel.basic_auth == "api:secure123"
        assert db_tunnel.remote_port == 15432

    def test_documentation_config_validation(self):
        """Test documentation configuration validation"""
        doc_config = DocumentationConfig(
            project_name="FRP Python Wrapper Examples",
            version="1.0.0",
            author="FRP Wrapper Team",
            description="Comprehensive examples and documentation for the FRP Python Wrapper library",
            output_dir="build/documentation",
            api_docs_dir="reference",
            examples_docs_dir="tutorials",
            include_api_reference=True,
            include_examples=True,
            include_tutorials=True,
            auto_generate=True,
            validate_links=True,
            generate_toc=True
        )

        # Verify all settings
        assert doc_config.project_name == "FRP Python Wrapper Examples"
        assert doc_config.version == "1.0.0"
        assert doc_config.output_dir == "build/documentation"
        assert doc_config.auto_generate is True
        assert doc_config.validate_links is True

        # Test serialization for CI/CD configuration
        config_dict = doc_config.model_dump()

        assert config_dict["include_api_reference"] is True
        assert config_dict["generate_toc"] is True

        # Test restoration from dict (for CI/CD pipelines)
        restored_config = DocumentationConfig.model_validate(config_dict)
        assert restored_config.author == "FRP Wrapper Team"
```

### 3. Complete Example Implementation

```python
# examples/production_ready_example.py
"""
Production-Ready Multi-Service Example with Pydantic Configuration

This example demonstrates a complete production setup with:
- Pydantic-based configuration management
- Multiple HTTP and TCP tunnels
- Monitoring and logging
- Error handling and recovery
- Health checks and auto-reconnection
"""

import asyncio
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional, Dict, List
from contextlib import asynccontextmanager

from pydantic import ValidationError
from frp_wrapper import FRPClient
from frp_wrapper.monitoring import MonitoringSystem, MonitoringConfig
from examples.config.models import ExampleConfig, ExampleTunnelConfig, TunnelType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('frp_example.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProductionTunnelManager:
    """Production-ready tunnel manager with Pydantic configuration"""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config: Optional[ExampleConfig] = None
        self.client: Optional[FRPClient] = None
        self.monitoring: Optional[MonitoringSystem] = None
        self.tunnels: Dict[str, Any] = {}
        self.running = False

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def load_config(self) -> None:
        """Load and validate configuration from file"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

            config_text = self.config_path.read_text()
            self.config = ExampleConfig.model_validate_json(config_text)

            logger.info(f"Configuration loaded: {self.config.project_name}")
            logger.info(f"Environment: {self.config.environment}")
            logger.info(f"Tunnels: {len(self.config.tunnels)}")

        except ValidationError as e:
            logger.error(f"Configuration validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def setup_monitoring(self) -> None:
        """Setup monitoring system if enabled"""
        if not self.config.enable_monitoring:
            return

        monitoring_config = MonitoringConfig(
            metrics_collection_interval=5.0,
            enable_dashboard=True,
            dashboard_port=self.config.monitoring_port,
            logging=LoggingConfig(
                level=LogLevel(self.config.log_level.lower()),
                enable_file_logging=True,
                log_file="frp_monitoring.log"
            )
        )

        self.monitoring = MonitoringSystem(monitoring_config)
        self.monitoring.start()

        logger.info(f"Monitoring dashboard available at: http://localhost:{self.config.monitoring_port}")

    def create_client(self) -> None:
        """Create and configure FRP client"""
        self.client = FRPClient(
            server=self.config.server_host,
            port=self.config.server_port,
            auth_token=self.config.auth_token,
            auto_reconnect=self.config.auto_reconnect,
            reconnect_interval=self.config.reconnect_interval
        )

        # Setup event handlers
        self.client.on_connect = self._on_client_connect
        self.client.on_disconnect = self._on_client_disconnect
        self.client.on_tunnel_connect = self._on_tunnel_connect
        self.client.on_tunnel_disconnect = self._on_tunnel_disconnect

    def _on_client_connect(self) -> None:
        """Handle client connection events"""
        logger.info("FRP client connected successfully")

    def _on_client_disconnect(self) -> None:
        """Handle client disconnection events"""
        logger.warning("FRP client disconnected")

    def _on_tunnel_connect(self, tunnel_id: str) -> None:
        """Handle tunnel connection events"""
        logger.info(f"Tunnel connected: {tunnel_id}")
        if self.monitoring:
            self.monitoring.register_tunnel(tunnel_id)

    def _on_tunnel_disconnect(self, tunnel_id: str) -> None:
        """Handle tunnel disconnection events"""
        logger.warning(f"Tunnel disconnected: {tunnel_id}")
        if self.monitoring:
            self.monitoring.unregister_tunnel(tunnel_id)

    def create_tunnels(self) -> None:
        """Create all configured tunnels"""
        for tunnel_config in self.config.tunnels:
            try:
                tunnel = self._create_single_tunnel(tunnel_config)
                self.tunnels[tunnel_config.name] = tunnel
                logger.info(f"Created tunnel: {tunnel_config.name} -> {getattr(tunnel, 'url', 'TCP tunnel')}")

            except Exception as e:
                logger.error(f"Failed to create tunnel {tunnel_config.name}: {e}")
                raise

    def _create_single_tunnel(self, config: ExampleTunnelConfig):
        """Create a single tunnel based on configuration"""
        if config.type == TunnelType.HTTP:
            return self.client.expose_path(
                local_port=config.local_port,
                path=config.path,
                websocket=config.websocket_support,
                strip_path=config.strip_path,
                custom_headers=config.custom_headers,
                basic_auth=config.basic_auth
            )
        elif config.type == TunnelType.TCP:
            return self.client.expose_tcp(
                local_port=config.local_port,
                remote_port=config.remote_port
            )
        else:
            raise ValueError(f"Unsupported tunnel type: {config.type}")

    async def start(self) -> None:
        """Start the tunnel manager"""
        try:
            logger.info("Starting production tunnel manager...")

            # Load configuration
            self.load_config()

            # Setup monitoring
            self.setup_monitoring()

            # Create client
            self.create_client()

            # Connect to server
            self.client.connect()

            # Create tunnels
            self.create_tunnels()

            self.running = True
            logger.info("All tunnels created successfully")

            # Print tunnel information
            self._print_tunnel_info()

            # Start health check loop
            await self._health_check_loop()

        except Exception as e:
            logger.error(f"Failed to start tunnel manager: {e}")
            await self.shutdown()
            raise

    def _print_tunnel_info(self) -> None:
        """Print information about created tunnels"""
        print("\n" + "="*50)
        print(f"🚀 {self.config.project_name} - Tunnels Active")
        print("="*50)

        for name, tunnel in self.tunnels.items():
            tunnel_config = self.config.get_tunnel_by_name(name)
            if tunnel_config.type == TunnelType.HTTP:
                print(f"🌐 {name}: {tunnel.url}")
                if tunnel_config.websocket_support:
                    print(f"   WebSocket: {tunnel.websocket_url}")
            else:
                print(f"🔗 {name}: {self.config.server_host}:{tunnel_config.remote_port}")

        if self.config.enable_monitoring:
            print(f"📊 Monitoring: http://localhost:{self.config.monitoring_port}")

        print("="*50)
        print("Press Ctrl+C to stop")

    async def _health_check_loop(self) -> None:
        """Continuous health check loop"""
        while self.running:
            try:
                # Check client connection
                if not self.client.is_connected():
                    logger.warning("Client connection lost, attempting reconnection...")

                # Check tunnel status
                for name, tunnel in self.tunnels.items():
                    if hasattr(tunnel, 'status') and tunnel.status != 'connected':
                        logger.warning(f"Tunnel {name} is not connected: {tunnel.status}")

                # Wait before next check
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(10)

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False
        asyncio.create_task(self.shutdown())

    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("Shutting down tunnel manager...")
        self.running = False

        # Close tunnels
        if self.client:
            try:
                for name in list(self.tunnels.keys()):
                    tunnel = self.tunnels[name]
                    if hasattr(tunnel, 'close'):
                        tunnel.close()
                    logger.info(f"Closed tunnel: {name}")

                # Disconnect client
                self.client.disconnect()
                logger.info("Client disconnected")

            except Exception as e:
                logger.error(f"Error during tunnel cleanup: {e}")

        # Stop monitoring
        if self.monitoring:
            self.monitoring.stop()
            logger.info("Monitoring stopped")

        logger.info("Shutdown complete")

async def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python production_ready_example.py <config_file>")
        print("Example: python production_ready_example.py config/production.json")
        sys.exit(1)

    config_file = sys.argv[1]

    if not Path(config_file).exists():
        logger.error(f"Configuration file not found: {config_file}")
        sys.exit(1)

    manager = ProductionTunnelManager(config_file)

    try:
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

## Implementation Timeline (TDD + Pydantic)

### Day 1: Configuration Models & Test Framework
1. **Write configuration model tests**: ExampleConfig, TunnelConfig validation
2. **Implement Pydantic models**: Complete configuration system with validation
3. **Write example execution tests**: Test framework for validating examples
4. **Create test configurations**: Development, staging, production configs

### Day 2: Production Examples & Documentation
1. **Write production example tests**: Complex multi-service scenarios
2. **Implement production examples**: Real-world use cases with monitoring
3. **Write documentation generation tests**: API docs, tutorials, guides
4. **Create comprehensive documentation**: User guides, API reference

### Day 3: Integration & Packaging
1. **Write integration tests**: End-to-end example validation
2. **Create deployment examples**: Docker, CI/CD, production deployment
3. **Package documentation**: Generate final docs and validate links
4. **Final testing**: All examples, documentation, and package deployment

## File Structure
```
examples/
├── __init__.py
├── config/
│   ├── __init__.py
│   ├── models.py                    # Pydantic configuration models
│   ├── development.json             # Development configuration
│   ├── staging.json                 # Staging configuration
│   └── production.json              # Production configuration
├── basic/
│   ├── 01_simple_http_tunnel.py     # Basic HTTP tunnel
│   ├── 02_tcp_tunnel.py             # Basic TCP tunnel
│   └── 03_context_manager.py        # Context manager usage
├── intermediate/
│   ├── 04_multiple_services.py      # Multi-service setup
│   ├── 05_webhook_receiver.py       # Webhook handling
│   └── 06_api_gateway.py            # API gateway pattern
├── advanced/
│   ├── 07_monitoring_integration.py # Monitoring and metrics
│   ├── 08_production_deployment.py  # Production-ready setup
│   └── 09_custom_middleware.py      # Custom middleware
└── production_ready_example.py      # Complete production example

docs/
├── __init__.py
├── README.md                        # Main documentation
├── quickstart.md                    # Quick start guide
├── api-reference.md                 # Complete API reference
├── configuration.md                 # Configuration guide
├── examples/                        # Example documentation
├── deployment/                      # Deployment guides
└── troubleshooting.md              # Common issues and solutions

tests/
├── __init__.py
├── test_examples.py                 # Example validation tests
├── test_example_configs.py          # Configuration tests
├── test_documentation.py           # Documentation validation
└── test_example_integration.py     # Integration tests
```

## Success Criteria
- [ ] 100% test coverage for all examples
- [ ] All Pydantic configuration models validated
- [ ] Production-ready examples with monitoring
- [ ] Complete API documentation generated
- [ ] All external links validated
- [ ] Package ready for PyPI deployment
- [ ] CI/CD pipeline for documentation

## Key Pydantic Benefits for Examples & Documentation
1. **Configuration Validation**: Comprehensive validation of example configurations
2. **Type Safety**: Full IDE support for example development
3. **Documentation Generation**: Auto-generated configuration documentation
4. **Serialization**: Easy JSON/YAML configuration files
5. **Error Messages**: Clear validation errors for example setup
6. **Versioning**: Configuration schema versioning and migration

This approach provides production-ready examples with comprehensive validation, excellent documentation, and robust configuration management suitable for enterprise deployments and easy onboarding of new users.
