from datetime import datetime

import pytest
from pydantic import ValidationError

from frp_wrapper.tunnel import (
    BaseTunnel,
    HTTPTunnel,
    TCPTunnel,
    TunnelStatus,
    TunnelType,
)


class TestTunnelEnums:
    def test_tunnel_type_enum(self):
        """Test TunnelType enum values"""
        assert TunnelType.HTTP == "http"
        assert TunnelType.TCP == "tcp"

    def test_tunnel_status_enum(self):
        """Test TunnelStatus enum values"""
        assert TunnelStatus.PENDING == "pending"
        assert TunnelStatus.CONNECTING == "connecting"
        assert TunnelStatus.CONNECTED == "connected"
        assert TunnelStatus.DISCONNECTED == "disconnected"
        assert TunnelStatus.ERROR == "error"
        assert TunnelStatus.CLOSED == "closed"


class TestBaseTunnel:
    def test_base_tunnel_creation(self):
        """Test BaseTunnel creation with required fields"""
        tunnel = BaseTunnel(
            id="test-tunnel-1", tunnel_type=TunnelType.TCP, local_port=3000
        )

        assert tunnel.id == "test-tunnel-1"
        assert tunnel.tunnel_type == TunnelType.TCP
        assert tunnel.local_port == 3000
        assert tunnel.status == TunnelStatus.PENDING
        assert isinstance(tunnel.created_at, datetime)
        assert tunnel.connected_at is None

    def test_tunnel_port_validation(self):
        """Test port validation with Pydantic validators"""
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=8080)
        assert tunnel.local_port == 8080

        with pytest.raises(ValidationError) as exc_info:
            BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=0)

        errors = exc_info.value.errors()
        assert any("greater than or equal to 1" in str(error) for error in errors)

        with pytest.raises(ValidationError):
            BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=65536)

    def test_tunnel_id_validation(self):
        """Test tunnel ID validation"""
        BaseTunnel(id="valid-id", tunnel_type=TunnelType.TCP, local_port=3000)

        with pytest.raises(ValidationError) as exc_info:
            BaseTunnel(id="", tunnel_type=TunnelType.TCP, local_port=3000)

        errors = exc_info.value.errors()
        assert any("at least 1 character" in str(error) for error in errors)

    def test_tunnel_immutability(self):
        """Test that tunnel is immutable after creation"""
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=3000)

        with pytest.raises(ValidationError):
            tunnel.status = TunnelStatus.CONNECTED

    def test_tunnel_with_status_creates_new_instance(self):
        """Test immutable status update pattern"""
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=3000)

        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)

        assert tunnel.status == TunnelStatus.PENDING
        assert tunnel.connected_at is None

        assert connected_tunnel.status == TunnelStatus.CONNECTED
        assert connected_tunnel.connected_at is not None
        assert connected_tunnel.id == tunnel.id  # Other fields preserved
        assert connected_tunnel.local_port == tunnel.local_port

    def test_tunnel_status_transitions(self):
        """Test various status transitions"""
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=3000)

        connecting_tunnel = tunnel.with_status(TunnelStatus.CONNECTING)
        assert connecting_tunnel.status == TunnelStatus.CONNECTING
        assert connecting_tunnel.connected_at is None

        connected_tunnel = connecting_tunnel.with_status(TunnelStatus.CONNECTED)
        assert connected_tunnel.status == TunnelStatus.CONNECTED
        assert connected_tunnel.connected_at is not None

        disconnected_tunnel = connected_tunnel.with_status(TunnelStatus.DISCONNECTED)
        assert disconnected_tunnel.status == TunnelStatus.DISCONNECTED
        assert disconnected_tunnel.connected_at is not None  # Preserves connection time

        error_tunnel = tunnel.with_status(TunnelStatus.ERROR)
        assert error_tunnel.status == TunnelStatus.ERROR

    def test_tunnel_created_at_timestamp(self):
        """Test that created_at is automatically set"""
        before_creation = datetime.now()
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=3000)
        after_creation = datetime.now()

        assert before_creation <= tunnel.created_at <= after_creation

    def test_tunnel_connected_at_only_set_on_connected(self):
        """Test that connected_at is only set when transitioning to CONNECTED"""
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=3000)

        connecting_tunnel = tunnel.with_status(TunnelStatus.CONNECTING)
        assert connecting_tunnel.connected_at is None

        error_tunnel = tunnel.with_status(TunnelStatus.ERROR)
        assert error_tunnel.connected_at is None

        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        assert connected_tunnel.connected_at is not None

    def test_tunnel_with_status_preserves_connected_at(self):
        """Test that connected_at is preserved across status changes"""
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=3000)
        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        original_connected_at = connected_tunnel.connected_at

        disconnected_tunnel = connected_tunnel.with_status(TunnelStatus.DISCONNECTED)
        assert disconnected_tunnel.connected_at == original_connected_at

        reconnected_tunnel = disconnected_tunnel.with_status(TunnelStatus.CONNECTED)
        assert reconnected_tunnel.connected_at == original_connected_at

    def test_base_tunnel_serialization_to_dict(self):
        """Test BaseTunnel serialization to dictionary"""
        tunnel = BaseTunnel(
            id="test-tunnel", tunnel_type=TunnelType.HTTP, local_port=8080
        )

        data = tunnel.model_dump()

        assert data["id"] == "test-tunnel"
        assert data["tunnel_type"] == "http"
        assert data["local_port"] == 8080
        assert data["status"] == "pending"
        assert "created_at" in data
        assert data["connected_at"] is None

    def test_base_tunnel_deserialization_from_dict(self):
        """Test BaseTunnel deserialization from dictionary"""
        data = {
            "id": "test-tunnel",
            "tunnel_type": "tcp",
            "local_port": 3000,
            "status": "connected",
            "created_at": "2023-01-01T12:00:00",
            "connected_at": "2023-01-01T12:01:00",
        }

        tunnel = BaseTunnel.model_validate(data)

        assert tunnel.id == "test-tunnel"
        assert tunnel.tunnel_type == TunnelType.TCP
        assert tunnel.local_port == 3000
        assert tunnel.status == TunnelStatus.CONNECTED

    def test_base_tunnel_json_serialization(self):
        """Test BaseTunnel JSON serialization roundtrip"""
        tunnel = BaseTunnel(id="json-test", tunnel_type=TunnelType.TCP, local_port=5432)

        json_str = tunnel.model_dump_json()
        restored_tunnel = BaseTunnel.model_validate_json(json_str)

        assert restored_tunnel.id == tunnel.id
        assert restored_tunnel.tunnel_type == tunnel.tunnel_type
        assert restored_tunnel.local_port == tunnel.local_port
        assert restored_tunnel.status == tunnel.status


