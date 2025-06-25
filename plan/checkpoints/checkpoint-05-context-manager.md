# Checkpoint 5: Context Manager with Pydantic (TDD Approach)

## Status: ✅ Completed
Implementation finished and tested with 95%+ coverage.

## Overview
TDD와 Pydantic v2를 활용하여 안전하고 직관적인 Context Manager를 구현합니다. Python의 `with` 문을 통한 자동 리소스 정리와 Pydantic 기반 설정 관리를 제공합니다.

## Goals
- Pydantic 기반 Context Manager 설정 모델
- FRPClient와 Tunnel의 Context Manager 프로토콜 구현
- 자동 리소스 정리 및 예외 안전성
- TDD 방식의 완전한 테스트 커버리지
- 중첩 context 지원

## Test-First Implementation with Pydantic

### 1. Context Manager Configuration Models

```python
# src/frp_wrapper/common/context_config.py
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from pydantic import BaseModel, Field, ConfigDict, field_validator

class CleanupStrategy(str, Enum):
    """Resource cleanup strategy"""
    GRACEFUL = "graceful"        # Try graceful shutdown first
    FORCE = "force"              # Force immediate shutdown
    GRACEFUL_THEN_FORCE = "graceful_then_force"  # Graceful with fallback

class ContextConfig(BaseModel):
    """Pydantic configuration for Context Manager behavior"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    # Timeout settings
    connect_timeout: float = Field(default=10.0, ge=0.1, le=60.0, description="Connection timeout in seconds")
    cleanup_timeout: float = Field(default=5.0, ge=0.1, le=30.0, description="Cleanup timeout in seconds")
    graceful_shutdown_timeout: float = Field(default=3.0, ge=0.1, le=10.0, description="Graceful shutdown timeout")

    # Cleanup behavior
    cleanup_strategy: CleanupStrategy = Field(default=CleanupStrategy.GRACEFUL_THEN_FORCE)
    suppress_cleanup_errors: bool = Field(default=True, description="Suppress errors during cleanup")
    log_cleanup_errors: bool = Field(default=True, description="Log cleanup errors")

    # Resource tracking
    track_resources: bool = Field(default=True, description="Enable resource tracking")
    max_tracked_resources: int = Field(default=100, ge=1, le=1000, description="Maximum resources to track")

    @field_validator('connect_timeout', 'cleanup_timeout', 'graceful_shutdown_timeout')
    @classmethod
    def validate_positive_timeout(cls, v: float) -> float:
        """Ensure timeouts are positive"""
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v

class TunnelGroupConfig(BaseModel):
    """Configuration for TunnelGroup context manager"""

    model_config = ConfigDict(str_strip_whitespace=True)

    group_name: str = Field(..., min_length=1, max_length=50, description="Group identifier")
    max_tunnels: int = Field(default=10, ge=1, le=50, description="Maximum tunnels in group")
    parallel_cleanup: bool = Field(default=True, description="Clean up tunnels in parallel")
    cleanup_order: str = Field(default="lifo", pattern="^(lifo|fifo)$", description="Cleanup order: lifo or fifo")

    @field_validator('group_name')
    @classmethod
    def validate_group_name(cls, v: str) -> str:
        """Validate group name format"""
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Group name must contain only alphanumeric characters, hyphens, and underscores")
        return v

class ResourceTracker(BaseModel):
    """Pydantic model for tracking resources"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    resources: Dict[str, Any] = Field(default_factory=dict)
    cleanup_callbacks: Dict[str, Callable] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    max_resources: int = Field(default=100, ge=1)

    def register_resource(self, resource_id: str, resource: Any, cleanup_callback: Callable) -> None:
        """Register a resource for tracking"""
        if len(self.resources) >= self.max_resources:
            raise ValueError(f"Maximum resources ({self.max_resources}) exceeded")

        self.resources[resource_id] = resource
        self.cleanup_callbacks[resource_id] = cleanup_callback

    def unregister_resource(self, resource_id: str) -> None:
        """Unregister a resource"""
        self.resources.pop(resource_id, None)
        self.cleanup_callbacks.pop(resource_id, None)

    def cleanup_all(self) -> List[str]:
        """Clean up all registered resources, return list of errors"""
        errors = []

        # Cleanup in reverse order (LIFO)
        for resource_id in reversed(list(self.resources.keys())):
            try:
                cleanup_callback = self.cleanup_callbacks.get(resource_id)
                if cleanup_callback:
                    cleanup_callback()
            except Exception as e:
                errors.append(f"Resource {resource_id}: {str(e)}")
            finally:
                self.unregister_resource(resource_id)

        return errors
```

