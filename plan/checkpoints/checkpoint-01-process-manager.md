# Checkpoint 1: Process Manager (TDD Approach)

## Overview
TDD를 적용하여 FRP 바이너리 프로세스를 관리하는 간단하고 안정적인 ProcessManager 클래스를 구현합니다.

## Goals
- FRP 프로세스의 생명주기 관리 (시작, 종료, 재시작)
- 프로세스 상태 모니터링
- 설정 파일 관리
- TDD 방식으로 높은 테스트 커버리지 달성

## Test-First Implementation

### 1. Test Structure
```python
# tests/test_process.py
import pytest
from unittest.mock import Mock, patch
from frp_wrapper.core.process import ProcessManager
from frp_wrapper.common.exceptions import ProcessError, BinaryNotFoundError

class TestProcessManager:
    def test_process_manager_requires_binary_path(self):
        """ProcessManager should require a valid binary path"""
        # This test fails first - implement to make it pass

    def test_process_manager_starts_frp_process(self):
        """ProcessManager should start FRP process successfully"""

    def test_process_manager_stops_frp_process(self):
        """ProcessManager should stop FRP process gracefully"""

    def test_process_manager_restarts_frp_process(self):
        """ProcessManager should restart FRP process"""

    def test_process_manager_detects_process_death(self):
        """ProcessManager should detect when process dies unexpectedly"""
```

### 2. ProcessManager Class (Test-Driven)

```python
# src/frp_wrapper/core/process.py
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional, Callable
from ..common.exceptions import ProcessError, BinaryNotFoundError

class ProcessManager:
    """Manages FRP binary process lifecycle"""

    def __init__(self, binary_path: str, config_path: str):
        """Initialize ProcessManager with binary and config paths

        Args:
            binary_path: Path to frpc binary
            config_path: Path to FRP configuration file

        Raises:
            BinaryNotFoundError: If binary doesn't exist or isn't executable
            ValueError: If paths are invalid
        """
        # TDD: Start with failing tests, implement step by step

    def start(self) -> bool:
        """Start FRP process

        Returns:
            True if started successfully, False otherwise

        Raises:
            ProcessError: If process fails to start
        """
        # Implementation driven by tests

    def stop(self) -> bool:
        """Stop FRP process gracefully

        Returns:
            True if stopped successfully, False otherwise
        """
        # Implementation driven by tests

    def restart(self) -> bool:
        """Restart FRP process

        Returns:
            True if restarted successfully, False otherwise
        """
        # Implementation driven by tests

    def is_running(self) -> bool:
        """Check if process is currently running"""
        # Implementation driven by tests

    @property
    def pid(self) -> Optional[int]:
        """Get process ID if running"""
        # Implementation driven by tests

    def wait_for_startup(self, timeout: float = 10.0) -> bool:
        """Wait for process to fully start up"""
        # Implementation driven by tests
```

### 3. Test Cases (Write These First)

