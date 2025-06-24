"""Tests for tunnel configuration."""

import pytest
from pydantic import ValidationError

from frp_wrapper.client.tunnel import TunnelConfig


class TestTunnelConfig:
    """Test TunnelConfig Pydantic model."""

    def test_tunnel_config_creation_with_required_fields(self):
        """Test TunnelConfig creation with only required fields."""
        config = TunnelConfig(server_host="tunnel.example.com")

        assert config.server_host == "tunnel.example.com"
        assert config.auth_token is None
        assert config.default_domain is None
        assert config.max_tunnels == 10  # Default value

    def test_tunnel_config_creation_with_all_fields(self):
        """Test TunnelConfig creation with all fields."""
        config = TunnelConfig(
            server_host="tunnel.example.com",
            auth_token="secret123",
            default_domain="example.com",
            max_tunnels=5,
        )

        assert config.server_host == "tunnel.example.com"
        assert config.auth_token == "secret123"
        assert config.default_domain == "example.com"
        assert config.max_tunnels == 5

    def test_tunnel_config_server_host_validation(self):
        """Test server host validation."""
        # Valid hostnames
        TunnelConfig(server_host="example.com")
        TunnelConfig(server_host="tunnel.example.com")
        TunnelConfig(server_host="my-server.test")
        TunnelConfig(server_host="server_1.domain.org")
        TunnelConfig(server_host="localhost")

        # Invalid hostnames
        with pytest.raises(ValidationError):
            TunnelConfig(server_host="")  # Empty

        with pytest.raises(ValidationError):
            TunnelConfig(server_host="invalid@hostname")  # Contains @

        with pytest.raises(ValidationError):
            TunnelConfig(server_host="server:8080")  # Contains :

        with pytest.raises(ValidationError):
            TunnelConfig(server_host="server/path")  # Contains /

    def test_tunnel_config_max_tunnels_validation(self):
        """Test max_tunnels validation."""
        # Valid values
        TunnelConfig(server_host="example.com", max_tunnels=1)
        TunnelConfig(server_host="example.com", max_tunnels=50)
        TunnelConfig(server_host="example.com", max_tunnels=100)

        # Invalid values
        with pytest.raises(ValidationError):
            TunnelConfig(server_host="example.com", max_tunnels=0)  # Below minimum

        with pytest.raises(ValidationError):
            TunnelConfig(server_host="example.com", max_tunnels=101)  # Above maximum

        with pytest.raises(ValidationError):
            TunnelConfig(server_host="example.com", max_tunnels=-5)  # Negative

    def test_tunnel_config_whitespace_stripping(self):
        """Test that whitespace is stripped from string fields."""
        config = TunnelConfig(
            server_host="  tunnel.example.com  ",
            auth_token="  secret123  ",
            default_domain="  example.com  ",
        )

        assert config.server_host == "tunnel.example.com"
        assert config.auth_token == "secret123"
        assert config.default_domain == "example.com"

    def test_tunnel_config_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            TunnelConfig(
                server_host="example.com",
                extra_field="not_allowed",  # This should fail
            )

    def test_tunnel_config_serialization(self):
        """Test TunnelConfig serialization/deserialization."""
        config = TunnelConfig(
            server_host="tunnel.example.com",
            auth_token="secret123",
            default_domain="example.com",
            max_tunnels=20,
        )

        data = config.model_dump()
        assert data["server_host"] == "tunnel.example.com"
        assert data["auth_token"] == "secret123"
        assert data["default_domain"] == "example.com"
        assert data["max_tunnels"] == 20

        restored_config = TunnelConfig.model_validate(data)
        assert restored_config.server_host == config.server_host
        assert restored_config.auth_token == config.auth_token
        assert restored_config.default_domain == config.default_domain
        assert restored_config.max_tunnels == config.max_tunnels

    def test_tunnel_config_json_roundtrip(self):
        """Test TunnelConfig JSON serialization roundtrip."""
        config = TunnelConfig(
            server_host="tunnel.example.com",
            auth_token="secret123",
        )

        json_str = config.model_dump_json()
        restored_config = TunnelConfig.model_validate_json(json_str)

        assert restored_config.server_host == config.server_host
        assert restored_config.auth_token == config.auth_token
        assert restored_config.max_tunnels == config.max_tunnels  # Default value

    def test_tunnel_config_optional_fields_none(self):
        """Test TunnelConfig with optional fields as None."""
        config = TunnelConfig(
            server_host="example.com",
            auth_token=None,
            default_domain=None,
        )

        assert config.server_host == "example.com"
        assert config.auth_token is None
        assert config.default_domain is None
        assert config.max_tunnels == 10  # Default

    def test_tunnel_config_hostname_edge_cases(self):
        """Test edge cases for hostname validation."""
        # IP addresses should work
        TunnelConfig(server_host="192.168.1.1")
        TunnelConfig(server_host="10.0.0.1")

        # Single character should work
        TunnelConfig(server_host="a")

        # Numbers should work
        TunnelConfig(server_host="123")

        # Mixed alphanumeric with valid separators
        TunnelConfig(server_host="server123.test-domain.com")
        TunnelConfig(server_host="my_server.example_domain.org")