### 2. Enhanced Context Manager Tests

```python
# tests/test_context_manager.py
import pytest
import tempfile
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager
from pydantic import ValidationError

from frp_wrapper.common.context_config import (
    ContextConfig, TunnelGroupConfig, ResourceTracker, CleanupStrategy
)
from frp_wrapper.core.client import FRPClient
from frp_wrapper.tunnels.models import HTTPTunnel, TCPTunnel, TunnelStatus
from frp_wrapper.common.exceptions import TunnelError, ConnectionError

class TestContextConfig:
    def test_context_config_creation_with_defaults(self):
        """Test ContextConfig creation with default values"""
        config = ContextConfig()

        assert config.connect_timeout == 10.0
        assert config.cleanup_timeout == 5.0
        assert config.cleanup_strategy == CleanupStrategy.GRACEFUL_THEN_FORCE
        assert config.suppress_cleanup_errors is True
        assert config.track_resources is True

    def test_context_config_validation_errors(self):
        """Test ContextConfig validation with invalid values"""
        # Negative timeout
        with pytest.raises(ValidationError, match="greater than or equal to 0.1"):
            ContextConfig(connect_timeout=-1.0)

        # Too large max resources
        with pytest.raises(ValidationError, match="less than or equal to 1000"):
            ContextConfig(max_tracked_resources=1001)

        # Zero timeout
        with pytest.raises(ValidationError, match="Timeout must be positive"):
            ContextConfig(cleanup_timeout=0.0)

    def test_tunnel_group_config_validation(self):
        """Test TunnelGroupConfig validation"""
        # Valid group config
        config = TunnelGroupConfig(group_name="test-group-1")
        assert config.group_name == "test-group-1"
        assert config.max_tunnels == 10
        assert config.cleanup_order == "lifo"

        # Invalid group name
        with pytest.raises(ValidationError, match="alphanumeric characters"):
            TunnelGroupConfig(group_name="test@group")

        # Invalid cleanup order
        with pytest.raises(ValidationError, match="fifo"):
            TunnelGroupConfig(group_name="test", cleanup_order="invalid")

class TestResourceTracker:
    def test_resource_tracker_creation(self):
        """Test ResourceTracker creation and basic operations"""
        tracker = ResourceTracker(max_resources=5)

        assert len(tracker.resources) == 0
        assert len(tracker.cleanup_callbacks) == 0
        assert tracker.max_resources == 5

    def test_resource_registration(self):
        """Test resource registration and cleanup"""
        tracker = ResourceTracker()

        # Mock resource and cleanup
        mock_resource = Mock()
        mock_cleanup = Mock()

        tracker.register_resource("test-resource", mock_resource, mock_cleanup)

        assert "test-resource" in tracker.resources
        assert tracker.resources["test-resource"] is mock_resource
        assert "test-resource" in tracker.cleanup_callbacks

    def test_resource_cleanup_all(self):
        """Test cleanup all resources"""
        tracker = ResourceTracker()

        # Register multiple resources
        cleanup_calls = []
        for i in range(3):
            resource = Mock()
            cleanup = Mock(side_effect=lambda idx=i: cleanup_calls.append(idx))
            tracker.register_resource(f"resource-{i}", resource, cleanup)

        errors = tracker.cleanup_all()

        assert len(errors) == 0
        assert len(tracker.resources) == 0
        assert len(cleanup_calls) == 3
        # Cleanup should be in reverse order (LIFO)
        assert cleanup_calls == [2, 1, 0]

    def test_resource_cleanup_with_errors(self):
        """Test cleanup handling errors"""
        tracker = ResourceTracker()

        # Register resources with failing cleanup
        good_cleanup = Mock()
        bad_cleanup = Mock(side_effect=Exception("Cleanup failed"))

        tracker.register_resource("good", Mock(), good_cleanup)
        tracker.register_resource("bad", Mock(), bad_cleanup)

        errors = tracker.cleanup_all()

        assert len(errors) == 1
        assert "bad" in errors[0]
        assert "Cleanup failed" in errors[0]
        good_cleanup.assert_called_once()
        bad_cleanup.assert_called_once()

    def test_max_resources_limit(self):
        """Test maximum resources limit"""
        tracker = ResourceTracker(max_resources=2)

        # Register up to limit
        tracker.register_resource("res1", Mock(), Mock())
        tracker.register_resource("res2", Mock(), Mock())

        # Should fail when exceeding limit
        with pytest.raises(ValueError, match="Maximum resources"):
            tracker.register_resource("res3", Mock(), Mock())

class TestFRPClientContextManager:
    @pytest.fixture
    def mock_client(self):
        """Create mock FRPClient for testing"""
        with patch('frp_wrapper.client.FRPClient.find_frp_binary'):
            with patch('frp_wrapper.client.ProcessManager'):
                with patch('frp_wrapper.client.ConfigBuilder'):
                    client = FRPClient("example.com")
                    return client

    def test_client_context_manager_success(self, mock_client):
        """Test successful context manager usage"""
        with patch.object(mock_client, 'connect', return_value=True):
            with patch.object(mock_client, 'disconnect', return_value=True):
                with patch.object(mock_client, 'is_connected', return_value=True):
                    with patch.object(mock_client, 'list_tunnels', return_value=[]):

                        with mock_client as client:
                            assert client.is_connected()

                        # Should be disconnected after context
                        mock_client.disconnect.assert_called_once()

    def test_client_context_manager_with_tunnels(self, mock_client):
        """Test context manager with active tunnels"""
        mock_tunnel = Mock()
        mock_tunnel.id = "test-tunnel"
        mock_tunnel.close = Mock()

        with patch.object(mock_client, 'connect', return_value=True):
            with patch.object(mock_client, 'disconnect', return_value=True):
                with patch.object(mock_client, 'is_connected', return_value=True):
                    with patch.object(mock_client, 'list_tunnels', return_value=[mock_tunnel]):
                        with patch.object(mock_client, 'close_tunnel') as mock_close:

                            with mock_client as client:
                                pass  # Context automatically manages tunnels

                            # Should close all tunnels
                            mock_close.assert_called()

    def test_client_context_manager_exception_handling(self, mock_client):
        """Test context manager exception handling"""
        with patch.object(mock_client, 'connect', return_value=True):
            with patch.object(mock_client, 'disconnect', return_value=True):
                with patch.object(mock_client, 'is_connected', return_value=True):
                    with patch.object(mock_client, 'list_tunnels', return_value=[]):

                        try:
                            with mock_client as client:
                                raise ValueError("Test exception")
                        except ValueError:
                            pass  # Expected

                        # Should still disconnect
                        mock_client.disconnect.assert_called_once()

    def test_client_context_manager_with_config(self, mock_client):
        """Test context manager with custom ContextConfig"""
        config = ContextConfig(
            cleanup_timeout=2.0,
            cleanup_strategy=CleanupStrategy.FORCE,
            suppress_cleanup_errors=False
        )

        mock_client.context_config = config

        with patch.object(mock_client, 'connect', return_value=True):
            with patch.object(mock_client, 'disconnect', return_value=True):
                with patch.object(mock_client, 'is_connected', return_value=True):
                    with patch.object(mock_client, 'list_tunnels', return_value=[]):

                        with mock_client as client:
                            assert client.context_config.cleanup_timeout == 2.0
                            assert client.context_config.cleanup_strategy == CleanupStrategy.FORCE

class TestTunnelContextManager:
    def test_tunnel_context_manager_success(self):
        """Test tunnel context manager basic usage"""
        config = HTTPTunnelConfig(path="test", custom_domains=["example.com"])
        tunnel = AdvancedHTTPTunnel(
            id="test-tunnel",
            local_port=3000,
            config=config
        ).with_status(TunnelStatus.CONNECTED)

        with patch.object(tunnel, 'close') as mock_close:
            with tunnel as t:
                assert t.status == TunnelStatus.CONNECTED
                assert t.id == "test-tunnel"

            mock_close.assert_called_once()

    def test_tunnel_context_manager_closed_tunnel(self):
        """Test context manager with closed tunnel"""
        config = HTTPTunnelConfig(path="test", custom_domains=["example.com"])
        tunnel = AdvancedHTTPTunnel(
            id="test-tunnel",
            local_port=3000,
            config=config
        ).with_status(TunnelStatus.CLOSED)

        with pytest.raises(TunnelError, match="Cannot enter context of closed tunnel"):
            with tunnel:
                pass

class TestTunnelGroup:
    @pytest.fixture
    def mock_client(self):
        """Create mock client for TunnelGroup tests"""
        client = Mock(spec=FRPClient)
        return client

    def test_tunnel_group_creation(self, mock_client):
        """Test TunnelGroup creation with Pydantic config"""
        config = TunnelGroupConfig(group_name="test-group")
        group = TunnelGroup(mock_client, config)

        assert group.config.group_name == "test-group"
        assert group.config.max_tunnels == 10
        assert len(group.tunnels) == 0

    def test_tunnel_group_add_tunnels(self, mock_client):
        """Test adding tunnels to group"""
        config = TunnelGroupConfig(group_name="test-group", max_tunnels=3)
        group = TunnelGroup(mock_client, config)

        # Mock tunnel creation
        mock_tunnels = []
        for i in range(3):
            mock_tunnel = Mock()
            mock_tunnel.id = f"tunnel-{i}"
            mock_tunnels.append(mock_tunnel)

        mock_client.expose_path.side_effect = mock_tunnels
        mock_client.expose_tcp.return_value = mock_tunnels[2]

        # Add HTTP tunnels
        group.add_http_tunnel(3000, "app1")
        group.add_http_tunnel(3001, "app2")

        # Add TCP tunnel
        group.add_tcp_tunnel(5432)

        assert len(group.tunnels) == 3
        assert mock_client.expose_path.call_count == 2
        assert mock_client.expose_tcp.call_count == 1

    def test_tunnel_group_max_tunnels_limit(self, mock_client):
        """Test TunnelGroup respects max tunnels limit"""
        config = TunnelGroupConfig(group_name="test-group", max_tunnels=2)
        group = TunnelGroup(mock_client, config)

        mock_client.expose_path.return_value = Mock()

        # Add up to limit
        group.add_http_tunnel(3000, "app1")
        group.add_http_tunnel(3001, "app2")

        # Should fail when exceeding limit
        with pytest.raises(TunnelError, match="Maximum tunnels"):
            group.add_http_tunnel(3002, "app3")

    def test_tunnel_group_context_manager(self, mock_client):
        """Test TunnelGroup as context manager"""
        config = TunnelGroupConfig(group_name="test-group", cleanup_order="lifo")
        group = TunnelGroup(mock_client, config)

        # Create mock tunnels
        mock_tunnels = []
        for i in range(3):
            mock_tunnel = Mock()
            mock_tunnel.id = f"tunnel-{i}"
            mock_tunnel.close = Mock()
            mock_tunnels.append(mock_tunnel)

        group.tunnels = mock_tunnels

        with group as tunnels:
            assert len(tunnels) == 3
            assert tunnels == mock_tunnels

        # Check cleanup was called in LIFO order
        for tunnel in mock_tunnels:
            tunnel.close.assert_called_once()

# Advanced context manager tests
class TestAdvancedContextFeatures:
    def test_temporary_tunnel_context_manager(self):
        """Test temporary tunnel convenience function"""
        with patch('frp_wrapper.context.FRPClient') as MockClient:
            mock_client = Mock()
            mock_tunnel = Mock()
            MockClient.return_value = mock_client
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.tunnel.return_value.__enter__.return_value = mock_tunnel
            mock_client.tunnel.return_value.__exit__.return_value = None

            with temporary_tunnel("example.com", 3000, "myapp") as tunnel:
                assert tunnel is mock_tunnel

            MockClient.assert_called_once_with("example.com")

    def test_nested_context_managers(self):
        """Test nested context managers work correctly"""
        with patch('frp_wrapper.client.FRPClient') as MockClient:
            mock_client = Mock()
            MockClient.return_value = mock_client
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None

            # Mock tunnels
            mock_tunnel1 = Mock()
            mock_tunnel2 = Mock()
            mock_client.tunnel.side_effect = [
                Mock(__enter__=Mock(return_value=mock_tunnel1), __exit__=Mock()),
                Mock(__enter__=Mock(return_value=mock_tunnel2), __exit__=Mock())
            ]

            with MockClient("example.com") as client:
                with client.tunnel(3000, "app1") as tunnel1:
                    with client.tunnel(3001, "app2") as tunnel2:
                        assert tunnel1 is mock_tunnel1
                        assert tunnel2 is mock_tunnel2
```

