# Checkpoint 3: Tunnel Management with Pydantic (TDD Approach)

## Overview
TDD와 Pydantic v2를 활용하여 간단하고 타입 안전한 터널 관리 시스템을 구현합니다. Pydantic BaseModel을 사용해 강력한 데이터 검증과 직렬화를 제공합니다.

## Goals
- Pydantic v2 BaseModel을 활용한 타입 안전 터널 모델
- TCP/HTTP 터널 생성 및 관리
- 강력한 데이터 검증 및 오류 처리
- Context manager를 통한 자동 리소스 정리
- 100% TDD 커버리지

## Test-First Implementation with Pydantic

### 1. Pydantic Models
```python
# src/frp_wrapper/tunnel.py
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from pydantic import HttpUrl, IPvAnyAddress

class TunnelStatus(str, Enum):
    """Tunnel status enumeration"""
    PENDING = "pending"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CLOSED = "closed"

class TunnelType(str, Enum):
    """Tunnel type enumeration"""
    TCP = "tcp"
    HTTP = "http"
    UDP = "udp"

class BaseTunnel(BaseModel):
    """Base tunnel model with Pydantic validation"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid',
        frozen=True,  # Immutable after creation
        use_enum_values=True
    )

    id: str = Field(..., min_length=1, description="Unique tunnel identifier")
    tunnel_type: TunnelType = Field(..., description="Type of tunnel")
    local_port: int = Field(..., ge=1, le=65535, description="Local port number")
    status: TunnelStatus = Field(default=TunnelStatus.PENDING, description="Current tunnel status")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    connected_at: Optional[datetime] = Field(None, description="Connection timestamp")
    error_message: Optional[str] = Field(None, description="Error message if any")

    @field_validator('local_port')
    @classmethod
    def validate_port_range(cls, v: int) -> int:
        """Validate port is in valid range"""
        if v < 1024:
            # Warning for privileged ports but don't fail
            import warnings
            warnings.warn(f"Port {v} is privileged and may require root access")
        return v

    def with_status(self, status: TunnelStatus, **kwargs) -> 'BaseTunnel':
        """Create new tunnel with updated status (immutable pattern)"""
        update_data = {'status': status, **kwargs}
        if status == TunnelStatus.CONNECTED and 'connected_at' not in kwargs:
            update_data['connected_at'] = datetime.now()
        return self.model_copy(update=update_data)

class TCPTunnel(BaseTunnel):
    """TCP tunnel with remote port configuration"""

    tunnel_type: TunnelType = Field(default=TunnelType.TCP, frozen=True)
    remote_port: Optional[int] = Field(None, ge=1, le=65535, description="Remote port number")

    @property
    def endpoint(self) -> Optional[str]:
        """Get tunnel endpoint if connected"""
        if self.status == TunnelStatus.CONNECTED and self.remote_port:
            # Server host would be injected during runtime
            return f"{{server_host}}:{self.remote_port}"
        return None

class HTTPTunnel(BaseTunnel):
    """HTTP tunnel with path-based routing using FRP locations"""

    tunnel_type: TunnelType = Field(default=TunnelType.HTTP, frozen=True)
    path: str = Field(..., min_length=1, description="URL path for routing")
    custom_domains: List[str] = Field(default_factory=list, description="Custom domains")
    strip_path: bool = Field(default=True, description="Whether to strip path in requests")
    websocket: bool = Field(default=True, description="Enable WebSocket support")
    custom_headers: Dict[str, str] = Field(default_factory=dict, description="Custom headers")

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate path format"""
        if v.startswith('/'):
            raise ValueError("Path should not start with '/'")
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Path should contain only alphanumeric characters, hyphens, and underscores")
        return v

    @property
    def url(self) -> Optional[str]:
        """Get tunnel URL if connected"""
        if self.status == TunnelStatus.CONNECTED and self.custom_domains:
            domain = self.custom_domains[0]
            return f"https://{domain}/{self.path}/"
        return None

    @property
    def locations(self) -> List[str]:
        """Get FRP locations configuration"""
        return [f"/{self.path}"]

class TunnelConfig(BaseModel):
    """Configuration for creating tunnels"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid'
    )

    server_host: str = Field(..., min_length=1, description="FRP server hostname")
    auth_token: Optional[str] = Field(None, description="Authentication token")
    default_domain: Optional[str] = Field(None, description="Default domain for HTTP tunnels")
    max_tunnels: int = Field(default=10, ge=1, le=100, description="Maximum concurrent tunnels")

    @field_validator('server_host')
    @classmethod
    def validate_server_host(cls, v: str) -> str:
        """Validate server hostname format"""
        if not v.replace('.', '').replace('-', '').isalnum():
            raise ValueError("Invalid hostname format")
        return v
```

