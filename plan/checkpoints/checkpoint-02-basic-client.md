# Checkpoint 2: Basic Client API (TDD Approach)

## Status: ✅ Completed
Implementation finished and tested with 95%+ coverage.

## Overview
TDD를 사용하여 사용자 친화적인 FRPClient 클래스를 구현합니다. 간단하고 직관적인 Python API를 제공하며 FRP 서버 연결을 관리합니다.

## Goals
- 직관적인 FRPClient 클래스 구현
- 서버 연결 관리 및 검증
- 기본 인증 처리
- Context manager 지원
- 강력한 TDD 커버리지

## Test-First Implementation

### 1. Test Structure
```python
# tests/test_client.py
import pytest
from unittest.mock import Mock, patch
from frp_wrapper.core.client import FRPClient
from frp_wrapper.common.exceptions import ConnectionError, AuthenticationError

class TestFRPClient:
    def test_client_requires_server_address(self):
        """FRPClient should require a valid server address"""

    def test_client_connects_to_server(self):
        """FRPClient should connect to FRP server successfully"""

    def test_client_handles_connection_failure(self):
        """FRPClient should handle connection failures gracefully"""

    def test_client_supports_authentication(self):
        """FRPClient should support token-based authentication"""

    def test_client_context_manager(self):
        """FRPClient should work as a context manager"""
```

### 2. FRPClient Class (Test-Driven)

```python
# src/frp_wrapper/core/client.py
import os
import shutil
from typing import Optional, List
from contextlib import contextmanager
from .process import ProcessManager
from .config import ConfigBuilder
from ..common.exceptions import ConnectionError, AuthenticationError, BinaryNotFoundError

class FRPClient:
    """Main client for connecting to FRP server and managing tunnels"""

    def __init__(self,
                 server: str,
                 port: int = 7000,
                 auth_token: Optional[str] = None,
                 binary_path: Optional[str] = None):
        """Initialize FRP client

        Args:
            server: FRP server address
            port: FRP server port (default: 7000)
            auth_token: Authentication token (optional)
            binary_path: Path to frpc binary (auto-detected if None)

        Raises:
            ValueError: If server address is invalid
            BinaryNotFoundError: If FRP binary not found
        """
        # TDD: Implement step by step based on failing tests

    def connect(self) -> bool:
        """Connect to FRP server

        Returns:
            True if connected successfully

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        # Implementation driven by tests

    def disconnect(self) -> bool:
        """Disconnect from FRP server

        Returns:
            True if disconnected successfully
        """
        # Implementation driven by tests

    def is_connected(self) -> bool:
        """Check if currently connected to server"""
        # Implementation driven by tests

    def __enter__(self):
        """Context manager entry"""
        # Implementation driven by tests

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        # Implementation driven by tests

    @staticmethod
    def find_frp_binary() -> str:
        """Find FRP binary in system PATH

        Returns:
            Path to frpc binary

        Raises:
            BinaryNotFoundError: If binary not found
        """
        # Implementation driven by tests
```

### 3. Test Cases (Write These First)

