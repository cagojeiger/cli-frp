import os
from unittest.mock import patch

import pytest

from frp_wrapper.core.config import ConfigBuilder


class TestConfigBuilder:
    def test_config_builder_initialization(self):
        """ConfigBuilder should initialize with empty state"""
        builder = ConfigBuilder()

        assert builder._server_addr is None
        assert builder._server_port == 7000
        assert builder._auth_token is None
        assert builder._config_path is None

    def test_add_server_basic(self):
        """ConfigBuilder should add server configuration"""
        builder = ConfigBuilder()
        result = builder.add_server("example.com")

        assert result is builder  # Should return self for chaining
        assert builder._server_addr == "example.com"
        assert builder._server_port == 7000
        assert builder._auth_token is None

    def test_add_server_with_port_and_token(self):
        """ConfigBuilder should add server with custom port and token"""
        builder = ConfigBuilder()
        builder.add_server("example.com", port=8000, token="secret123")

        assert builder._server_addr == "example.com"
        assert builder._server_port == 8000
        assert builder._auth_token == "secret123"

    def test_add_server_validates_address(self):
        """ConfigBuilder should validate server address"""
        builder = ConfigBuilder()

        with pytest.raises(ValueError, match="Server address cannot be empty"):
            builder.add_server("")

        with pytest.raises(ValueError, match="Server address cannot be empty"):
            builder.add_server("   ")

    def test_add_server_validates_port(self):
        """ConfigBuilder should validate port number"""
        builder = ConfigBuilder()

        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            builder.add_server("example.com", port=0)

        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            builder.add_server("example.com", port=65536)

    def test_build_requires_server(self):
        """ConfigBuilder should require server address before building"""
        builder = ConfigBuilder()

        with pytest.raises(ValueError, match="Server address not set"):
            builder.build()

    def test_build_creates_config_file(self):
        """ConfigBuilder should create TOML configuration file"""
        builder = ConfigBuilder()
        builder.add_server("example.com")

        config_path = builder.build()

        assert config_path is not None
        assert os.path.exists(config_path)
        assert config_path.endswith(".toml")

        with open(config_path) as f:
            content = f.read()

        assert "[common]" in content
        assert 'server_addr = "example.com"' in content
        assert "server_port = 7000" in content

        builder.cleanup()

    def test_build_handles_file_creation_error(self):
        """ConfigBuilder should handle file creation errors"""
        builder = ConfigBuilder()
        builder.add_server("example.com")

        with patch("tempfile.mkstemp") as mock_mkstemp:
            mock_mkstemp.side_effect = OSError("Permission denied")

            with pytest.raises(OSError):
                builder.build()

    def test_build_with_token(self):
        """ConfigBuilder should include token in configuration"""
        builder = ConfigBuilder()
        builder.add_server("example.com", token="secret123")

        config_path = builder.build()

        with open(config_path) as f:
            content = f.read()

        assert 'token = "secret123"' in content

        builder.cleanup()

    def test_build_with_custom_port(self):
        """ConfigBuilder should include custom port in configuration"""
        builder = ConfigBuilder()
        builder.add_server("example.com", port=8000)

        config_path = builder.build()

        with open(config_path) as f:
            content = f.read()

        assert "server_port = 8000" in content

        builder.cleanup()

    def test_cleanup_removes_config_file(self):
        """ConfigBuilder should clean up temporary config file"""
        builder = ConfigBuilder()
        builder.add_server("example.com")

        config_path = builder.build()
        assert os.path.exists(config_path)

        builder.cleanup()
        assert not os.path.exists(config_path)

    def test_cleanup_handles_missing_file(self):
        """ConfigBuilder should handle cleanup when file doesn't exist"""
        builder = ConfigBuilder()

        builder.cleanup()

    def test_cleanup_handles_permission_error(self):
        """ConfigBuilder should handle cleanup permission errors"""
        builder = ConfigBuilder()
        builder.add_server("example.com")

        builder.build()

        with patch("os.unlink") as mock_unlink:
            mock_unlink.side_effect = OSError("Permission denied")

            builder.cleanup()  # Should not raise exception

    def test_multiple_builds_create_different_files(self):
        """ConfigBuilder should create new file on each build"""
        builder = ConfigBuilder()
        builder.add_server("example.com")

        config_path1 = builder.build()
        config_path2 = builder.build()

        assert config_path1 != config_path2
        assert os.path.exists(config_path1)
        assert os.path.exists(config_path2)

        builder.cleanup()
        assert os.path.exists(config_path1)
        assert not os.path.exists(config_path2)

        os.unlink(config_path1)

    def test_config_builder_as_context_manager(self):
        """ConfigBuilder should work as context manager for automatic cleanup"""
        config_path = None

        with ConfigBuilder() as builder:
            builder.add_server("example.com")
            config_path = builder.build()
            assert os.path.exists(config_path)

        assert not os.path.exists(config_path)

    def test_context_manager_handles_exception(self):
        """ConfigBuilder context manager should cleanup on exception"""
        config_path = None

        try:
            with ConfigBuilder() as builder:
                builder.add_server("example.com")
                config_path = builder.build()
                assert os.path.exists(config_path)
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        assert not os.path.exists(config_path)

    def test_context_manager_handles_cleanup_exception(self):
        """ConfigBuilder context manager should handle cleanup exceptions"""
        with patch("frp_wrapper.config.ConfigBuilder.cleanup") as mock_cleanup:
            mock_cleanup.side_effect = Exception("Cleanup failed")

            with ConfigBuilder() as builder:
                builder.add_server("example.com")
                builder.build()

            mock_cleanup.assert_called_once()

    def test_toml_format_validation(self):
        """ConfigBuilder should generate valid TOML format"""
        try:
            import tomllib  # Python 3.11+ built-in
        except ImportError:
            try:
                import tomli as tomllib  # Fallback for older Python
            except ImportError:
                pytest.skip("No TOML parser available")

        builder = ConfigBuilder()
        builder.add_server("example.com", port=8000, token="secret123")

        config_path = builder.build()

        with open(config_path, "rb") as f:
            parsed = tomllib.load(f)

        assert "common" in parsed
        assert parsed["common"]["server_addr"] == "example.com"
        assert parsed["common"]["server_port"] == 8000
        assert parsed["common"]["token"] == "secret123"

    def test_build_exception_cleanup(self):
        """Test that build() cleans up temp file on exception."""
        builder = ConfigBuilder()
        builder.add_server("example.com")

        # Mock tempfile.mkstemp and os.fdopen to simulate exception
        with (
            patch("tempfile.mkstemp") as mock_mkstemp,
            patch("os.fdopen") as mock_fdopen,
            patch("os.unlink") as mock_unlink,
        ):
            # Setup mkstemp to return fake fd and path
            mock_mkstemp.return_value = (5, "/tmp/test_config.toml")

            # Make fdopen raise exception
            mock_fdopen.side_effect = Exception("File open error")

            with pytest.raises(Exception, match="File open error"):
                builder.build()

            # Verify cleanup was attempted
            mock_unlink.assert_called_once_with("/tmp/test_config.toml")

    def test_build_exception_cleanup_with_oserror(self):
        """Test build() exception cleanup when temp file deletion also fails."""
        builder = ConfigBuilder()
        builder.add_server("example.com")

        # Mock tempfile.mkstemp and os.fdopen to simulate exception
        # and OSError during cleanup
        with (
            patch("tempfile.mkstemp") as mock_mkstemp,
            patch("os.fdopen") as mock_fdopen,
            patch("os.unlink") as mock_unlink,
        ):
            # Setup mkstemp to return fake fd and path
            mock_mkstemp.return_value = (5, "/tmp/test_config.toml")

            # Make fdopen raise exception
            mock_fdopen.side_effect = Exception("File open error")

            # Make unlink() raise OSError during cleanup
            mock_unlink.side_effect = OSError("Delete failed")

            # Both exceptions should be handled gracefully
            # The original exception should be re-raised, OSError should be suppressed
            with pytest.raises(Exception, match="File open error"):
                builder.build()

            # Verify cleanup was attempted
            mock_unlink.assert_called_once_with("/tmp/test_config.toml")
