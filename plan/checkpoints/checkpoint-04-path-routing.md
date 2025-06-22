# Checkpoint 4: Path-Based Routing with Pydantic (TDD Approach)

## Overview
TDD와 Pydantic v2를 활용하여 FRP의 네이티브 `locations` 기능을 사용한 강력한 경로 기반 라우팅 시스템을 구현합니다. HTTP 터널을 경로별로 노출하는 핵심 기능을 제공합니다.

## Goals
- FRP locations 파라미터 활용한 경로 기반 라우팅
- Pydantic 기반 HTTP 터널 설정 및 검증
- customDomains와 locations 조합으로 직접 라우팅
- WebSocket 지원 및 경로 변환 옵션
- 완전한 TDD 커버리지

## Test-First Implementation with Pydantic

### 1. Enhanced HTTP Tunnel Models
```python
# src/frp_wrapper/http_tunnel.py
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from pydantic import HttpUrl, AnyHttpUrl
from .tunnel import BaseTunnel, TunnelType, TunnelStatus

class PathRewriteMode(str, Enum):
    """Path rewrite modes for HTTP tunnels"""
    STRIP = "strip"      # Remove path prefix
    PRESERVE = "preserve"  # Keep full path
    REWRITE = "rewrite"   # Custom rewrite rules

class HTTPHeaders(BaseModel):
    """Pydantic model for HTTP headers configuration"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid'
    )

    set_headers: Dict[str, str] = Field(default_factory=dict, description="Headers to set")
    remove_headers: List[str] = Field(default_factory=list, description="Headers to remove")
    host_header_rewrite: Optional[str] = Field(None, description="Rewrite Host header")

    @field_validator('set_headers')
    @classmethod
    def validate_header_names(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate HTTP header names"""
        for header_name in v.keys():
            if not header_name.replace('-', '').replace('_', '').isalnum():
                raise ValueError(f"Invalid header name: {header_name}")
        return v

class HTTPTunnelConfig(BaseModel):
    """Advanced HTTP tunnel configuration with Pydantic validation"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    # Core path routing
    path: str = Field(..., min_length=1, max_length=100, description="URL path for routing")
    custom_domains: List[str] = Field(..., min_items=1, description="Custom domains for tunnel")

    # Path handling
    path_rewrite_mode: PathRewriteMode = Field(default=PathRewriteMode.STRIP, description="How to handle path in requests")
    path_rewrite_rules: Dict[str, str] = Field(default_factory=dict, description="Custom path rewrite rules")

    # HTTP features
    websocket: bool = Field(default=True, description="Enable WebSocket support")
    compression: bool = Field(default=True, description="Enable compression")
    encryption: bool = Field(default=True, description="Enable encryption")

    # Headers and routing
    headers: HTTPHeaders = Field(default_factory=HTTPHeaders, description="HTTP headers configuration")
    basic_auth: Optional[str] = Field(None, description="Basic auth credentials (user:pass)")

    # Advanced routing
    subdomain_host: Optional[str] = Field(None, description="Subdomain host for routing")
    router_by_http_user: Optional[str] = Field(None, description="Route by HTTP user")

    @field_validator('path')
    @classmethod
    def validate_path_format(cls, v: str) -> str:
        """Validate path format for FRP locations"""
        if v.startswith('/'):
            raise ValueError("Path should not start with '/' - it will be added automatically")

        if v.endswith('/'):
            v = v.rstrip('/')

        # Allow alphanumeric, hyphens, underscores, and forward slashes for nested paths
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/')
        if not set(v).issubset(allowed_chars):
            raise ValueError("Path contains invalid characters. Use only alphanumeric, hyphens, underscores, and slashes")

        return v

    @field_validator('custom_domains')
    @classmethod
    def validate_domains(cls, v: List[str]) -> List[str]:
        """Validate domain names"""
        for domain in v:
            if not domain or '.' not in domain:
                raise ValueError(f"Invalid domain format: {domain}")
            # Basic domain validation
            parts = domain.split('.')
            for part in parts:
                if not part or not part.replace('-', '').isalnum():
                    raise ValueError(f"Invalid domain part in: {domain}")
        return v

    @field_validator('basic_auth')
    @classmethod
    def validate_basic_auth(cls, v: Optional[str]) -> Optional[str]:
        """Validate basic auth format"""
        if v is not None and ':' not in v:
            raise ValueError("Basic auth must be in format 'username:password'")
        return v

    @property
    def locations(self) -> List[str]:
        """Generate FRP locations configuration"""
        return [f"/{self.path}"]

    @property
    def frp_config(self) -> Dict[str, Any]:
        """Generate FRP proxy configuration"""
        config = {
            "type": "http",
            "customDomains": self.custom_domains,
            "locations": self.locations,
            "useCompression": self.compression,
            "useEncryption": self.encryption
        }

        # Add WebSocket support
        if self.websocket:
            config["websocket"] = True

        # Add headers configuration
        if self.headers.set_headers:
            config["requestHeaders"] = {"set": self.headers.set_headers}

        if self.headers.host_header_rewrite:
            config["hostHeaderRewrite"] = self.headers.host_header_rewrite

        # Add authentication
        if self.basic_auth:
            config["httpUser"], config["httpPwd"] = self.basic_auth.split(':', 1)

        # Add path rewriting
        if self.path_rewrite_mode == PathRewriteMode.REWRITE and self.path_rewrite_rules:
            config["pathRewrite"] = self.path_rewrite_rules

        return config

class AdvancedHTTPTunnel(BaseTunnel):
    """Enhanced HTTP tunnel with advanced path routing"""

    tunnel_type: TunnelType = Field(default=TunnelType.HTTP, frozen=True)
    config: HTTPTunnelConfig = Field(..., description="HTTP tunnel configuration")

    @property
    def url(self) -> Optional[str]:
        """Get tunnel URL with proper path handling"""
        if self.status == TunnelStatus.CONNECTED and self.config.custom_domains:
            domain = self.config.custom_domains[0]
            path = self.config.path

            # Use HTTPS by default for custom domains
            return f"https://{domain}/{path}/"
        return None

    @property
    def urls(self) -> List[str]:
        """Get all possible URLs for this tunnel"""
        if self.status != TunnelStatus.CONNECTED:
            return []

        urls = []
        for domain in self.config.custom_domains:
            urls.append(f"https://{domain}/{self.config.path}/")

        return urls

    @property
    def websocket_url(self) -> Optional[str]:
        """Get WebSocket URL if WebSocket is enabled"""
        if not self.config.websocket or self.status != TunnelStatus.CONNECTED:
            return None

        if self.config.custom_domains:
            domain = self.config.custom_domains[0]
            path = self.config.path
            return f"wss://{domain}/{path}/"

        return None

    def get_curl_command(self) -> Optional[str]:
        """Generate curl command for testing the tunnel"""
        if not self.url:
            return None

        cmd = f"curl -v {self.url}"

        if self.config.basic_auth:
            username, password = self.config.basic_auth.split(':', 1)
            cmd += f" -u {username}:{password}"

        return cmd

class PathMatcher(BaseModel):
    """Pydantic model for path matching and routing"""

    model_config = ConfigDict(str_strip_whitespace=True)

    pattern: str = Field(..., description="Path pattern to match")
    tunnel_id: str = Field(..., description="Tunnel ID to route to")
    priority: int = Field(default=0, description="Matching priority (higher = more priority)")

    @field_validator('pattern')
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Validate path pattern"""
        if not v.startswith('/'):
            v = '/' + v
        return v

    def matches(self, path: str) -> bool:
        """Check if path matches this pattern"""
        import fnmatch
        return fnmatch.fnmatch(path, self.pattern)

class RoutingTable(BaseModel):
    """Pydantic model for managing routing table"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    matchers: List[PathMatcher] = Field(default_factory=list)
    default_tunnel: Optional[str] = Field(None, description="Default tunnel for unmatched paths")

    def add_route(self, pattern: str, tunnel_id: str, priority: int = 0) -> None:
        """Add route to routing table"""
        matcher = PathMatcher(pattern=pattern, tunnel_id=tunnel_id, priority=priority)
        self.matchers.append(matcher)
        # Sort by priority (descending)
        self.matchers.sort(key=lambda m: m.priority, reverse=True)

    def find_tunnel(self, path: str) -> Optional[str]:
        """Find tunnel ID for given path"""
        for matcher in self.matchers:
            if matcher.matches(path):
                return matcher.tunnel_id

        return self.default_tunnel

    def get_routes_for_tunnel(self, tunnel_id: str) -> List[str]:
        """Get all route patterns for a tunnel"""
        return [m.pattern for m in self.matchers if m.tunnel_id == tunnel_id]
```