class TestTCPTunnel:
    def test_tcp_tunnel_creation(self):
        """Test TCP tunnel creation with Pydantic validation"""
        tunnel = TCPTunnel(id="tcp-test", local_port=3000, remote_port=8080)

        assert tunnel.tunnel_type == TunnelType.TCP
        assert tunnel.local_port == 3000
        assert tunnel.remote_port == 8080

    def test_tcp_tunnel_without_remote_port(self):
        """Test TCP tunnel creation without remote port"""
        tunnel = TCPTunnel(id="tcp-test", local_port=3000)

        assert tunnel.tunnel_type == TunnelType.TCP
        assert tunnel.local_port == 3000
        assert tunnel.remote_port is None

    def test_tcp_tunnel_endpoint_property(self):
        """Test TCP tunnel endpoint generation"""
        tunnel = TCPTunnel(id="tcp-test", local_port=3000, remote_port=8080)

        assert tunnel.endpoint is None

        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        assert connected_tunnel.endpoint is not None

    def test_tcp_tunnel_validation_errors(self):
        """Test TCP tunnel Pydantic validation"""
        with pytest.raises(ValidationError):
            TCPTunnel(
                id="",  # Empty ID should fail
                local_port=3000,
            )

        with pytest.raises(ValidationError):
            TCPTunnel(
                id="test",
                local_port=3000,
                remote_port=99999,  # Invalid port
            )

    def test_tcp_tunnel_remote_port_validation(self):
        """Test TCP tunnel remote port validation"""
        TCPTunnel(id="test", local_port=3000, remote_port=1)
        TCPTunnel(id="test", local_port=3000, remote_port=8080)
        TCPTunnel(id="test", local_port=3000, remote_port=65535)

        with pytest.raises(ValidationError):
            TCPTunnel(id="test", local_port=3000, remote_port=0)

        with pytest.raises(ValidationError):
            TCPTunnel(id="test", local_port=3000, remote_port=65536)

        with pytest.raises(ValidationError):
            TCPTunnel(id="test", local_port=3000, remote_port=-1)

    def test_tcp_tunnel_endpoint_format(self):
        """Test TCP tunnel endpoint format generation"""
        tunnel = TCPTunnel(id="tcp-test", local_port=3000, remote_port=8080)

        assert tunnel.endpoint is None

        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        assert connected_tunnel.endpoint == "{server_host}:8080"

    def test_tcp_tunnel_endpoint_without_remote_port(self):
        """Test TCP tunnel endpoint when remote port is None"""
        tunnel = TCPTunnel(id="tcp-test", local_port=3000)

        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        assert connected_tunnel.endpoint is None

    def test_tcp_tunnel_endpoint_status_dependency(self):
        """Test TCP tunnel endpoint depends on connection status"""
        tunnel = TCPTunnel(id="tcp-test", local_port=3000, remote_port=8080)

        pending_tunnel = tunnel.with_status(TunnelStatus.PENDING)
        assert pending_tunnel.endpoint is None

        connecting_tunnel = tunnel.with_status(TunnelStatus.CONNECTING)
        assert connecting_tunnel.endpoint is None

        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        assert connected_tunnel.endpoint == "{server_host}:8080"

        disconnected_tunnel = tunnel.with_status(TunnelStatus.DISCONNECTED)
        assert disconnected_tunnel.endpoint is None

        error_tunnel = tunnel.with_status(TunnelStatus.ERROR)
        assert error_tunnel.endpoint is None

    def test_tcp_tunnel_immutability_with_status(self):
        """Test TCP tunnel immutability with status changes"""
        tunnel = TCPTunnel(id="tcp-test", local_port=3000, remote_port=8080)

        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)

        assert tunnel.status == TunnelStatus.PENDING
        assert tunnel.endpoint is None

        assert connected_tunnel.status == TunnelStatus.CONNECTED
        assert connected_tunnel.endpoint == "{server_host}:8080"

        # Other properties preserved
        assert connected_tunnel.local_port == tunnel.local_port
        assert connected_tunnel.remote_port == tunnel.remote_port
        assert connected_tunnel.id == tunnel.id

    def test_tcp_tunnel_auto_assigned_remote_port(self):
        """Test TCP tunnel behavior with auto-assigned remote port"""
        tunnel = TCPTunnel(id="tcp-test", local_port=3000)

        assert tunnel.remote_port is None

        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        assert connected_tunnel.remote_port is None
        assert connected_tunnel.endpoint is None

    def test_tcp_tunnel_serialization(self):
        """Test TCP tunnel serialization/deserialization"""
        tunnel = TCPTunnel(id="tcp-test", local_port=3000, remote_port=8080)

        data = tunnel.model_dump()
        assert data["tunnel_type"] == "tcp"
        assert data["local_port"] == 3000
        assert data["remote_port"] == 8080
        assert data["id"] == "tcp-test"

        restored_tunnel = TCPTunnel.model_validate(data)
        assert restored_tunnel.id == tunnel.id
        assert restored_tunnel.local_port == tunnel.local_port
        assert restored_tunnel.remote_port == tunnel.remote_port
        assert restored_tunnel.tunnel_type == tunnel.tunnel_type

    def test_tcp_tunnel_serialization_without_remote_port(self):
        """Test TCP tunnel serialization when remote port is None"""
        tunnel = TCPTunnel(id="tcp-test", local_port=3000)

        data = tunnel.model_dump()
        assert data["tunnel_type"] == "tcp"
        assert data["local_port"] == 3000
        assert data["remote_port"] is None

        restored_tunnel = TCPTunnel.model_validate(data)
        assert restored_tunnel.remote_port is None
        assert restored_tunnel.local_port == tunnel.local_port

    def test_tcp_tunnel_json_roundtrip(self):
        """Test TCP tunnel JSON serialization roundtrip"""
        tunnel = TCPTunnel(id="json-test", local_port=5432, remote_port=9876)

        json_str = tunnel.model_dump_json()
        restored_tunnel = TCPTunnel.model_validate_json(json_str)

        assert restored_tunnel.id == tunnel.id
        assert restored_tunnel.local_port == tunnel.local_port
        assert restored_tunnel.remote_port == tunnel.remote_port
        assert restored_tunnel.tunnel_type == tunnel.tunnel_type
        assert restored_tunnel.status == tunnel.status

    def test_tcp_tunnel_json_roundtrip_without_remote_port(self):
        """Test TCP tunnel JSON serialization roundtrip without remote port"""
        tunnel = TCPTunnel(id="json-test", local_port=5432)

        json_str = tunnel.model_dump_json()
        restored_tunnel = TCPTunnel.model_validate_json(json_str)

        assert restored_tunnel.id == tunnel.id
        assert restored_tunnel.local_port == tunnel.local_port
        assert restored_tunnel.remote_port is None
        assert restored_tunnel.tunnel_type == tunnel.tunnel_type

    def test_tcp_tunnel_inheritance_from_base(self):
        """Test TCP tunnel inherits BaseTunnel functionality"""
        tunnel = TCPTunnel(id="inheritance-test", local_port=3000, remote_port=8080)

        assert hasattr(tunnel, "created_at")
        assert hasattr(tunnel, "connected_at")
        assert hasattr(tunnel, "status")
        assert tunnel.status == TunnelStatus.PENDING

        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        assert connected_tunnel.status == TunnelStatus.CONNECTED
        assert connected_tunnel.connected_at is not None


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

        with pytest.raises(ValidationError):
            HTTPTunnel(id="test", local_port=3000, path="my app")  # Space

        with pytest.raises(ValidationError):
            HTTPTunnel(id="test", local_port=3000, path="my.app")  # Dot

        with pytest.raises(ValidationError):
            HTTPTunnel(id="test", local_port=3000, path="my#app")  # Hash

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