### 2. Test Structure with Pydantic
```python
# tests/test_tunnel.py
import pytest
from datetime import datetime
from pydantic import ValidationError
from frp_wrapper.tunnel import BaseTunnel, TCPTunnel, HTTPTunnel, TunnelStatus, TunnelType, TunnelConfig

class TestBaseTunnel:
    def test_tunnel_creation_with_valid_data(self):
        """Test tunnel creation with valid Pydantic data"""
        tunnel = BaseTunnel(
            id="test-tunnel-1",
            tunnel_type=TunnelType.TCP,
            local_port=3000
        )

        assert tunnel.id == "test-tunnel-1"
        assert tunnel.tunnel_type == TunnelType.TCP
        assert tunnel.local_port == 3000
        assert tunnel.status == TunnelStatus.PENDING
        assert isinstance(tunnel.created_at, datetime)

    def test_tunnel_port_validation(self):
        """Test port validation with Pydantic validators"""
        # Valid port
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=8080)
        assert tunnel.local_port == 8080

        # Invalid ports
        with pytest.raises(ValidationError) as exc_info:
            BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=0)

        errors = exc_info.value.errors()
        assert any("greater than or equal to 1" in str(error) for error in errors)

        with pytest.raises(ValidationError):
            BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=65536)

    def test_tunnel_immutability(self):
        """Test that tunnel is immutable after creation"""
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=3000)

        # Pydantic frozen model should prevent direct modification
        with pytest.raises(ValidationError):
            tunnel.status = TunnelStatus.CONNECTED

    def test_tunnel_with_status_creates_new_instance(self):
        """Test immutable status update pattern"""
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=3000)

        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)

        # Original tunnel unchanged
        assert tunnel.status == TunnelStatus.PENDING
        assert tunnel.connected_at is None

        # New tunnel has updated status
        assert connected_tunnel.status == TunnelStatus.CONNECTED
        assert connected_tunnel.connected_at is not None
        assert connected_tunnel.id == tunnel.id  # Other fields preserved

class TestTCPTunnel:
    def test_tcp_tunnel_creation(self):
        """Test TCP tunnel creation with Pydantic validation"""
        tunnel = TCPTunnel(
            id="tcp-test",
            local_port=3000,
            remote_port=8080
        )

        assert tunnel.tunnel_type == TunnelType.TCP
        assert tunnel.local_port == 3000
        assert tunnel.remote_port == 8080

    def test_tcp_tunnel_endpoint_property(self):
        """Test TCP tunnel endpoint generation"""
        tunnel = TCPTunnel(
            id="tcp-test",
            local_port=3000,
            remote_port=8080
        )

        # No endpoint when not connected
        assert tunnel.endpoint is None

        # Endpoint available when connected
        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        assert "{server_host}:8080" in connected_tunnel.endpoint

    def test_tcp_tunnel_validation_errors(self):
        """Test TCP tunnel Pydantic validation"""
        with pytest.raises(ValidationError):
            TCPTunnel(
                id="",  # Empty ID should fail
                local_port=3000
            )

        with pytest.raises(ValidationError):
            TCPTunnel(
                id="test",
                local_port=3000,
                remote_port=99999  # Invalid port
            )

class TestHTTPTunnel:
    def test_http_tunnel_creation(self):
        """Test HTTP tunnel creation with path validation"""
        tunnel = HTTPTunnel(
            id="http-test",
            local_port=3000,
            path="myapp",
            custom_domains=["example.com"]
        )

        assert tunnel.tunnel_type == TunnelType.HTTP
        assert tunnel.path == "myapp"
        assert tunnel.custom_domains == ["example.com"]
        assert tunnel.strip_path is True  # Default value
        assert tunnel.websocket is True  # Default value

    def test_http_tunnel_path_validation(self):
        """Test HTTP tunnel path validation with Pydantic validators"""
        # Valid paths
        HTTPTunnel(id="test", local_port=3000, path="myapp")
        HTTPTunnel(id="test", local_port=3000, path="my-app")
        HTTPTunnel(id="test", local_port=3000, path="my_app")
        HTTPTunnel(id="test", local_port=3000, path="app123")

        # Invalid paths
        with pytest.raises(ValidationError, match="Path should not start with"):
            HTTPTunnel(id="test", local_port=3000, path="/myapp")

        with pytest.raises(ValidationError, match="alphanumeric characters"):
            HTTPTunnel(id="test", local_port=3000, path="my@app")

    def test_http_tunnel_url_property(self):
        """Test HTTP tunnel URL generation"""
        tunnel = HTTPTunnel(
            id="http-test",
            local_port=3000,
            path="myapp",
            custom_domains=["example.com"]
        )

        # No URL when not connected
        assert tunnel.url is None

        # URL available when connected
        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        assert connected_tunnel.url == "https://example.com/myapp/"

    def test_http_tunnel_locations_property(self):
        """Test FRP locations configuration"""
        tunnel = HTTPTunnel(
            id="http-test",
            local_port=3000,
            path="myapp"
        )

        assert tunnel.locations == ["/myapp"]

class TestTunnelConfig:
    def test_config_creation_with_validation(self):
        """Test tunnel configuration with Pydantic validation"""
        config = TunnelConfig(
            server_host="tunnel.example.com",
            auth_token="secret123",
            default_domain="example.com",
            max_tunnels=5
        )

        assert config.server_host == "tunnel.example.com"
        assert config.auth_token == "secret123"
        assert config.max_tunnels == 5

    def test_config_validation_errors(self):
        """Test configuration validation errors"""
        with pytest.raises(ValidationError):
            TunnelConfig(server_host="")  # Empty hostname

        with pytest.raises(ValidationError):
            TunnelConfig(
                server_host="example.com",
                max_tunnels=0  # Below minimum
            )

        with pytest.raises(ValidationError):
            TunnelConfig(
                server_host="example.com",
                max_tunnels=101  # Above maximum
            )

# Pydantic serialization/deserialization tests
class TestTunnelSerialization:
    def test_tunnel_to_dict(self):
        """Test tunnel serialization to dict"""
        tunnel = HTTPTunnel(
            id="http-test",
            local_port=3000,
            path="myapp",
            custom_domains=["example.com"]
        )

        data = tunnel.model_dump()

        assert data['id'] == "http-test"
        assert data['tunnel_type'] == "http"
        assert data['local_port'] == 3000
        assert data['path'] == "myapp"

    def test_tunnel_from_dict(self):
        """Test tunnel deserialization from dict"""
        data = {
            'id': 'http-test',
            'tunnel_type': 'http',
            'local_port': 3000,
            'path': 'myapp',
            'custom_domains': ['example.com']
        }

        tunnel = HTTPTunnel.model_validate(data)

        assert tunnel.id == "http-test"
        assert tunnel.tunnel_type == TunnelType.HTTP
        assert tunnel.local_port == 3000
        assert tunnel.path == "myapp"

    def test_tunnel_json_serialization(self):
        """Test tunnel JSON serialization"""
        tunnel = TCPTunnel(
            id="tcp-test",
            local_port=3000,
            remote_port=8080
        )

        json_str = tunnel.model_dump_json()
        restored_tunnel = TCPTunnel.model_validate_json(json_str)

        assert restored_tunnel.id == tunnel.id
        assert restored_tunnel.local_port == tunnel.local_port
        assert restored_tunnel.remote_port == tunnel.remote_port
```

