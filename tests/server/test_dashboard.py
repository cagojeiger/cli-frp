"""Tests for FRP server dashboard configuration."""

import pytest
from pydantic import ValidationError

from frp_wrapper.server.config import DashboardConfig


class TestDashboardConfig:
    """Test DashboardConfig model validation."""

    def test_dashboard_config_defaults(self):
        """Test DashboardConfig with default values."""
        config = DashboardConfig(password="Admin123")

        assert config.enabled is False
        assert config.port == 7500
        assert config.user == "admin"
        assert config.password == "Admin123"
        assert config.assets_dir is None

    def test_dashboard_config_custom(self):
        """Test DashboardConfig with custom values."""
        config = DashboardConfig(
            enabled=True,
            port=8500,
            user="superadmin",
            password="SuperSecure123",
            assets_dir="/path/to/assets",
        )

        assert config.enabled is True
        assert config.port == 8500
        assert config.user == "superadmin"
        assert config.password == "SuperSecure123"
        assert config.assets_dir == "/path/to/assets"

    def test_password_validation(self):
        """Test password strength validation."""
        # Valid passwords
        DashboardConfig(password="Admin123")
        DashboardConfig(password="SuperSecure123!")

        # Too short
        with pytest.raises(ValidationError) as exc_info:
            DashboardConfig(password="Abc1")
        assert "at least 6 characters" in str(exc_info.value)

        # Missing uppercase
        with pytest.raises(ValidationError) as exc_info:
            DashboardConfig(password="admin123")
        assert "uppercase, lowercase, and numbers" in str(exc_info.value)

        # Missing lowercase
        with pytest.raises(ValidationError) as exc_info:
            DashboardConfig(password="ADMIN123")
        assert "uppercase, lowercase, and numbers" in str(exc_info.value)

        # Missing numbers
        with pytest.raises(ValidationError) as exc_info:
            DashboardConfig(password="AdminPass")
        assert "uppercase, lowercase, and numbers" in str(exc_info.value)

    def test_user_validation(self):
        """Test username validation."""
        # Valid usernames
        config = DashboardConfig(user="adm", password="Admin123")
        assert config.user == "adm"

        # Too short
        with pytest.raises(ValidationError) as exc_info:
            DashboardConfig(user="ab", password="Admin123")
        assert "at least 3 characters" in str(exc_info.value)

    def test_to_toml_section_disabled(self):
        """Test TOML generation when dashboard is disabled."""
        config = DashboardConfig(password="Admin123")
        toml = config.to_toml_section()

        assert toml == ""  # Empty when disabled

    def test_to_toml_section_enabled(self):
        """Test TOML generation when dashboard is enabled."""
        config = DashboardConfig(
            enabled=True, port=8500, user="superadmin", password="SuperSecure123"
        )
        toml = config.to_toml_section()

        assert "[webServer]" in toml
        assert 'addr = "0.0.0.0"' in toml
        assert "port = 8500" in toml
        assert 'user = "superadmin"' in toml
        assert 'password = "SuperSecure123"' in toml

        # Should not include assets_dir when None
        assert "assetsDir" not in toml

    def test_to_toml_section_with_assets(self):
        """Test TOML generation with custom assets directory."""
        config = DashboardConfig(
            enabled=True, password="Admin123", assets_dir="/custom/assets"
        )
        toml = config.to_toml_section()

        assert 'assetsDir = "/custom/assets"' in toml