class TestTunnelSerialization:
    def test_tunnel_to_dict(self):
        """Test tunnel serialization to dict"""
        tunnel = HTTPTunnel(
            id="http-test",
            local_port=3000,
            path="myapp",
            custom_domains=["example.com"],
        )

        data = tunnel.model_dump()

        assert data["id"] == "http-test"
        assert data["tunnel_type"] == "http"
        assert data["local_port"] == 3000
        assert data["path"] == "myapp"
        assert data["custom_domains"] == ["example.com"]

    def test_tunnel_from_dict(self):
        """Test tunnel deserialization from dict"""
        data = {
            "id": "http-test",
            "tunnel_type": "http",
            "local_port": 3000,
            "path": "myapp",
            "custom_domains": ["example.com"],
            "strip_path": True,
            "websocket": True,
        }

        tunnel = HTTPTunnel.model_validate(data)

        assert tunnel.id == "http-test"
        assert tunnel.tunnel_type == TunnelType.HTTP
        assert tunnel.local_port == 3000
        assert tunnel.path == "myapp"
        assert tunnel.custom_domains == ["example.com"]

    def test_tunnel_json_serialization(self):
        """Test tunnel JSON serialization"""
        tunnel = TCPTunnel(id="tcp-test", local_port=3000, remote_port=8080)

        json_str = tunnel.model_dump_json()
        restored_tunnel = TCPTunnel.model_validate_json(json_str)

        assert restored_tunnel.id == tunnel.id
        assert restored_tunnel.local_port == tunnel.local_port
        assert restored_tunnel.remote_port == tunnel.remote_port
        assert restored_tunnel.tunnel_type == tunnel.tunnel_type
