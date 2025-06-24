"""Tests for TCP tunnel."""

import pytest
from pydantic import ValidationError

from frp_wrapper.client.tunnel import TCPTunnel, TunnelStatus, TunnelType


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