### 3. Tunnel Manager with Pydantic
```python
# src/frp_wrapper/tunnel_manager.py
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field
from .tunnel import BaseTunnel, TCPTunnel, HTTPTunnel, TunnelStatus, TunnelConfig
from .exceptions import TunnelError, TunnelNotFoundError

class TunnelRegistry(BaseModel):
    """Pydantic model for managing tunnel registry"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    tunnels: Dict[str, BaseTunnel] = Field(default_factory=dict)
    max_tunnels: int = Field(default=10, ge=1, le=100)

    def add_tunnel(self, tunnel: BaseTunnel) -> None:
        """Add tunnel to registry with validation"""
        if len(self.tunnels) >= self.max_tunnels:
            raise TunnelError(f"Maximum number of tunnels ({self.max_tunnels}) reached")

        if tunnel.id in self.tunnels:
            raise TunnelError(f"Tunnel with ID {tunnel.id} already exists")

        self.tunnels[tunnel.id] = tunnel

    def remove_tunnel(self, tunnel_id: str) -> BaseTunnel:
        """Remove tunnel from registry"""
        if tunnel_id not in self.tunnels:
            raise TunnelNotFoundError(f"Tunnel {tunnel_id} not found")

        return self.tunnels.pop(tunnel_id)

    def get_tunnel(self, tunnel_id: str) -> BaseTunnel:
        """Get tunnel by ID"""
        if tunnel_id not in self.tunnels:
            raise TunnelNotFoundError(f"Tunnel {tunnel_id} not found")

        return self.tunnels[tunnel_id]

    def update_tunnel(self, tunnel: BaseTunnel) -> None:
        """Update existing tunnel"""
        if tunnel.id not in self.tunnels:
            raise TunnelNotFoundError(f"Tunnel {tunnel.id} not found")

        self.tunnels[tunnel.id] = tunnel

    def list_tunnels(self, status: Optional[TunnelStatus] = None) -> List[BaseTunnel]:
        """List tunnels, optionally filtered by status"""
        tunnels = list(self.tunnels.values())

        if status:
            tunnels = [t for t in tunnels if t.status == status]

        return tunnels

    def get_stats(self) -> Dict[str, int]:
        """Get tunnel statistics"""
        stats = {status.value: 0 for status in TunnelStatus}

        for tunnel in self.tunnels.values():
            stats[tunnel.status.value] += 1

        stats['total'] = len(self.tunnels)
        return stats

class TunnelManager:
    """Main tunnel manager with Pydantic models"""

    def __init__(self, config: TunnelConfig):
        self.config = config
        self.registry = TunnelRegistry(max_tunnels=config.max_tunnels)

    def create_tcp_tunnel(self, tunnel_id: str, local_port: int,
                         remote_port: Optional[int] = None) -> TCPTunnel:
        """Create TCP tunnel with Pydantic validation"""
        tunnel = TCPTunnel(
            id=tunnel_id,
            local_port=local_port,
            remote_port=remote_port
        )

        self.registry.add_tunnel(tunnel)
        return tunnel

    def create_http_tunnel(self, tunnel_id: str, local_port: int, path: str,
                          custom_domains: Optional[List[str]] = None,
                          **kwargs) -> HTTPTunnel:
        """Create HTTP tunnel with Pydantic validation"""
        if custom_domains is None and self.config.default_domain:
            custom_domains = [self.config.default_domain]

        tunnel = HTTPTunnel(
            id=tunnel_id,
            local_port=local_port,
            path=path,
            custom_domains=custom_domains or [],
            **kwargs
        )

        self.registry.add_tunnel(tunnel)
        return tunnel

    def close_tunnel(self, tunnel_id: str) -> BaseTunnel:
        """Close tunnel and remove from registry"""
        tunnel = self.registry.get_tunnel(tunnel_id)
        closed_tunnel = tunnel.with_status(TunnelStatus.CLOSED)

        self.registry.remove_tunnel(tunnel_id)
        return closed_tunnel

    def get_tunnel_info(self, tunnel_id: str) -> Dict:
        """Get tunnel information as dict"""
        tunnel = self.registry.get_tunnel(tunnel_id)
        return tunnel.model_dump()

    def export_config(self) -> Dict:
        """Export all tunnels configuration"""
        return {
            'config': self.config.model_dump(),
            'tunnels': [tunnel.model_dump() for tunnel in self.registry.tunnels.values()]
        }
```