### 2. Test Structure for Path Routing
```python
# tests/test_http_tunnel.py
import pytest
from pydantic import ValidationError
from frp_wrapper.http_tunnel import (
    HTTPTunnelConfig, AdvancedHTTPTunnel, HTTPHeaders,
    PathRewriteMode, PathMatcher, RoutingTable
)
from frp_wrapper.tunnel import TunnelType, TunnelStatus

class TestHTTPTunnelConfig:
    def test_config_creation_with_valid_data(self):
        """Test HTTP tunnel config creation with Pydantic validation"""
        config = HTTPTunnelConfig(
            path="myapp",
            custom_domains=["example.com", "app.example.com"]
        )

        assert config.path == "myapp"
        assert config.custom_domains == ["example.com", "app.example.com"]
        assert config.websocket is True  # Default
        assert config.compression is True  # Default
        assert config.path_rewrite_mode == PathRewriteMode.STRIP

    def test_path_validation_errors(self):
        """Test path validation with various invalid inputs"""
        # Path starting with /
        with pytest.raises(ValidationError, match="should not start with"):
            HTTPTunnelConfig(path="/myapp", custom_domains=["example.com"])

        # Invalid characters
        with pytest.raises(ValidationError, match="invalid characters"):
            HTTPTunnelConfig(path="my@app", custom_domains=["example.com"])

        # Empty path
        with pytest.raises(ValidationError):
            HTTPTunnelConfig(path="", custom_domains=["example.com"])

        # Path too long
        with pytest.raises(ValidationError):
            HTTPTunnelConfig(path="a" * 101, custom_domains=["example.com"])

    def test_domain_validation(self):
        """Test domain validation with Pydantic validators"""
        # Valid domains
        config = HTTPTunnelConfig(
            path="app",
            custom_domains=["example.com", "sub.example.com", "app-1.example.org"]
        )
        assert len(config.custom_domains) == 3

        # Invalid domains
        with pytest.raises(ValidationError, match="Invalid domain"):
            HTTPTunnelConfig(path="app", custom_domains=["invalid"])

        with pytest.raises(ValidationError, match="Invalid domain"):
            HTTPTunnelConfig(path="app", custom_domains=[""])

        # Empty domains list
        with pytest.raises(ValidationError):
            HTTPTunnelConfig(path="app", custom_domains=[])

    def test_basic_auth_validation(self):
        """Test basic auth validation"""
        # Valid basic auth
        config = HTTPTunnelConfig(
            path="app",
            custom_domains=["example.com"],
            basic_auth="user:password"
        )
        assert config.basic_auth == "user:password"

        # Invalid basic auth (no colon)
        with pytest.raises(ValidationError, match="username:password"):
            HTTPTunnelConfig(
                path="app",
                custom_domains=["example.com"],
                basic_auth="userpassword"
            )

    def test_frp_config_generation(self):
        """Test FRP configuration generation"""
        config = HTTPTunnelConfig(
            path="myapp",
            custom_domains=["example.com"],
            websocket=True,
            compression=False,
            basic_auth="user:pass"
        )

        frp_config = config.frp_config

        assert frp_config["type"] == "http"
        assert frp_config["customDomains"] == ["example.com"]
        assert frp_config["locations"] == ["/myapp"]
        assert frp_config["websocket"] is True
        assert frp_config["useCompression"] is False
        assert frp_config["httpUser"] == "user"
        assert frp_config["httpPwd"] == "pass"

class TestHTTPHeaders:
    def test_headers_creation(self):
        """Test HTTP headers model creation"""
        headers = HTTPHeaders(
            set_headers={"X-Custom": "value", "X-App-Name": "MyApp"},
            remove_headers=["Server", "X-Powered-By"],
            host_header_rewrite="backend.internal"
        )

        assert headers.set_headers["X-Custom"] == "value"
        assert "Server" in headers.remove_headers
        assert headers.host_header_rewrite == "backend.internal"

    def test_header_name_validation(self):
        """Test header name validation"""
        # Valid header names
        headers = HTTPHeaders(set_headers={
            "X-Custom": "value",
            "Content-Type": "application/json",
            "X_Custom_Header": "value"
        })
        assert len(headers.set_headers) == 3

        # Invalid header names
        with pytest.raises(ValidationError, match="Invalid header name"):
            HTTPHeaders(set_headers={"Invalid@Header": "value"})

class TestAdvancedHTTPTunnel:
    def test_tunnel_creation(self):
        """Test advanced HTTP tunnel creation"""
        config = HTTPTunnelConfig(
            path="myapp",
            custom_domains=["example.com"]
        )

        tunnel = AdvancedHTTPTunnel(
            id="http-tunnel-1",
            local_port=3000,
            config=config
        )

        assert tunnel.tunnel_type == TunnelType.HTTP
        assert tunnel.config.path == "myapp"
        assert tunnel.local_port == 3000

    def test_url_generation(self):
        """Test URL generation for different states"""
        config = HTTPTunnelConfig(
            path="myapp",
            custom_domains=["example.com"]
        )

        tunnel = AdvancedHTTPTunnel(
            id="test",
            local_port=3000,
            config=config
        )

        # No URL when not connected
        assert tunnel.url is None
        assert tunnel.urls == []

        # URL available when connected
        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        assert connected_tunnel.url == "https://example.com/myapp/"
        assert "https://example.com/myapp/" in connected_tunnel.urls

    def test_websocket_url_generation(self):
        """Test WebSocket URL generation"""
        config = HTTPTunnelConfig(
            path="ws",
            custom_domains=["example.com"],
            websocket=True
        )

        tunnel = AdvancedHTTPTunnel(
            id="ws-tunnel",
            local_port=3000,
            config=config
        ).with_status(TunnelStatus.CONNECTED)

        assert tunnel.websocket_url == "wss://example.com/ws/"

        # No WebSocket URL when disabled
        config_no_ws = HTTPTunnelConfig(
            path="app",
            custom_domains=["example.com"],
            websocket=False
        )

        tunnel_no_ws = AdvancedHTTPTunnel(
            id="no-ws",
            local_port=3000,
            config=config_no_ws
        ).with_status(TunnelStatus.CONNECTED)

        assert tunnel_no_ws.websocket_url is None

    def test_curl_command_generation(self):
        """Test curl command generation for testing"""
        config = HTTPTunnelConfig(
            path="api",
            custom_domains=["api.example.com"],
            basic_auth="admin:secret"
        )

        tunnel = AdvancedHTTPTunnel(
            id="api-tunnel",
            local_port=8000,
            config=config
        ).with_status(TunnelStatus.CONNECTED)

        curl_cmd = tunnel.get_curl_command()

        assert "curl -v https://api.example.com/api/" in curl_cmd
        assert "-u admin:secret" in curl_cmd

class TestPathMatcher:
    def test_matcher_creation(self):
        """Test path matcher creation with validation"""
        matcher = PathMatcher(
            pattern="api/*",
            tunnel_id="api-tunnel",
            priority=10
        )

        assert matcher.pattern == "/api/*"  # Auto-adds leading slash
        assert matcher.tunnel_id == "api-tunnel"
        assert matcher.priority == 10

    def test_path_matching(self):
        """Test path matching logic"""
        matcher = PathMatcher(pattern="/api/*", tunnel_id="api-tunnel")

        assert matcher.matches("/api/users")
        assert matcher.matches("/api/posts/123")
        assert not matcher.matches("/app/users")
        assert not matcher.matches("/api")  # Doesn't match without trailing content

class TestRoutingTable:
    def test_routing_table_operations(self):
        """Test routing table operations"""
        table = RoutingTable()

        # Add routes
        table.add_route("/api/*", "api-tunnel", priority=10)
        table.add_route("/app/*", "app-tunnel", priority=5)
        table.add_route("/admin/*", "admin-tunnel", priority=15)

        # Test routing (should match by priority)
        assert table.find_tunnel("/api/users") == "api-tunnel"
        assert table.find_tunnel("/app/dashboard") == "app-tunnel"
        assert table.find_tunnel("/admin/settings") == "admin-tunnel"

        # Test default tunnel
        table.default_tunnel = "default-tunnel"
        assert table.find_tunnel("/unknown/path") == "default-tunnel"

    def test_route_priority_ordering(self):
        """Test that routes are ordered by priority"""
        table = RoutingTable()

        # Add routes in random order
        table.add_route("/api/v1/*", "api-v1", priority=5)
        table.add_route("/api/*", "api-general", priority=1)  # Lower priority
        table.add_route("/api/admin/*", "api-admin", priority=10)  # Higher priority

        # More specific route should match first due to higher priority
        assert table.find_tunnel("/api/admin/users") == "api-admin"
        assert table.find_tunnel("/api/v1/posts") == "api-v1"
        assert table.find_tunnel("/api/general") == "api-general"

# Integration tests with FRP configuration
class TestFRPIntegration:
    def test_frp_config_export(self):
        """Test exporting tunnel configuration for FRP"""
        config = HTTPTunnelConfig(
            path="myapp",
            custom_domains=["example.com"],
            websocket=True,
            headers=HTTPHeaders(
                set_headers={"X-App": "MyApp"},
                host_header_rewrite="localhost"
            )
        )

        frp_config = config.frp_config

        # Verify FRP-compatible configuration
        assert frp_config["type"] == "http"
        assert frp_config["customDomains"] == ["example.com"]
        assert frp_config["locations"] == ["/myapp"]
        assert frp_config["websocket"] is True
        assert frp_config["requestHeaders"]["set"]["X-App"] == "MyApp"
        assert frp_config["hostHeaderRewrite"] == "localhost"

    def test_complex_routing_scenario(self):
        """Test complex routing scenario with multiple tunnels"""
        # Create multiple tunnel configs
        api_config = HTTPTunnelConfig(
            path="api",
            custom_domains=["api.example.com"],
            basic_auth="api:secret"
        )

        app_config = HTTPTunnelConfig(
            path="app",
            custom_domains=["app.example.com"],
            websocket=True
        )

        admin_config = HTTPTunnelConfig(
            path="admin",
            custom_domains=["admin.example.com"],
            basic_auth="admin:supersecret",
            headers=HTTPHeaders(set_headers={"X-Admin": "true"})
        )

        # Create tunnels
        api_tunnel = AdvancedHTTPTunnel(
            id="api-tunnel",
            local_port=8000,
            config=api_config
        ).with_status(TunnelStatus.CONNECTED)

        app_tunnel = AdvancedHTTPTunnel(
            id="app-tunnel",
            local_port=3000,
            config=app_config
        ).with_status(TunnelStatus.CONNECTED)

        admin_tunnel = AdvancedHTTPTunnel(
            id="admin-tunnel",
            local_port=3001,
            config=admin_config
        ).with_status(TunnelStatus.CONNECTED)

        # Verify URLs
        assert api_tunnel.url == "https://api.example.com/api/"
        assert app_tunnel.url == "https://app.example.com/app/"
        assert admin_tunnel.url == "https://admin.example.com/admin/"

        # Verify WebSocket URLs
        assert api_tunnel.websocket_url is None  # WebSocket disabled by default
        assert app_tunnel.websocket_url == "wss://app.example.com/app/"
        assert admin_tunnel.websocket_url is None  # WebSocket disabled by default

        # Verify FRP configurations
        api_frp = api_config.frp_config
        assert api_frp["httpUser"] == "api"
        assert api_frp["httpPwd"] == "secret"

        admin_frp = admin_config.frp_config
        assert admin_frp["requestHeaders"]["set"]["X-Admin"] == "true"
```