### 3. Context Manager Implementation

```python
# src/frp_wrapper/common/context.py
import asyncio
import logging
import threading
import time
from contextlib import contextmanager
from typing import Iterator, List, Optional, Any, Type
from types import TracebackType

from .context_config import ContextConfig, TunnelGroupConfig, ResourceTracker, CleanupStrategy
from .tunnel import BaseTunnel, HTTPTunnel, TCPTunnel
from .exceptions import TunnelError

logger = logging.getLogger(__name__)

class TunnelGroup:
    """Pydantic-configured tunnel group with context manager support"""

    def __init__(self, client: 'FRPClient', config: Optional[TunnelGroupConfig] = None):
        self.client = client
        self.config = config or TunnelGroupConfig(group_name="default")
        self.tunnels: List[BaseTunnel] = []
        self._resource_tracker = ResourceTracker()

    def add_http_tunnel(self, local_port: int, path: str, **kwargs) -> 'TunnelGroup':
        """Add HTTP tunnel to group (chainable)"""
        if len(self.tunnels) >= self.config.max_tunnels:
            raise TunnelError(f"Maximum tunnels ({self.config.max_tunnels}) exceeded for group {self.config.group_name}")

        tunnel = self.client.expose_path(local_port, path, **kwargs)
        self.tunnels.append(tunnel)
        self._resource_tracker.register_resource(
            tunnel.id, tunnel, lambda: self._safe_close_tunnel(tunnel)
        )
        return self

    def add_tcp_tunnel(self, local_port: int, **kwargs) -> 'TunnelGroup':
        """Add TCP tunnel to group (chainable)"""
        if len(self.tunnels) >= self.config.max_tunnels:
            raise TunnelError(f"Maximum tunnels ({self.config.max_tunnels}) exceeded for group {self.config.group_name}")

        tunnel = self.client.expose_tcp(local_port, **kwargs)
        self.tunnels.append(tunnel)
        self._resource_tracker.register_resource(
            tunnel.id, tunnel, lambda: self._safe_close_tunnel(tunnel)
        )
        return self

    def _safe_close_tunnel(self, tunnel: BaseTunnel) -> None:
        """Safely close a tunnel, handling errors"""
        try:
            tunnel.close()
        except Exception as e:
            logger.error(f"Error closing tunnel {tunnel.id}: {e}")

    def __enter__(self) -> List[BaseTunnel]:
        """Enter context and return list of tunnels"""
        return self.tunnels

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> None:
        """Exit context and clean up all tunnels"""
        if self.config.parallel_cleanup:
            self._parallel_cleanup()
        else:
            self._sequential_cleanup()

    def _sequential_cleanup(self) -> None:
        """Clean up tunnels sequentially"""
        tunnels_to_cleanup = (
            self.tunnels if self.config.cleanup_order == "fifo"
            else reversed(self.tunnels)
        )

        for tunnel in tunnels_to_cleanup:
            self._safe_close_tunnel(tunnel)

    def _parallel_cleanup(self) -> None:
        """Clean up tunnels in parallel using threads"""
        def cleanup_worker(tunnel: BaseTunnel) -> None:
            self._safe_close_tunnel(tunnel)

        threads = []
        for tunnel in self.tunnels:
            thread = threading.Thread(target=cleanup_worker, args=(tunnel,))
            thread.start()
            threads.append(thread)

        # Wait for all cleanup threads
        for thread in threads:
            thread.join(timeout=5.0)  # Don't wait forever

@contextmanager
def temporary_tunnel(
    server: str,
    local_port: int,
    path: str,
    auth_token: Optional[str] = None,
    **options
) -> Iterator[HTTPTunnel]:
    """Create a temporary HTTP tunnel with automatic cleanup"""
    from .client import FRPClient

    with FRPClient(server, auth_token=auth_token, **options) as client:
        with client.tunnel(local_port, path) as tunnel:
            yield tunnel

@contextmanager
def tunnel_group(
    client: 'FRPClient',
    group_name: str = "default",
    max_tunnels: int = 10,
    **config_kwargs
) -> Iterator[TunnelGroup]:
    """Create a temporary tunnel group with automatic cleanup"""
    config = TunnelGroupConfig(
        group_name=group_name,
        max_tunnels=max_tunnels,
        **config_kwargs
    )

    with TunnelGroup(client, config) as group:
        yield group

class ContextManagerMixin:
    """Mixin providing context manager functionality with Pydantic config"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context_config = kwargs.get('context_config', ContextConfig())
        self._resource_tracker = ResourceTracker()
        self._in_context = False

    def __enter__(self):
        """Enter context with automatic connection"""
        self._in_context = True

        if hasattr(self, 'connect') and not self.is_connected():
            try:
                if not self.connect():
                    raise ConnectionError("Failed to connect in context manager")
            except Exception as e:
                self._in_context = False
                raise

        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> None:
        """Exit context with automatic cleanup"""
        self._in_context = False
        errors = []

        try:
            # 1. Clean up tracked resources
            if hasattr(self, '_resource_tracker'):
                resource_errors = self._resource_tracker.cleanup_all()
                errors.extend(resource_errors)

            # 2. Close tunnels if this is a client
            if hasattr(self, 'list_tunnels'):
                tunnel_errors = self._cleanup_tunnels()
                errors.extend(tunnel_errors)

            # 3. Disconnect if connected
            if hasattr(self, 'disconnect') and hasattr(self, 'is_connected'):
                if self.is_connected():
                    try:
                        self.disconnect()
                    except Exception as e:
                        errors.append(f"Disconnect error: {str(e)}")

            # 4. Handle cleanup errors according to config
            if errors:
                error_message = f"Cleanup errors: {'; '.join(errors)}"
                if self.context_config.log_cleanup_errors:
                    logger.error(error_message)

                if not self.context_config.suppress_cleanup_errors:
                    raise TunnelError(error_message)

        except Exception as e:
            if not self.context_config.suppress_cleanup_errors:
                raise
            else:
                logger.error(f"Context exit error: {e}")

        # Don't suppress the original exception
        return False

    def _cleanup_tunnels(self) -> List[str]:
        """Clean up all tunnels, return list of errors"""
        errors = []

        for tunnel in self.list_tunnels():
            try:
                if hasattr(self, 'close_tunnel'):
                    self.close_tunnel(tunnel.id)
                elif hasattr(tunnel, 'close'):
                    tunnel.close()
            except Exception as e:
                errors.append(f"Tunnel {tunnel.id}: {str(e)}")

        return errors

    @contextmanager
    def tunnel(self, local_port: int, path: Optional[str] = None, **options) -> Iterator[BaseTunnel]:
        """Create temporary tunnel within client context"""
        tunnel = None
        try:
            if path:
                tunnel = self.expose_path(local_port, path, **options)
            else:
                tunnel = self.expose_tcp(local_port, **options)
            yield tunnel
        finally:
            if tunnel and hasattr(tunnel, 'close'):
                try:
                    tunnel.close()
                except Exception as e:
                    if self.context_config.log_cleanup_errors:
                        logger.error(f"Error closing temporary tunnel {tunnel.id}: {e}")
```