## Implementation Timeline (TDD + Pydantic)

### Day 1: Pydantic Models
1. **Setup Pydantic environment**: Install Pydantic v2, configure
2. **Write model tests**: Validation, serialization, deserialization
3. **Implement Pydantic models**: BaseTunnel, TCPTunnel, HTTPTunnel
4. **Custom validators**: Path validation, port validation

### Day 2: Tunnel Manager
1. **Write manager tests**: CRUD operations, validation
2. **Implement TunnelRegistry**: Pydantic-based registry
3. **Implement TunnelManager**: High-level tunnel operations
4. **Integration with config**: TunnelConfig validation

### Day 3: Context Managers & Advanced Features
1. **Context manager tests**: Automatic cleanup
2. **Implement tunnel context managers**: Auto-close functionality
3. **Serialization tests**: JSON export/import
4. **Performance tests**: Pydantic validation performance

## File Structure
```
src/frp_wrapper/
├── __init__.py
├── tunnel.py           # Pydantic tunnel models
├── tunnel_manager.py   # TunnelManager with Pydantic
├── client.py           # FRPClient (from checkpoint 2)
├── process.py          # ProcessManager (from checkpoint 1)
├── config.py           # ConfigBuilder with Pydantic
└── exceptions.py       # Custom exceptions

tests/
├── __init__.py
├── test_tunnel.py      # Pydantic model tests
├── test_tunnel_manager.py  # Manager tests
└── test_tunnel_integration.py  # Integration tests
```

## Success Criteria
- [ ] 100% test coverage with Pydantic models
- [ ] All validation scenarios tested
- [ ] Serialization/deserialization works perfectly
- [ ] Type safety with mypy
- [ ] Performance benchmarks with Pydantic
- [ ] Context managers for resource cleanup
- [ ] Integration with FRP configuration

## Key Pydantic Benefits
1. **Automatic Validation**: Built-in type and constraint validation
2. **Serialization**: Easy JSON/dict export/import
3. **Type Safety**: Full mypy compatibility
4. **Performance**: Rust-powered validation (v2)
5. **Documentation**: Auto-generated field documentation
6. **IDE Support**: Excellent autocomplete and error detection

This approach leverages Pydantic v2's powerful validation, serialization, and type safety features while maintaining comprehensive TDD coverage and simple, intuitive APIs.