## Implementation Timeline (TDD + Pydantic)

### Day 1: Enhanced HTTP Models
1. **Setup advanced Pydantic models**: HTTPTunnelConfig, HTTPHeaders
2. **Write comprehensive validation tests**: Path, domain, auth validation
3. **Implement custom validators**: Complex path validation, domain checking
4. **FRP config generation**: Native locations integration

### Day 2: Routing and Path Matching
1. **Write routing tests**: PathMatcher, RoutingTable functionality
2. **Implement path matching**: Pattern matching with priorities
3. **Advanced tunnel features**: WebSocket URLs, curl commands
4. **Integration tests**: Complex multi-tunnel scenarios

### Day 3: Client Integration
1. **Integrate with FRPClient**: expose_path method enhancement
2. **Context manager support**: Automatic tunnel cleanup
3. **Real FRP testing**: Integration with actual FRP binary
4. **Performance optimization**: Pydantic validation performance

## File Structure
```
src/frp_wrapper/
├── __init__.py
├── tunnel.py           # Base tunnel models
├── http_tunnel.py      # Advanced HTTP tunnel models
├── tunnel_manager.py   # Enhanced with path routing
├── client.py           # FRPClient with expose_path
├── process.py          # ProcessManager
├── config.py           # ConfigBuilder with Pydantic
└── exceptions.py       # Custom exceptions

tests/
├── __init__.py
├── test_http_tunnel.py # HTTP tunnel tests
├── test_path_routing.py # Routing logic tests
├── test_frp_integration.py # FRP binary integration
└── conftest.py         # Shared fixtures
```

## Success Criteria
- [ ] 100% test coverage for HTTP tunnels and routing
- [ ] All FRP locations configurations tested
- [ ] Path validation handles edge cases
- [ ] WebSocket support fully functional
- [ ] Custom domains and headers work correctly
- [ ] Integration with real FRP binary successful
- [ ] Performance benchmarks meet requirements

## Key Features Enabled by Pydantic
1. **Strong Validation**: Comprehensive path and domain validation
2. **Type Safety**: Full IDE support and mypy compatibility
3. **Serialization**: Easy export to FRP configuration format
4. **Documentation**: Auto-generated field documentation
5. **Error Messages**: Clear validation error messages
6. **Performance**: Rust-powered validation for high throughput

This approach leverages FRP's native `locations` feature while providing a robust, type-safe, and well-tested Python API with comprehensive validation and excellent developer experience.