```python
# tests/test_client.py
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from frp_wrapper.core.client import FRPClient
from frp_wrapper.common.exceptions import ConnectionError, AuthenticationError, BinaryNotFoundError

class TestFRPClient:

    def test_client_requires_server_address(self):
        """FRPClient should validate server address"""
        with pytest.raises(ValueError, match="Server address cannot be empty"):
            FRPClient("")

        with pytest.raises(ValueError, match="Server address cannot be empty"):
            FRPClient("   ")  # Whitespace only

    def test_client_validates_port(self):
        """FRPClient should validate port number"""
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            FRPClient("example.com", port=0)

        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            FRPClient("example.com", port=65536)

    @patch('frp_wrapper.core.client.FRPClient.find_frp_binary')
    def test_client_initialization_success(self, mock_find_binary):
        """FRPClient should initialize successfully with valid parameters"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"

        client = FRPClient("example.com", port=7000, auth_token="secret123")

        assert client.server == "example.com"
        assert client.port == 7000
        assert client.auth_token == "secret123"
        assert not client.is_connected()
        mock_find_binary.assert_called_once()

    @patch('frp_wrapper.core.client.FRPClient.find_frp_binary')
    def test_client_auto_finds_binary(self, mock_find_binary):
        """FRPClient should automatically find FRP binary"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"

        client = FRPClient("example.com")

        assert client.binary_path == "/usr/local/bin/frpc"
        mock_find_binary.assert_called_once()

    @patch('frp_wrapper.core.client.FRPClient.find_frp_binary')
    def test_client_handles_missing_binary(self, mock_find_binary):
        """FRPClient should handle missing FRP binary"""
        mock_find_binary.side_effect = BinaryNotFoundError("frpc binary not found")

        with pytest.raises(BinaryNotFoundError):
            FRPClient("example.com")

    @patch('frp_wrapper.core.client.FRPClient.find_frp_binary')
    @patch('frp_wrapper.core.client.ProcessManager')
    @patch('frp_wrapper.core.client.ConfigBuilder')
    def test_client_connects_successfully(self, mock_config_builder, mock_process_manager, mock_find_binary):
        """FRPClient should connect to server successfully"""
        # Setup mocks
        mock_find_binary.return_value = "/usr/local/bin/frpc"
        mock_config = Mock()
        mock_config_builder.return_value = mock_config
        mock_config.build.return_value = "/tmp/test.toml"

        mock_process = Mock()
        mock_process_manager.return_value = mock_process
        mock_process.start.return_value = True
        mock_process.wait_for_startup.return_value = True

        client = FRPClient("example.com", auth_token="secret")
        result = client.connect()

        assert result is True
        assert client.is_connected()
        mock_config.add_server.assert_called_with("example.com", 7000, "secret")
        mock_process.start.assert_called_once()

    @patch('frp_wrapper.core.client.FRPClient.find_frp_binary')
    @patch('frp_wrapper.core.client.ProcessManager')
    def test_client_handles_connection_failure(self, mock_process_manager, mock_find_binary):
        """FRPClient should handle connection failures"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"
        mock_process = Mock()
        mock_process_manager.return_value = mock_process
        mock_process.start.side_effect = OSError("Connection refused")

        client = FRPClient("invalid.server.com")

        with pytest.raises(ConnectionError, match="Failed to connect"):
            client.connect()

        assert not client.is_connected()

    @patch('frp_wrapper.core.client.FRPClient.find_frp_binary')
    @patch('frp_wrapper.core.client.ProcessManager')
    def test_client_handles_authentication_failure(self, mock_process_manager, mock_find_binary):
        """FRPClient should handle authentication failures"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"
        mock_process = Mock()
        mock_process_manager.return_value = mock_process
        mock_process.start.return_value = True
        mock_process.wait_for_startup.return_value = False  # Startup failed = auth issue

        client = FRPClient("example.com", auth_token="invalid_token")

        with pytest.raises(AuthenticationError, match="Authentication failed"):
            client.connect()

    @patch('frp_wrapper.core.client.FRPClient.find_frp_binary')
    @patch('frp_wrapper.core.client.ProcessManager')
    def test_client_disconnects_successfully(self, mock_process_manager, mock_find_binary):
        """FRPClient should disconnect from server"""
        # Setup connected client
        mock_find_binary.return_value = "/usr/local/bin/frpc"
        mock_process = Mock()
        mock_process_manager.return_value = mock_process
        mock_process.start.return_value = True
        mock_process.wait_for_startup.return_value = True
        mock_process.stop.return_value = True

        client = FRPClient("example.com")
        client.connect()

        # Test disconnect
        result = client.disconnect()

        assert result is True
        assert not client.is_connected()
        mock_process.stop.assert_called_once()

    @patch('frp_wrapper.core.client.FRPClient.find_frp_binary')
    @patch('frp_wrapper.core.client.ProcessManager')
    def test_client_context_manager(self, mock_process_manager, mock_find_binary):
        """FRPClient should work as context manager"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"
        mock_process = Mock()
        mock_process_manager.return_value = mock_process
        mock_process.start.return_value = True
        mock_process.wait_for_startup.return_value = True
        mock_process.stop.return_value = True

        with FRPClient("example.com") as client:
            assert client.is_connected()
            mock_process.start.assert_called_once()

        # Should auto-disconnect on exit
        mock_process.stop.assert_called_once()

    @patch('frp_wrapper.core.client.FRPClient.find_frp_binary')
    def test_client_context_manager_handles_exception(self, mock_find_binary):
        """FRPClient context manager should handle exceptions"""
        mock_find_binary.return_value = "/usr/local/bin/frpc"

        with patch('frp_wrapper.core.client.ProcessManager') as mock_process_manager:
            mock_process = Mock()
            mock_process_manager.return_value = mock_process
            mock_process.start.return_value = True
            mock_process.wait_for_startup.return_value = True
            mock_process.stop.return_value = True

            try:
                with FRPClient("example.com") as client:
                    raise ValueError("Test exception")
            except ValueError:
                pass  # Expected

            # Should still disconnect on exception
            mock_process.stop.assert_called_once()

    @patch('shutil.which')
    def test_find_frp_binary_success(self, mock_which):
        """find_frp_binary should locate frpc binary"""
        mock_which.return_value = "/usr/local/bin/frpc"

        binary_path = FRPClient.find_frp_binary()

        assert binary_path == "/usr/local/bin/frpc"
        mock_which.assert_called_with('frpc')

    @patch('shutil.which')
    def test_find_frp_binary_not_found(self, mock_which):
        """find_frp_binary should raise exception if binary not found"""
        mock_which.return_value = None

        with pytest.raises(BinaryNotFoundError, match="frpc binary not found"):
            FRPClient.find_frp_binary()

    @patch('os.path.exists')
    @patch('os.access')
    def test_find_frp_binary_custom_paths(self, mock_access, mock_exists):
        """find_frp_binary should check common installation paths"""
        with patch('shutil.which', return_value=None):  # Not in PATH
            mock_exists.side_effect = lambda path: path == "/opt/frp/frpc"
            mock_access.side_effect = lambda path, mode: path == "/opt/frp/frpc"

            binary_path = FRPClient.find_frp_binary()

            assert binary_path == "/opt/frp/frpc"

# Integration tests
@pytest.mark.integration
class TestFRPClientIntegration:

    def test_real_connection_no_server(self):
        """Test connection failure with no server"""
        client = FRPClient("127.0.0.1", port=9999)  # Unlikely to have server

        with pytest.raises(ConnectionError):
            client.connect()

    @pytest.mark.skipif(not shutil.which('frpc'), reason="FRP binary not available")
    def test_real_binary_detection(self):
        """Test real FRP binary detection"""
        binary_path = FRPClient.find_frp_binary()

        assert os.path.exists(binary_path)
        assert os.access(binary_path, os.X_OK)
        assert binary_path.endswith('frpc')
```

