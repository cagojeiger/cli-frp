"""Tests for ServerManager class.

Following TDD approach - tests written first to define expected behavior.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from frp_wrapper.server.config import CompleteServerConfig, ServerConfig
from frp_wrapper.server.manager import ServerManager, ServerStatus


class TestServerStatus:
    """Test ServerStatus enum"""

    def test_server_status_values(self):
        """Test ServerStatus enum values"""
        assert ServerStatus.STOPPED.value == "stopped"
        assert ServerStatus.STARTING.value == "starting"
        assert ServerStatus.RUNNING.value == "running"
        assert ServerStatus.STOPPING.value == "stopping"
        assert ServerStatus.ERROR.value == "error"


class TestServerManager:
    """Test ServerManager class"""

    def test_server_manager_init_with_config_path(self):
        """Test ServerManager initialization with config path"""
        with tempfile.NamedTemporaryFile(suffix='.toml', delete=False) as f:
            config_path = Path(f.name)

        try:
            manager = ServerManager(config_path=str(config_path))

            assert manager.config_path == str(config_path)
            assert manager.binary_path is None
            assert manager.status == ServerStatus.STOPPED
            assert manager.pid is None

        finally:
            config_path.unlink(missing_ok=True)

    def test_server_manager_init_with_config_object(self):
        """Test ServerManager initialization with config object"""
        config = CompleteServerConfig(
            server=ServerConfig(bind_port=7001, auth_token="TestToken123!")
        )

        manager = ServerManager(config=config)

        assert manager.config == config
        assert manager.status == ServerStatus.STOPPED
        assert manager.pid is None

    def test_server_manager_init_validation(self):
        """Test ServerManager initialization validation"""
        with pytest.raises(ValueError, match="Either config_path or config must be provided"):
            ServerManager()

        config = CompleteServerConfig()
        with pytest.raises(ValueError, match="Cannot provide both config_path and config"):
            ServerManager(config_path="/tmp/test.toml", config=config)

    def test_binary_discovery(self):
        """Test FRP server binary discovery"""
        ServerManager(config=CompleteServerConfig())

        manager_custom = ServerManager(
            config=CompleteServerConfig(),
            binary_path="/custom/path/frps"
        )
        assert manager_custom.binary_path == "/custom/path/frps"

    @patch('shutil.which')
    def test_find_binary_system_path(self, mock_which):
        """Test finding binary in system PATH"""
        mock_which.return_value = "/usr/bin/frps"

        manager = ServerManager(config=CompleteServerConfig())
        binary_path = manager._find_binary()

        assert binary_path == "/usr/bin/frps"
        mock_which.assert_called_with('frps')

    @patch('shutil.which')
    @patch('pathlib.Path.exists')
    def test_find_binary_common_paths(self, mock_exists, mock_which):
        """Test finding binary in common installation paths"""
        mock_which.return_value = None
        mock_exists.return_value = True

        manager = ServerManager(config=CompleteServerConfig())
        binary_path = manager._find_binary()

        assert binary_path == "/usr/local/bin/frps"

    @patch('shutil.which')
    @patch('pathlib.Path.exists')
    @patch.dict('os.environ', {'FRP_SERVER_BINARY_PATH': '/env/path/frps'})
    def test_find_binary_environment_variable(self, mock_exists, mock_which):
        """Test finding binary via environment variable"""
        mock_which.return_value = None
        mock_exists.return_value = True

        manager = ServerManager(config=CompleteServerConfig())
        binary_path = manager._find_binary()

        assert binary_path == "/env/path/frps"

    @patch('subprocess.Popen')
    @patch('pathlib.Path.exists')
    def test_start_server_success(self, mock_exists, mock_popen):
        """Test successful server start"""
        mock_exists.return_value = True  # Binary exists
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        config = CompleteServerConfig(
            server=ServerConfig(bind_port=7001, auth_token="TestToken123!")
        )
        manager = ServerManager(config=config, binary_path="/usr/bin/frps")

        with patch.object(manager, '_is_port_in_use', return_value=True):
            result = manager.start()

        assert result is True
        assert manager.status == ServerStatus.RUNNING
        assert manager.pid == 12345
        mock_popen.assert_called_once()

    @patch('subprocess.Popen')
    def test_start_server_already_running(self, mock_popen):
        """Test starting server when already running"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        manager = ServerManager(config=CompleteServerConfig(), binary_path="/usr/bin/frps")
        manager._process = mock_process
        manager._status = ServerStatus.RUNNING

        result = manager.start()

        assert result is True
        assert manager.status == ServerStatus.RUNNING
        mock_popen.assert_not_called()

    @patch('subprocess.Popen')
    def test_start_server_binary_not_found(self, mock_popen):
        """Test server start with missing binary"""
        manager = ServerManager(config=CompleteServerConfig(), binary_path="/nonexistent/frps")

        with pytest.raises(FileNotFoundError, match="FRP server binary not found"):
            manager.start()

    def test_stop_server_not_running(self):
        """Test stopping server when not running"""
        manager = ServerManager(config=CompleteServerConfig())

        result = manager.stop()

        assert result is True
        assert manager.status == ServerStatus.STOPPED

    @patch('frp_wrapper.server.manager.time.sleep')
    @patch('frp_wrapper.server.manager.time.time')
    def test_stop_server_success(self, mock_time, mock_sleep):
        """Test successful server stop"""
        mock_time.return_value = 0.0  # Fixed time to avoid timeout logic

        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0  # Process stopped immediately
        mock_process.terminate.return_value = None
        mock_process.wait.return_value = None

        mock_temp_file = Mock()
        mock_temp_file.name = "/tmp/test_config.toml"
        mock_temp_file.close.return_value = None

        manager = ServerManager(config=CompleteServerConfig())
        manager._process = mock_process
        manager._status = ServerStatus.RUNNING
        manager._temp_config_file = mock_temp_file

        with patch('pathlib.Path.unlink') as mock_unlink:
            mock_unlink.return_value = None
            result = manager.stop(timeout=1.0)

        assert result is True
        assert manager.status == ServerStatus.STOPPED
        assert manager.pid is None
        mock_process.terminate.assert_called_once()

    @patch('time.sleep')
    def test_stop_server_force_kill(self, mock_sleep):
        """Test server stop with force kill"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Never stops gracefully
        mock_process.terminate.return_value = None
        mock_process.kill.return_value = None

        manager = ServerManager(config=CompleteServerConfig())
        manager._process = mock_process
        manager._status = ServerStatus.RUNNING

        result = manager.stop(timeout=0.1)

        assert result is True
        assert manager.status == ServerStatus.STOPPED
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    def test_restart_server(self):
        """Test server restart"""
        manager = ServerManager(config=CompleteServerConfig(), binary_path="/usr/bin/frps")

        with patch.object(manager, 'stop', return_value=True) as mock_stop, \
             patch.object(manager, 'start', return_value=True) as mock_start:

            result = manager.restart()

            assert result is True
            mock_stop.assert_called_once()
            mock_start.assert_called_once()

    def test_restart_server_stop_failed(self):
        """Test server restart when stop fails"""
        manager = ServerManager(config=CompleteServerConfig())

        with patch.object(manager, 'stop', return_value=False) as mock_stop:
            result = manager.restart()

            assert result is False
            mock_stop.assert_called_once()

    @patch('signal.SIGHUP', 1)  # Mock SIGHUP signal
    def test_reload_config_success(self):
        """Test successful config reload"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.send_signal.return_value = None

        manager = ServerManager(config=CompleteServerConfig())
        manager._process = mock_process
        manager._status = ServerStatus.RUNNING

        result = manager.reload_config()

        assert result is True
        mock_process.send_signal.assert_called_once_with(1)  # SIGHUP

    def test_reload_config_not_running(self):
        """Test config reload when server not running"""
        manager = ServerManager(config=CompleteServerConfig())

        result = manager.reload_config()

        assert result is False

    def test_is_port_in_use(self):
        """Test port usage detection"""
        manager = ServerManager(config=CompleteServerConfig())

        assert manager._is_port_in_use(65432) is False

        with patch('socket.socket') as mock_socket:
            mock_sock = Mock()
            mock_socket.return_value.__enter__.return_value = mock_sock
            mock_sock.connect_ex.return_value = 0  # Connection successful = port in use

            assert manager._is_port_in_use(80) is True

    def test_get_server_info(self):
        """Test getting server information"""
        config = CompleteServerConfig(
            server=ServerConfig(bind_port=7001, auth_token="TestToken123!")
        )
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running

        manager = ServerManager(config=config)
        manager._process = mock_process
        manager._status = ServerStatus.RUNNING

        info = manager.get_server_info()

        assert info['status'] == ServerStatus.RUNNING.value
        assert info['pid'] == 12345
        assert info['bind_port'] == 7001
        assert 'start_time' in info
        assert 'config_path' in info

    def test_context_manager_success(self):
        """Test ServerManager as context manager - success case"""
        manager = ServerManager(config=CompleteServerConfig(), binary_path="/usr/bin/frps")

        with patch.object(manager, 'start', return_value=True) as mock_start, \
             patch.object(manager, 'stop', return_value=True) as mock_stop:

            with manager:
                assert mock_start.called

            assert mock_stop.called

    def test_context_manager_start_failure(self):
        """Test ServerManager as context manager - start failure"""
        manager = ServerManager(config=CompleteServerConfig())

        with patch.object(manager, 'start', return_value=False):
            with pytest.raises(RuntimeError, match="Failed to start FRP server"):
                with manager:
                    pass

    def test_context_manager_exception_handling(self):
        """Test ServerManager context manager with exception"""
        manager = ServerManager(config=CompleteServerConfig(), binary_path="/usr/bin/frps")

        with patch.object(manager, 'start', return_value=True) as mock_start, \
             patch.object(manager, 'stop', return_value=True) as mock_stop:

            with pytest.raises(ValueError, match="test exception"):
                with manager:
                    raise ValueError("test exception")

            assert mock_start.called
            assert mock_stop.called


