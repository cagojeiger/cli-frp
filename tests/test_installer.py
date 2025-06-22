"""Tests for server installer functionality."""

import pytest
import tempfile
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock, call
from pydantic import ValidationError

from frp_wrapper.server.installer import ServerInstaller, InstallationConfig
from frp_wrapper.server.config import CompleteServerConfig, ServerConfig, DashboardConfig, SSLConfig


class TestInstallationConfig:
    """Test InstallationConfig model."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = InstallationConfig()
        assert config.install_dir == Path("/opt/frp-server")
        assert config.binary_name == "frps"
        assert config.config_file == "frps.toml"
        assert config.service_name == "frp-server"
        assert config.user == "frp"
        assert config.group == "frp"
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = InstallationConfig(
            install_dir=Path("/custom/path"),
            binary_name="custom-frps",
            config_file="custom.toml",
            service_name="custom-service",
            user="custom-user",
            group="custom-group"
        )
        assert config.install_dir == Path("/custom/path")
        assert config.binary_name == "custom-frps"
        assert config.config_file == "custom.toml"
        assert config.service_name == "custom-service"
        assert config.user == "custom-user"
        assert config.group == "custom-group"
    
    def test_relative_path_validation(self):
        """Test that relative paths are rejected."""
        with pytest.raises(ValidationError, match="Installation directory must be an absolute path"):
            InstallationConfig(install_dir=Path("relative/path"))
    
    def test_string_stripping(self):
        """Test that string fields are stripped of whitespace."""
        config = InstallationConfig(
            binary_name="  frps  ",
            service_name="  frp-server  ",
            user="  frp  "
        )
        assert config.binary_name == "frps"
        assert config.service_name == "frp-server"
        assert config.user == "frp"


class TestServerInstaller:
    """Test ServerInstaller functionality."""
    
    def test_installer_initialization_default(self):
        """Test installer initialization with default config."""
        installer = ServerInstaller()
        assert installer.config is not None
        assert isinstance(installer.config, InstallationConfig)
        assert installer.config.install_dir == Path("/opt/frp-server")
    
    def test_installer_initialization_custom(self):
        """Test installer initialization with custom config."""
        custom_config = InstallationConfig(install_dir=Path("/custom/path"))
        installer = ServerInstaller(custom_config)
        assert installer.config == custom_config
        assert installer.config.install_dir == Path("/custom/path")
    
    def test_get_system_info_linux_amd64(self):
        """Test system info detection for Linux AMD64."""
        installer = ServerInstaller()
        
        with patch('platform.system', return_value='Linux'), \
             patch('platform.machine', return_value='x86_64'):
            info = installer.get_system_info()
            assert info['os'] == 'linux'
            assert info['arch'] == 'amd64'
    
    def test_get_system_info_darwin_arm64(self):
        """Test system info detection for macOS ARM64."""
        installer = ServerInstaller()
        
        with patch('platform.system', return_value='Darwin'), \
             patch('platform.machine', return_value='arm64'):
            info = installer.get_system_info()
            assert info['os'] == 'darwin'
            assert info['arch'] == 'arm64'
    
    def test_get_system_info_windows_386(self):
        """Test system info detection for Windows 386."""
        installer = ServerInstaller()
        
        with patch('platform.system', return_value='Windows'), \
             patch('platform.machine', return_value='i386'):
            info = installer.get_system_info()
            assert info['os'] == 'windows'
            assert info['arch'] == '386'
    
    def test_get_system_info_unknown_defaults(self):
        """Test system info detection with unknown values defaults to Linux AMD64."""
        installer = ServerInstaller()
        
        with patch('platform.system', return_value='UnknownOS'), \
             patch('platform.machine', return_value='unknown_arch'):
            info = installer.get_system_info()
            assert info['os'] == 'linux'
            assert info['arch'] == 'amd64'
    
    def test_get_download_url_latest(self):
        """Test download URL generation for latest version."""
        installer = ServerInstaller()
        
        with patch.object(installer, 'get_system_info', return_value={'os': 'linux', 'arch': 'amd64'}):
            url = installer.get_download_url("latest")
            assert "frp_0.52.3_linux_amd64.tar.gz" in url
            assert "github.com/fatedier/frp/releases/download/v0.52.3/" in url
    
    def test_get_download_url_specific_version(self):
        """Test download URL generation for specific version."""
        installer = ServerInstaller()
        
        with patch.object(installer, 'get_system_info', return_value={'os': 'darwin', 'arch': 'arm64'}):
            url = installer.get_download_url("0.51.0")
            assert "frp_0.51.0_darwin_arm64.tar.gz" in url
            assert "github.com/fatedier/frp/releases/download/v0.51.0/" in url
    
    def test_get_download_url_version_with_v_prefix(self):
        """Test download URL generation with version having 'v' prefix."""
        installer = ServerInstaller()
        
        with patch.object(installer, 'get_system_info', return_value={'os': 'linux', 'arch': 'amd64'}):
            url = installer.get_download_url("v0.50.0")
            assert "frp_0.50.0_linux_amd64.tar.gz" in url
            assert "github.com/fatedier/frp/releases/download/v0.50.0/" in url
    
    @patch('frp_wrapper.server.installer.urlretrieve')
    @patch('frp_wrapper.server.installer.subprocess.run')
    @patch('frp_wrapper.server.installer.tempfile.TemporaryDirectory')
    @patch('frp_wrapper.server.installer.shutil.copy2')
    def test_download_frp_binary_success(self, mock_copy, mock_temp_dir, mock_subprocess, mock_urlretrieve):
        """Test successful FRP binary download."""
        installer = ServerInstaller()
        
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/test"
        
        with patch('frp_wrapper.server.installer.Path') as mock_path_class:
            mock_temp_path = Mock()
            mock_extract_dir = Mock()
            mock_extract_dir.mkdir = Mock()
            
            mock_frps_dir = Mock()
            mock_frps_binary = Mock()
            mock_frps_binary.exists.return_value = True
            mock_frps_dir.__truediv__.return_value = mock_frps_binary
            mock_extract_dir.iterdir.return_value = [mock_frps_dir]
            
            mock_temp_path.__truediv__.side_effect = lambda x: {
                "frp.tar.gz": Mock(),
                "extracted": mock_extract_dir,
                "frps": Mock()
            }.get(x, Mock())
            
            mock_path_class.return_value = mock_temp_path
            
            result = installer.download_frp_binary("0.52.3")
            
            mock_urlretrieve.assert_called_once()
            mock_subprocess.assert_called_once()
            assert result is not None
    
    @patch('frp_wrapper.server.installer.urlretrieve')
    @patch('frp_wrapper.server.installer.subprocess.run')
    @patch('frp_wrapper.server.installer.tempfile.TemporaryDirectory')
    def test_download_frp_binary_not_found(self, mock_temp_dir, mock_subprocess, mock_urlretrieve):
        """Test FRP binary download when binary not found in archive."""
        installer = ServerInstaller()
        
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/test"
        
        with patch('frp_wrapper.server.installer.Path') as mock_path_class:
            mock_temp_path = mock_path_class.return_value
            mock_extract_dir = Mock()
            mock_extract_dir.mkdir = Mock()
            mock_extract_dir.iterdir.return_value = []  # No directories found
            
            mock_temp_path.__truediv__.side_effect = lambda x: {
                "frp.tar.gz": Mock(),
                "extracted": mock_extract_dir
            }.get(x, Mock())
            
            with pytest.raises(FileNotFoundError, match="frps binary not found in downloaded archive"):
                installer.download_frp_binary("0.52.3")
    
    @patch('frp_wrapper.server.installer.shutil.copy2')
    @patch('frp_wrapper.server.installer.stat.S_IEXEC', 0o111)
    def test_install_binary_success(self, mock_copy):
        """Test successful binary installation."""
        installer = ServerInstaller()
        binary_path = Path("/tmp/frps")
        
        with patch('frp_wrapper.server.installer.Path') as mock_path_class:
            
            mock_target = Mock()
            mock_target.stat.return_value.st_mode = 0o644
            mock_target.chmod = Mock()
            
            mock_symlink = Mock()
            mock_symlink.exists.return_value = False
            mock_symlink.symlink_to = Mock()
            
            mock_path_class.side_effect = lambda x: {
                "/usr/local/bin": Mock(__truediv__=Mock(return_value=mock_symlink))
            }.get(str(x), mock_target if "frps" in str(x) else Mock())
            
            with patch.object(installer.config.install_dir, 'mkdir') as mock_mkdir:
                result = installer.install_binary(binary_path)
                
                assert result is True
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
            mock_copy.assert_called_once()
            mock_target.chmod.assert_called_once()
            mock_symlink.symlink_to.assert_called_once()
    
    @patch('frp_wrapper.server.installer.shutil.copy2', side_effect=PermissionError("Access denied"))
    def test_install_binary_permission_error(self, mock_copy):
        """Test binary installation with permission error."""
        installer = ServerInstaller()
        binary_path = Path("/tmp/frps")
        
        with patch.object(installer.config.install_dir, 'mkdir') as mock_mkdir:
            with pytest.raises(RuntimeError, match="Failed to install binary"):
                installer.install_binary(binary_path)
    
    @patch('frp_wrapper.server.installer.subprocess.run')
    def test_create_service_file_success(self, mock_subprocess):
        """Test successful service file creation."""
        installer = ServerInstaller()
        config_path = Path("/opt/frp-server/config/frps.toml")
        
        with patch('frp_wrapper.server.installer.Path') as mock_path_class:
            mock_service_file = Mock()
            mock_service_file.write_text = Mock()
            mock_path_class.return_value = mock_service_file
            
            result = installer.create_service_file(config_path)
            
            assert result is True
            mock_service_file.write_text.assert_called_once()
            mock_subprocess.assert_called_once_with(["systemctl", "daemon-reload"], check=True)
    
    @patch('frp_wrapper.server.installer.subprocess.run', side_effect=subprocess.CalledProcessError(1, "systemctl"))
    def test_create_service_file_subprocess_error(self, mock_subprocess):
        """Test service file creation with subprocess error."""
        installer = ServerInstaller()
        
        with patch('frp_wrapper.server.installer.Path') as mock_path_class:
            mock_service_file = Mock()
            mock_service_file.write_text = Mock()
            mock_path_class.return_value = mock_service_file
            
            with pytest.raises(RuntimeError, match="Failed to create service file"):
                installer.create_service_file()
    
    @patch('frp_wrapper.server.installer.subprocess.run')
    def test_create_user_and_group_success(self, mock_subprocess):
        """Test successful user and group creation."""
        installer = ServerInstaller()
        
        result = installer.create_user_and_group()
        
        assert result is True
        assert mock_subprocess.call_count == 2  # groupadd and useradd
        
        groupadd_call = call(["groupadd", "--system", "frp"], check=False)
        assert groupadd_call in mock_subprocess.call_args_list
        
        useradd_call = call([
            "useradd", "--system", "--gid", "frp",
            "--home-dir", "/opt/frp-server",
            "--shell", "/bin/false",
            "--comment", "FRP Server",
            "frp"
        ], check=False)
        assert useradd_call in mock_subprocess.call_args_list
    
    @patch('frp_wrapper.server.installer.subprocess.run', side_effect=subprocess.CalledProcessError(1, "useradd"))
    def test_create_user_and_group_error(self, mock_subprocess):
        """Test user and group creation with error."""
        installer = ServerInstaller()
        
        with pytest.raises(RuntimeError, match="Failed to create user/group"):
            installer.create_user_and_group()
    
    @patch('frp_wrapper.server.installer.shutil.chown')
    def test_setup_directories_success(self, mock_chown):
        """Test successful directory setup."""
        installer = ServerInstaller()
        
        with patch('frp_wrapper.server.installer.Path') as mock_path_class:
            mock_dir = Mock()
            mock_dir.mkdir = Mock()
            mock_path_class.return_value = mock_dir
            
            with patch.object(installer.config.install_dir, 'mkdir') as mock_install_mkdir, \
                 patch.object(installer.config.install_dir, '__truediv__', return_value=mock_dir) as mock_truediv:
                
                result = installer.setup_directories()
                
                assert result is True
                assert mock_dir.mkdir.call_count >= 3  # logs, config, /var/log/frp-server
    
    @patch('frp_wrapper.server.installer.shutil.chown', side_effect=OSError("Permission denied"))
    def test_setup_directories_chown_error_ignored(self, mock_chown):
        """Test directory setup ignores chown errors."""
        installer = ServerInstaller()
        
        with patch('frp_wrapper.server.installer.Path') as mock_path_class:
            mock_dir = Mock()
            mock_dir.mkdir = Mock()
            mock_path_class.return_value = mock_dir
            
            with patch.object(installer.config.install_dir, 'mkdir') as mock_install_mkdir, \
                 patch.object(installer.config.install_dir, '__truediv__', return_value=mock_dir) as mock_truediv:
                
                result = installer.setup_directories()
                assert result is True
    
    @patch('frp_wrapper.server.installer.shutil.chown')
    def test_install_configuration_success(self, mock_chown):
        """Test successful configuration installation."""
        installer = ServerInstaller()
        server_config = CompleteServerConfig()
        
        with patch.object(CompleteServerConfig, 'save_to_file') as mock_save:
            result = installer.install_configuration(server_config)
            
            assert isinstance(result, Path)
            mock_save.assert_called_once()
    
    def test_install_configuration_save_error(self):
        """Test configuration installation with save error."""
        installer = ServerInstaller()
        server_config = CompleteServerConfig()
        
        with patch.object(CompleteServerConfig, 'save_to_file', side_effect=OSError("Write failed")):
            with pytest.raises(RuntimeError, match="Failed to install configuration"):
                installer.install_configuration(server_config)
    
    @patch.object(ServerInstaller, 'setup_directories')
    @patch.object(ServerInstaller, 'create_user_and_group')
    @patch.object(ServerInstaller, 'download_frp_binary')
    @patch.object(ServerInstaller, 'install_binary')
    @patch.object(ServerInstaller, 'install_configuration')
    @patch.object(ServerInstaller, 'create_service_file')
    def test_full_installation_success(self, mock_service, mock_config, mock_install, 
                                     mock_download, mock_user, mock_dirs):
        """Test successful full installation."""
        installer = ServerInstaller()
        server_config = CompleteServerConfig()
        
        mock_dirs.return_value = True
        mock_user.return_value = True
        mock_download.return_value = Path("/tmp/frps")
        mock_install.return_value = True
        mock_config.return_value = Path("/opt/frp-server/config/frps.toml")
        mock_service.return_value = True
        
        result = installer.full_installation(server_config, "0.52.3")
        
        assert result["success"] is True
        assert len(result["steps_completed"]) == 6
        assert "config_path" in result
        assert "service_name" in result
        assert "install_dir" in result
        
        mock_dirs.assert_called_once()
        mock_user.assert_called_once()
        mock_download.assert_called_once_with("0.52.3")
        mock_install.assert_called_once()
        mock_config.assert_called_once()
        mock_service.assert_called_once()
    
    @patch.object(ServerInstaller, 'setup_directories', side_effect=RuntimeError("Setup failed"))
    def test_full_installation_failure(self, mock_dirs):
        """Test full installation with failure."""
        installer = ServerInstaller()
        server_config = CompleteServerConfig()
        
        result = installer.full_installation(server_config)
        
        assert result["success"] is False
        assert "error" in result
        assert "Setup failed" in result["error"]
        assert len(result["steps_completed"]) == 0
    
    @patch('frp_wrapper.server.installer.subprocess.run')
    @patch('frp_wrapper.server.installer.shutil.rmtree')
    def test_uninstall_success(self, mock_rmtree, mock_subprocess):
        """Test successful uninstallation."""
        installer = ServerInstaller()
        
        with patch('frp_wrapper.server.installer.Path') as mock_path_class:
            mock_service_file = Mock()
            mock_service_file.exists.return_value = True
            mock_service_file.unlink = Mock()
            
            mock_symlink = Mock()
            mock_symlink.exists.return_value = True
            mock_symlink.unlink = Mock()
            
            mock_path_class.side_effect = lambda x: {
                "/etc/systemd/system/frp-server.service": mock_service_file,
                "/usr/local/bin/frps": mock_symlink,
                "/var/log/frp-server": Mock(exists=Mock(return_value=True))
            }.get(str(x), Mock())
            
            with patch.object(installer.config.install_dir, 'exists', return_value=True) as mock_exists:
                result = installer.uninstall()
                
                assert result is True
                assert mock_subprocess.call_count >= 3  # stop, disable, daemon-reload
                mock_service_file.unlink.assert_called_once()
                mock_symlink.unlink.assert_called_once()
                assert mock_rmtree.call_count >= 1
    
    @patch('frp_wrapper.server.installer.subprocess.run', side_effect=subprocess.CalledProcessError(1, "systemctl"))
    def test_uninstall_subprocess_error(self, mock_subprocess):
        """Test uninstallation with subprocess error."""
        installer = ServerInstaller()
        
        with pytest.raises(RuntimeError, match="Failed to uninstall"):
            installer.uninstall()


class TestInstallationIntegration:
    """Integration tests for installation functionality."""
    
    def test_installation_config_with_installer(self):
        """Test that InstallationConfig works properly with ServerInstaller."""
        config = InstallationConfig(
            install_dir=Path("/custom/frp"),
            service_name="custom-frp"
        )
        installer = ServerInstaller(config)
        
        assert installer.config.install_dir == Path("/custom/frp")
        assert installer.config.service_name == "custom-frp"
    
    def test_system_info_affects_download_url(self):
        """Test that system info properly affects download URL generation."""
        installer = ServerInstaller()
        
        with patch.object(installer, 'get_system_info', return_value={'os': 'windows', 'arch': '386'}):
            url = installer.get_download_url("0.52.3")
            assert "windows_386" in url
        
        with patch.object(installer, 'get_system_info', return_value={'os': 'darwin', 'arch': 'arm64'}):
            url = installer.get_download_url("0.52.3")
            assert "darwin_arm64" in url
