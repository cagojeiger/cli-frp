"""Unit tests for ProcessManager class."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from frp_wrapper.process import ProcessManager
from frp_wrapper.exceptions import ProcessError, BinaryNotFoundError


class TestProcessManager:
    """Test cases for ProcessManager class"""

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

    def test_process_manager_requires_executable_binary(self, temp_config):
        """ProcessManager should validate binary is a file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(BinaryNotFoundError):
                ProcessManager(temp_dir, temp_config)

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
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
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
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.terminate.return_value = None
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        pm = ProcessManager(temp_binary, temp_config)
        pm.start()

        result = pm.stop()

        assert result is True
        assert not pm.is_running()
        mock_process.terminate.assert_called_once()

    @patch('subprocess.Popen')
    def test_process_manager_force_kills_unresponsive_process(self, mock_popen, temp_binary, temp_config):
        """ProcessManager should force kill unresponsive process"""
        import subprocess
        
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
        mock_process.terminate.assert_called()

    def test_process_manager_detects_dead_process(self, temp_binary, temp_config):
        """ProcessManager should detect when process dies"""
        pm = ProcessManager(temp_binary, temp_config)

        with patch.object(pm, '_process') as mock_process:
            mock_process.poll.return_value = 1

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

        with patch.object(pm, '_check_startup_success', return_value=False):
            result = pm.wait_for_startup(timeout=0.1)
            assert result is False

    def test_wait_for_startup_not_running(self, temp_binary, temp_config):
        """ProcessManager should return False if process not running"""
        pm = ProcessManager(temp_binary, temp_config)
        result = pm.wait_for_startup(timeout=1.0)
        assert result is False

    @patch('subprocess.Popen')
    def test_start_already_running(self, mock_popen, temp_binary, temp_config):
        """ProcessManager should return True if already running"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        pm = ProcessManager(temp_binary, temp_config)
        pm.start()
        
        result = pm.start()
        assert result is True
        assert mock_popen.call_count == 1

    def test_stop_not_running(self, temp_binary, temp_config):
        """ProcessManager should return True when stopping non-running process"""
        pm = ProcessManager(temp_binary, temp_config)
        result = pm.stop()
        assert result is True

    @patch('subprocess.Popen')
    def test_stop_with_exception(self, mock_popen, temp_binary, temp_config):
        """ProcessManager should handle exceptions during stop"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.terminate.side_effect = OSError("Permission denied")
        mock_popen.return_value = mock_process

        pm = ProcessManager(temp_binary, temp_config)
        pm.start()

        result = pm.stop()
        assert result is False
        assert pm._process is None

    def test_stop_with_none_process(self, temp_binary, temp_config):
        """ProcessManager should handle stop when _process is None but is_running is False"""
        pm = ProcessManager(temp_binary, temp_config)
        pm._process = None
        
        result = pm.stop()
        assert result is True

    @patch('subprocess.Popen')
    def test_stop_with_none_process_but_running(self, mock_popen, temp_binary, temp_config):
        """ProcessManager should handle stop when _process is None but is_running returns True"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        pm = ProcessManager(temp_binary, temp_config)
        pm.start()
        
        with patch.object(pm, 'is_running', return_value=False):
            result = pm.stop()
            assert result is True

    @patch('subprocess.Popen')
    def test_check_startup_success_with_process_death(self, mock_popen, temp_binary, temp_config):
        """Test _check_startup_success when process dies during check"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.side_effect = [None, 1]
        mock_popen.return_value = mock_process

        pm = ProcessManager(temp_binary, temp_config)
        pm.start()

        result = pm._check_startup_success()
        assert result is False

    @patch('subprocess.Popen')
    def test_stop_process_none_edge_case(self, mock_popen, temp_binary, temp_config):
        """Test stop method when _process is None but is_running returns False"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        pm = ProcessManager(temp_binary, temp_config)
        pm.start()
        
        pm._process = None
        
        with patch.object(pm, 'is_running', return_value=False):
            result = pm.stop()
            assert result is True
