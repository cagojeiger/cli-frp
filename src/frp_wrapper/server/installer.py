"""Installation utilities for FRP server setup.

This module provides comprehensive installation and setup utilities for FRP server
deployment, including binary management, service configuration, and system setup.
"""

import platform
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import CompleteServerConfig


class InstallationConfig(BaseModel):
    """Configuration for FRP server installation."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    install_dir: Path = Field(default=Path("/opt/frp-server"), description="Installation directory")
    binary_name: str = Field(default="frps", description="Binary executable name")
    config_file: str = Field(default="frps.toml", description="Configuration file name")
    service_name: str = Field(default="frp-server", description="Systemd service name")
    user: str = Field(default="frp", description="Service user account")
    group: str = Field(default="frp", description="Service group")

    @field_validator('install_dir')
    @classmethod
    def validate_install_dir(cls, v: Path) -> Path:
        """Validate installation directory path."""
        if not v.is_absolute():
            raise ValueError("Installation directory must be an absolute path")
        return v


class ServerInstaller:
    """Handles FRP server installation and setup."""

    def __init__(self, config: InstallationConfig | None = None):
        self.config = config or InstallationConfig()
        self._frp_releases_url = "https://api.github.com/repos/fatedier/frp/releases"

    def get_system_info(self) -> dict[str, str]:
        """Get system architecture and OS information."""
        system = platform.system().lower()
        machine = platform.machine().lower()

        arch_mapping = {
            'x86_64': 'amd64',
            'amd64': 'amd64',
            'i386': '386',
            'i686': '386',
            'armv7l': 'arm',
            'aarch64': 'arm64',
            'arm64': 'arm64'
        }

        os_mapping = {
            'linux': 'linux',
            'darwin': 'darwin',
            'windows': 'windows'
        }

        return {
            'os': os_mapping.get(system, 'linux'),
            'arch': arch_mapping.get(machine, 'amd64')
        }

    def get_download_url(self, version: str = "latest") -> str:
        """Get download URL for FRP binary."""
        system_info = self.get_system_info()

        if version == "latest":
            version = "0.52.3"  # Default to known stable version

        version = version.lstrip('v')

        filename = f"frp_{version}_{system_info['os']}_{system_info['arch']}.tar.gz"
        return f"https://github.com/fatedier/frp/releases/download/v{version}/{filename}"

    def download_frp_binary(self, version: str = "latest") -> Path:
        """Download FRP server binary."""
        download_url = self.get_download_url(version)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            archive_path = temp_path / "frp.tar.gz"

            urlretrieve(download_url, archive_path)

            extract_dir = temp_path / "extracted"
            extract_dir.mkdir()

            subprocess.run([
                "tar", "-xzf", str(archive_path), "-C", str(extract_dir)
            ], check=True)

            for item in extract_dir.iterdir():
                if item.is_dir():
                    frps_binary = item / "frps"
                    if frps_binary.exists():
                        final_path = temp_path / "frps"
                        shutil.copy2(frps_binary, final_path)
                        return final_path

            raise FileNotFoundError("frps binary not found in downloaded archive")

    def install_binary(self, binary_path: Path) -> bool:
        """Install FRP binary to system location."""
        try:
            self.config.install_dir.mkdir(parents=True, exist_ok=True)

            target_path = self.config.install_dir / self.config.binary_name
            shutil.copy2(binary_path, target_path)

            target_path.chmod(target_path.stat().st_mode | stat.S_IEXEC)

            symlink_path = Path("/usr/local/bin") / self.config.binary_name
            if symlink_path.exists():
                symlink_path.unlink()

            symlink_path.symlink_to(target_path)

            return True

        except (OSError, PermissionError) as e:
            raise RuntimeError(f"Failed to install binary: {e}") from e

    def create_service_file(self, config_path: Path | None = None) -> bool:
        """Create systemd service file for FRP server."""
        if config_path is None:
            config_path = self.config.install_dir / self.config.config_file

        service_content = f"""[Unit]