class TestServerManagerIntegration:
    """Integration tests for ServerManager"""

    def test_config_file_generation_and_usage(self):
        """Test generating config file and using it with ServerManager"""
        config = CompleteServerConfig(
            server=ServerConfig(
                bind_port=7001,
                auth_token="IntegrationTestToken123!",
                subdomain_host="test.example.com"
            ),
            description="Integration test configuration"
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            temp_path = Path(f.name)

        try:
            config.save_to_file(temp_path)

            manager = ServerManager(config_path=str(temp_path))

            assert manager.config_path == str(temp_path)

        finally:
            temp_path.unlink(missing_ok=True)

    def test_production_server_setup(self):
        """Test setting up a production-ready server configuration"""
        config = CompleteServerConfig(
            server=ServerConfig(
                bind_port=7000,
                vhost_http_port=80,
                vhost_https_port=443,
                auth_token="ProductionSecureToken123!",
                subdomain_host="tunnel.production.com",
                log_file="/var/log/frp/frps.log",
                max_ports_per_client=10
            ),
            description="Production server setup"
        )

        manager = ServerManager(config=config, binary_path="/usr/local/bin/frps")

        assert manager.config.server.bind_port == 7000
        assert manager.config.server.auth_token == "ProductionSecureToken123!"
        assert manager.config.server.subdomain_host == "tunnel.production.com"

        info = manager.get_server_info()
        assert info['bind_port'] == 7000
        assert info['status'] == ServerStatus.STOPPED.value

    def test_development_server_setup(self):
        """Test setting up a development server configuration"""
        config = CompleteServerConfig(
            server=ServerConfig(
                bind_port=7001,
                auth_token="DevToken123"
            ),
            description="Development server"
        )

        manager = ServerManager(config=config)

        assert manager.config.server.bind_port == 7001
        assert manager.config.server.auth_token == "DevToken123"
        assert manager.config.dashboard.enabled is False
        assert manager.config.ssl.enabled is False