```python
# tests/test_process.py
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from frp_wrapper.core.process import ProcessManager
from frp_wrapper.common.exceptions import ProcessError, BinaryNotFoundError

class TestProcessManager:

    @pytest.fixture
    def temp_binary(self):
        """Create a temporary executable file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.exe') as f:
            f.write('#!/bin/bash\necho "test binary"')
            temp_path = f.name
        os.chmod(temp_path, 0o755)
        yield temp_path
        os.unlink(temp_path)

    @pytest.fixture
    def temp_config(self):
        """Create a temporary config file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            f.write('[common]\nserver_addr = "test.example.com"')
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)

    def test_process_manager_requires_binary_path(self, temp_config):
        """ProcessManager should validate binary path"""
        with pytest.raises(BinaryNotFoundError):
            ProcessManager("/nonexistent/binary", temp_config)

    def test_process_manager_requires_config_path(self, temp_binary):
        """ProcessManager should validate config path"""
        with pytest.raises(FileNotFoundError):
            ProcessManager(temp_binary, "/nonexistent/config.toml")

    def test_process_manager_initialization_success(self, temp_binary, temp_config):
        """ProcessManager should initialize successfully with valid paths"""
        pm = ProcessManager(temp_binary, temp_config)
        assert pm.binary_path == temp_binary
        assert pm.config_path == temp_config
        assert not pm.is_running()
        assert pm.pid is None

    @patch('subprocess.Popen')
    def test_process_manager_starts_process(self, mock_popen, temp_binary, temp_config):
        """ProcessManager should start FRP process"""
        # Mock successful process start
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_process

        pm = ProcessManager(temp_binary, temp_config)
        result = pm.start()

        assert result is True
        assert pm.is_running()
        assert pm.pid == 12345
        mock_popen.assert_called_once()

    @patch('subprocess.Popen')
    def test_process_manager_handles_start_failure(self, mock_popen, temp_binary, temp_config):
        """ProcessManager should handle process start failure"""
        mock_popen.side_effect = OSError("Failed to start process")

        pm = ProcessManager(temp_binary, temp_config)

        with pytest.raises(ProcessError):
            pm.start()

        assert not pm.is_running()
        assert pm.pid is None

    @patch('subprocess.Popen')
    def test_process_manager_stops_process(self, mock_popen, temp_binary, temp_config):
        """ProcessManager should stop running process"""
        # Setup running process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.terminate.return_value = None
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        pm = ProcessManager(temp_binary, temp_config)
        pm.start()

        # Test stopping
        result = pm.stop()

        assert result is True
        assert not pm.is_running()
        mock_process.terminate.assert_called_once()

    @patch('subprocess.Popen')
    def test_process_manager_force_kills_unresponsive_process(self, mock_popen, temp_binary, temp_config):
        """ProcessManager should force kill unresponsive process"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.terminate.return_value = None
        mock_process.wait.side_effect = subprocess.TimeoutExpired("cmd", 5)
        mock_process.kill.return_value = None
        mock_popen.return_value = mock_process

        pm = ProcessManager(temp_binary, temp_config)
        pm.start()

        result = pm.stop()

        assert result is True
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    @patch('subprocess.Popen')
    def test_process_manager_restart(self, mock_popen, temp_binary, temp_config):
        """ProcessManager should restart process"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.terminate.return_value = None
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        pm = ProcessManager(temp_binary, temp_config)
        pm.start()

        result = pm.restart()

        assert result is True
        assert pm.is_running()
        # Should have called terminate (stop) and then started again
        mock_process.terminate.assert_called()

    def test_process_manager_detects_dead_process(self, temp_binary, temp_config):
        """ProcessManager should detect when process dies"""
        pm = ProcessManager(temp_binary, temp_config)

        # Simulate dead process
        with patch.object(pm, '_process') as mock_process:
            mock_process.poll.return_value = 1  # Exit code 1 = dead

            assert not pm.is_running()
            assert pm.pid is None

    @patch('subprocess.Popen')
    def test_wait_for_startup_success(self, mock_popen, temp_binary, temp_config):
        """ProcessManager should wait for successful startup"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        pm = ProcessManager(temp_binary, temp_config)
        pm.start()

        # Mock successful startup detection
        with patch.object(pm, '_check_startup_success', return_value=True):
            result = pm.wait_for_startup(timeout=1.0)
            assert result is True

    @patch('subprocess.Popen')
    def test_wait_for_startup_timeout(self, mock_popen, temp_binary, temp_config):
        """ProcessManager should timeout if startup takes too long"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        pm = ProcessManager(temp_binary, temp_config)
        pm.start()

        # Mock failed startup detection
        with patch.object(pm, '_check_startup_success', return_value=False):
            result = pm.wait_for_startup(timeout=0.1)
            assert result is False

# Integration tests (require actual FRP binary)
@pytest.mark.integration
class TestProcessManagerIntegration:

    def test_real_frp_process(self):
        """Test with real FRP binary if available"""
        # Skip if FRP not available
        frp_binary = self._find_frp_binary()
        if not frp_binary:
            pytest.skip("FRP binary not found")

        config_content = """
        [common]
        server_addr = "127.0.0.1"
        server_port = 7000
        """

        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            pm = ProcessManager(frp_binary, config_path)
            assert pm.start()
            assert pm.is_running()
            assert pm.pid is not None

            # Test restart
            old_pid = pm.pid
            assert pm.restart()
            assert pm.pid != old_pid

            # Test stop
            assert pm.stop()
            assert not pm.is_running()

        finally:
            os.unlink(config_path)

    def _find_frp_binary(self) -> Optional[str]:
        """Find FRP binary in system PATH"""
        import shutil
        return shutil.which('frpc')
```

## Implementation Timeline (TDD)

### Day 1: Core Structure
1. **Setup test environment**: pytest, coverage, fixtures
2. **Write failing tests**: Basic initialization and validation
3. **Implement minimal ProcessManager**: Just enough to pass tests
4. **Red-Green-Refactor cycle**: Each test method

### Day 2: Process Management
1. **Write tests for start/stop**: Process lifecycle management
2. **Implement process operations**: Using subprocess.Popen
3. **Write tests for error handling**: Failed starts, unresponsive processes
4. **Implement robust error handling**: Timeouts, force kills

### Day 3: Advanced Features
1. **Write tests for restart logic**: Clean restart process
2. **Implement restart functionality**: Stop + Start pattern
3. **Write tests for monitoring**: Process health detection
4. **Implement monitoring**: Polling, status checks

### Day 4: Integration & Polish
1. **Write integration tests**: Real FRP binary testing
2. **Refactor based on test feedback**: Clean up code
3. **Performance tests**: Startup time, resource usage
4. **Documentation**: Docstrings, usage examples

## File Structure
```
src/frp_wrapper/
├── __init__.py
├── core/
│   ├── __init__.py
│   └── process.py      # ProcessManager class
└── common/
    ├── __init__.py
    └── exceptions.py   # ProcessError, BinaryNotFoundError

tests/
├── __init__.py
├── test_process.py     # Unit tests
├── test_process_integration.py  # Integration tests
└── conftest.py         # Shared fixtures
```

## Success Criteria
- [ ] 100% test coverage for ProcessManager
- [ ] All tests pass consistently
- [ ] Handles process failures gracefully
- [ ] Works with real FRP binary
- [ ] Clean shutdown on exit
- [ ] Proper error messages
- [ ] Type hints and documentation

## Key Testing Principles
1. **Test First**: Write failing test before any implementation
2. **One Test, One Feature**: Each test focuses on single behavior
3. **Mock External Dependencies**: Use subprocess mocks for unit tests
4. **Integration Tests**: Separate tests with real FRP binary
5. **Edge Cases**: Test error conditions and failure modes

This TDD approach ensures robust, well-tested code while keeping the implementation simple and Pythonic.