Description=FRP Server
After=network.target
Wants=network.target

[Service]
Type=simple
User={self.config.user}
Group={self.config.group}
ExecStart={self.config.install_dir / self.config.binary_name} -c {config_path}
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

        try:
            service_file_path = Path(f"/etc/systemd/system/{self.config.service_name}.service")
            service_file_path.write_text(service_content, encoding='utf-8')

            subprocess.run(["systemctl", "daemon-reload"], check=True)

            return True

        except (OSError, PermissionError, subprocess.CalledProcessError) as e:
            raise RuntimeError(f"Failed to create service file: {e}") from e

    def create_user_and_group(self) -> bool:
        """Create system user and group for FRP service."""
        try:
            subprocess.run([
                "groupadd", "--system", self.config.group
            ], check=False)  # Don't fail if group already exists

            subprocess.run([
                "useradd", "--system", "--gid", self.config.group,
                "--home-dir", str(self.config.install_dir),
                "--shell", "/bin/false",
                "--comment", "FRP Server",
                self.config.user
            ], check=False)  # Don't fail if user already exists

            return True

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create user/group: {e}") from e

    def setup_directories(self) -> bool:
        """Create necessary directories for FRP server."""
        try:
            directories = [
                self.config.install_dir,
                self.config.install_dir / "logs",
                self.config.install_dir / "config",
                Path("/var/log/frp-server")
            ]

            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)

                try:
                    shutil.chown(directory, user=self.config.user, group=self.config.group)
                except (OSError, LookupError):
                    pass  # User/group might not exist yet

            return True

        except OSError as e:
            raise RuntimeError(f"Failed to setup directories: {e}") from e

    def install_configuration(self, server_config: CompleteServerConfig) -> Path:
        """Install server configuration file."""
        config_path = self.config.install_dir / "config" / self.config.config_file

        try:
            server_config.save_to_file(config_path)

            try:
                shutil.chown(config_path, user=self.config.user, group=self.config.group)
            except (OSError, LookupError):
                pass

            return config_path

        except OSError as e:
            raise RuntimeError(f"Failed to install configuration: {e}") from e

    def full_installation(self, server_config: CompleteServerConfig, version: str = "latest") -> dict[str, Any]:
        """Perform complete FRP server installation."""
        installation_steps = []

        try:
            self.setup_directories()
            installation_steps.append("directories_created")

            self.create_user_and_group()
            installation_steps.append("user_created")

            binary_path = self.download_frp_binary(version)
            installation_steps.append("binary_downloaded")

            self.install_binary(binary_path)
            installation_steps.append("binary_installed")

            config_path = self.install_configuration(server_config)
            installation_steps.append("config_installed")

            self.create_service_file(config_path)
            installation_steps.append("service_created")

            return {
                "success": True,
                "steps_completed": installation_steps,
                "config_path": str(config_path),
                "service_name": self.config.service_name,
                "install_dir": str(self.config.install_dir)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "steps_completed": installation_steps
            }

    def uninstall(self) -> bool:
        """Uninstall FRP server completely."""
        try:
            subprocess.run(["systemctl", "stop", self.config.service_name], check=False)
            subprocess.run(["systemctl", "disable", self.config.service_name], check=False)

            service_file = Path(f"/etc/systemd/system/{self.config.service_name}.service")
            if service_file.exists():
                service_file.unlink()

            symlink_path = Path("/usr/local/bin") / self.config.binary_name
            if symlink_path.exists():
                symlink_path.unlink()

            if self.config.install_dir.exists():
                shutil.rmtree(self.config.install_dir)

            log_dir = Path("/var/log/frp-server")
            if log_dir.exists():
                shutil.rmtree(log_dir)

            subprocess.run(["systemctl", "daemon-reload"], check=True)

            return True

        except Exception as e:
            raise RuntimeError(f"Failed to uninstall: {e}") from e