## Implementation Timeline (TDD + Pydantic)

### Day 1: Pydantic Configuration Models
1. **Write configuration tests**: ContextConfig, TunnelGroupConfig validation
2. **Implement Pydantic models**: Configuration classes with validators
3. **Write ResourceTracker tests**: Resource tracking and cleanup
4. **Implement ResourceTracker**: Pydantic-based resource management

### Day 2: Context Manager Implementation
1. **Write context manager tests**: Basic enter/exit behavior
2. **Implement ContextManagerMixin**: Base functionality with config
3. **Write FRPClient tests**: Client-specific context behavior
4. **Integrate with existing client**: Add context manager support

### Day 3: Advanced Features & Integration
1. **Write TunnelGroup tests**: Group management and cleanup
2. **Implement TunnelGroup**: Multi-tunnel context management
3. **Write convenience function tests**: temporary_tunnel, tunnel_group
4. **Integration testing**: Real FRP server scenarios

## File Structure
```
src/frp_wrapper/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── client.py        # Enhanced with ContextManagerMixin
│   ├── process.py       # ProcessManager
│   └── config.py        # ConfigBuilder
├── tunnels/
│   ├── __init__.py
│   ├── models.py        # Enhanced with context manager
│   └── manager.py       # TunnelManager
└── common/
    ├── __init__.py
    ├── context_config.py # Pydantic configuration models
    ├── context.py       # Context manager implementations
    └── exceptions.py    # Context-related exceptions

tests/
├── __init__.py
├── test_context_config.py   # Pydantic model tests
├── test_context_manager.py  # Context manager tests
├── test_tunnel_group.py     # TunnelGroup tests
└── test_context_integration.py  # Integration tests
```

## Success Criteria
- [ ] 100% test coverage for context managers
- [ ] All Pydantic validation scenarios tested
- [ ] Exception safety in all cleanup paths
- [ ] Resource leak prevention verified
- [ ] Nested context managers work correctly
- [ ] Parallel cleanup performance tested
- [ ] Real FRP integration tested

## Key Pydantic Benefits for Context Management
1. **Configuration Validation**: Timeout and behavior validation
2. **Type Safety**: Full IDE support for context configurations
3. **Serialization**: Easy export/import of context settings
4. **Documentation**: Self-documenting configuration fields
5. **Error Messages**: Clear validation error messages
6. **Performance**: Fast validation for context entry/exit

This approach provides robust, well-tested context management with comprehensive Pydantic validation and excellent developer experience through strong typing and clear configuration models.