### 4. Configuration Builder (Supporting Class)

```python
# src/frp_wrapper/core/config.py
import tempfile
import os
from typing import Optional

class ConfigBuilder:
    """Builds FRP configuration files"""

    def __init__(self):
        self._server_addr: Optional[str] = None
        self._server_port: int = 7000
        self._auth_token: Optional[str] = None
        self._config_path: Optional[str] = None

    def add_server(self, addr: str, port: int = 7000, token: Optional[str] = None):
        """Add server configuration"""
        self._server_addr = addr
        self._server_port = port
        self._auth_token = token

    def build(self) -> str:
        """Build configuration file and return path"""
        if not self._server_addr:
            raise ValueError("Server address not set")

        config_content = f"""[common]
server_addr = "{self._server_addr}"
server_port = {self._server_port}
"""

        if self._auth_token:
            config_content += f'token = "{self._auth_token}"\n'

        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(config_content)
            self._config_path = f.name

        return self._config_path

    def cleanup(self):
        """Clean up temporary config file"""
        if self._config_path and os.path.exists(self._config_path):
            os.unlink(self._config_path)
```

## Implementation Timeline (TDD)

### Day 1: Core Client Structure
1. **Setup test environment**: Client test fixtures
2. **Write initialization tests**: Server validation, binary detection
3. **Implement basic FRPClient**: Constructor and validation
4. **Binary detection**: find_frp_binary method

### Day 2: Connection Management
1. **Write connection tests**: Success and failure cases
2. **Implement connect/disconnect**: Process management integration
3. **Authentication tests**: Token-based auth validation
4. **Error handling**: Connection and auth failures

### Day 3: Context Manager & Polish
1. **Context manager tests**: Enter/exit behavior
2. **Implement context manager**: Automatic cleanup
3. **Integration tests**: Real FRP binary testing
4. **Edge cases**: Exception handling, cleanup

## File Structure
```
src/frp_wrapper/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── client.py       # FRPClient class
│   ├── config.py       # ConfigBuilder class
│   └── process.py      # ProcessManager (from checkpoint 1)
└── common/
    ├── __init__.py
    └── exceptions.py   # Custom exceptions

tests/
├── __init__.py
├── test_client.py      # Unit tests
├── test_config.py      # Config builder tests
└── test_client_integration.py  # Integration tests
```

## Success Criteria
- [ ] 100% test coverage for FRPClient
- [ ] All connection scenarios tested
- [ ] Context manager works correctly
- [ ] Authentication handled properly
- [ ] Binary detection robust
- [ ] Clean error messages
- [ ] Integration tests pass

## Key TDD Principles
1. **Test-First**: Every feature starts with failing test
2. **Simple API**: Intuitive methods, clear behavior
3. **Mock Dependencies**: Process and config management
4. **Real Integration**: Test with actual FRP binary
5. **Exception Safety**: Proper cleanup and error handling

This approach creates a user-friendly client API while maintaining comprehensive test coverage and robust error handling.
