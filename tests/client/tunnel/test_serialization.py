"""Tests for tunnel serialization."""

from frp_wrapper.client.tunnel import HTTPTunnel, TCPTunnel, TunnelType


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
