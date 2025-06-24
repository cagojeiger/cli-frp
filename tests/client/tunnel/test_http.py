"""Tests for HTTP tunnel."""

import pytest
from pydantic import ValidationError

from frp_wrapper.client.tunnel import HTTPTunnel, TunnelStatus, TunnelType


class TestHTTPTunnel:
    def test_http_tunnel_creation(self):
        """Test HTTP tunnel creation with path validation"""
        tunnel = HTTPTunnel(
            id="http-test",
            local_port=3000,
            path="myapp",
            custom_domains=["example.com"],
        )

        assert tunnel.tunnel_type == TunnelType.HTTP
        assert tunnel.path == "myapp"
        assert tunnel.custom_domains == ["example.com"]
        assert tunnel.strip_path is True  # Default value
        assert tunnel.websocket is True  # Default value

    def test_http_tunnel_path_validation(self):
        """Test HTTP tunnel path validation with Pydantic validators"""
        HTTPTunnel(id="test", local_port=3000, path="myapp")
        HTTPTunnel(id="test", local_port=3000, path="my-app")
        HTTPTunnel(id="test", local_port=3000, path="my_app")
        HTTPTunnel(id="test", local_port=3000, path="app123")

        with pytest.raises(ValidationError, match="Path should not start with"):
            HTTPTunnel(id="test", local_port=3000, path="/myapp")

        with pytest.raises(ValidationError, match="alphanumeric characters"):
            HTTPTunnel(id="test", local_port=3000, path="my@app")

    def test_http_tunnel_url_property(self):
        """Test HTTP tunnel URL generation"""
        tunnel = HTTPTunnel(
            id="http-test",
            local_port=3000,
            path="myapp",
            custom_domains=["example.com"],
        )

        assert tunnel.url is None

        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        assert connected_tunnel.url == "https://example.com/myapp/"

    def test_http_tunnel_locations_property(self):
        """Test FRP locations configuration"""
        tunnel = HTTPTunnel(id="http-test", local_port=3000, path="myapp")

        assert tunnel.locations == ["/myapp"]

    def test_http_tunnel_defaults(self):
        """Test HTTP tunnel default values"""
        tunnel = HTTPTunnel(id="http-test", local_port=3000, path="myapp")

        assert tunnel.custom_domains == []
        assert tunnel.strip_path is True
        assert tunnel.websocket is True

    def test_http_tunnel_path_validation_edge_cases(self):
        """Test HTTP tunnel path validation edge cases"""
        HTTPTunnel(id="test", local_port=3000, path="api/v1")
        HTTPTunnel(id="test", local_port=3000, path="my-app_v2")
        HTTPTunnel(id="test", local_port=3000, path="app123/test")
        HTTPTunnel(id="test", local_port=3000, path="my.app")  # Dot is now allowed
        HTTPTunnel(id="test", local_port=3000, path="api/*")  # Wildcard is now allowed

        with pytest.raises(ValidationError):
            HTTPTunnel(id="test", local_port=3000, path="my app")  # Space

        with pytest.raises(ValidationError):
            HTTPTunnel(id="test", local_port=3000, path="my#app")  # Hash

        with pytest.raises(ValidationError):
            HTTPTunnel(
                id="test", local_port=3000, path="api/../admin"
            )  # Directory traversal

        with pytest.raises(ValidationError):
            HTTPTunnel(id="test", local_port=3000, path="api/")  # Trailing slash

        # Test enhanced security validations
        with pytest.raises(ValidationError):
            HTTPTunnel(id="test", local_port=3000, path="./api")  # Relative path

        with pytest.raises(ValidationError):
            HTTPTunnel(id="test", local_port=3000, path="api/***")  # Triple wildcards

        with pytest.raises(ValidationError):
            HTTPTunnel(
                id="test", local_port=3000, path="**/**"
            )  # Nested recursive wildcards

        with pytest.raises(ValidationError):
            HTTPTunnel(
                id="test", local_port=3000, path="/**/"
            )  # Standalone recursive wildcards

        with pytest.raises(ValidationError):
            HTTPTunnel(
                id="test", local_port=3000, path="api\x00test"
            )  # Control characters

        with pytest.raises(ValidationError, match="Path too long"):
            HTTPTunnel(id="test", local_port=3000, path="a" * 201)  # Too long path

    def test_http_tunnel_multiple_custom_domains(self):
        """Test HTTP tunnel with multiple custom domains"""
        tunnel = HTTPTunnel(
            id="http-test",
            local_port=3000,
            path="myapp",
            custom_domains=["example.com", "test.com", "app.dev"],
        )

        assert len(tunnel.custom_domains) == 3
        assert "example.com" in tunnel.custom_domains
        assert "test.com" in tunnel.custom_domains
        assert "app.dev" in tunnel.custom_domains

        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        assert connected_tunnel.url == "https://example.com/myapp/"

    def test_http_tunnel_url_without_domains(self):
        """Test HTTP tunnel URL generation without custom domains"""
        tunnel = HTTPTunnel(id="http-test", local_port=3000, path="myapp")

        assert tunnel.url is None

        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        assert connected_tunnel.url is None

    def test_http_tunnel_strip_path_configuration(self):
        """Test HTTP tunnel strip_path configuration"""
        # Default strip_path is True
        tunnel_default = HTTPTunnel(id="http-test", local_port=3000, path="myapp")
        assert tunnel_default.strip_path is True

        tunnel_no_strip = HTTPTunnel(
            id="http-test", local_port=3000, path="myapp", strip_path=False
        )
        assert tunnel_no_strip.strip_path is False

    def test_http_tunnel_websocket_configuration(self):
        """Test HTTP tunnel WebSocket configuration"""
        # Default websocket is True
        tunnel_default = HTTPTunnel(id="http-test", local_port=3000, path="myapp")
        assert tunnel_default.websocket is True

        tunnel_no_ws = HTTPTunnel(
            id="http-test", local_port=3000, path="myapp", websocket=False
        )
        assert tunnel_no_ws.websocket is False

    def test_http_tunnel_locations_complex_paths(self):
        """Test FRP locations with complex paths"""
        tunnel_simple = HTTPTunnel(id="http-test", local_port=3000, path="myapp")
        assert tunnel_simple.locations == ["/myapp"]

        tunnel_nested = HTTPTunnel(id="http-test", local_port=3000, path="api/v1")
        assert tunnel_nested.locations == ["/api/v1"]

    def test_http_tunnel_immutability_with_status(self):
        """Test HTTP tunnel immutability with status changes"""
        tunnel = HTTPTunnel(
            id="http-test",
            local_port=3000,
            path="myapp",
            custom_domains=["example.com"],
        )

        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)

        assert tunnel.status == TunnelStatus.PENDING
        assert tunnel.url is None

        assert connected_tunnel.status == TunnelStatus.CONNECTED
        assert connected_tunnel.url == "https://example.com/myapp/"

        # Other properties preserved
        assert connected_tunnel.path == tunnel.path
        assert connected_tunnel.custom_domains == tunnel.custom_domains

    def test_http_tunnel_serialization(self):
        """Test HTTP tunnel serialization/deserialization"""
        tunnel = HTTPTunnel(
            id="http-test",
            local_port=3000,
            path="myapp",
            custom_domains=["example.com"],
            strip_path=False,
            websocket=False,
        )

        data = tunnel.model_dump()
        assert data["tunnel_type"] == "http"
        assert data["path"] == "myapp"
        assert data["custom_domains"] == ["example.com"]
        assert data["strip_path"] is False
        assert data["websocket"] is False

        restored_tunnel = HTTPTunnel.model_validate(data)
        assert restored_tunnel.path == tunnel.path
        assert restored_tunnel.custom_domains == tunnel.custom_domains
        assert restored_tunnel.strip_path == tunnel.strip_path
        assert restored_tunnel.websocket == tunnel.websocket

    def test_http_tunnel_json_roundtrip(self):
        """Test HTTP tunnel JSON serialization roundtrip"""
        tunnel = HTTPTunnel(
            id="json-test",
            local_port=8080,
            path="api/test",
            custom_domains=["api.example.com"],
        )

        json_str = tunnel.model_dump_json()
        restored_tunnel = HTTPTunnel.model_validate_json(json_str)

        assert restored_tunnel.id == tunnel.id
        assert restored_tunnel.path == tunnel.path
        assert restored_tunnel.custom_domains == tunnel.custom_domains
        assert restored_tunnel.tunnel_type == tunnel.tunnel_type
        assert restored_tunnel.local_port == tunnel.local_port
