"""Tests for tunnel models."""

from datetime import datetime
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from frp_wrapper.client.tunnel import (
    BaseTunnel,
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

    def test_tunnel_with_manager_association(self):
        """Test associating tunnel with manager."""
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=3000)
        mock_manager = Mock()

        tunnel_with_manager = tunnel.with_manager(mock_manager)

        assert tunnel_with_manager.manager is mock_manager
        assert tunnel_with_manager.id == tunnel.id
        assert tunnel.manager is None  # Original unchanged

    def test_tunnel_context_manager_success(self):
        """Test successful tunnel context manager usage."""
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=3000)

        # Create mock manager
        mock_manager = Mock()
        mock_manager.start_tunnel.return_value = True
        mock_manager.stop_tunnel.return_value = True
        mock_manager.remove_tunnel.return_value = tunnel

        # Mock registry to return updated tunnel
        updated_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        mock_manager.registry.get_tunnel.return_value = updated_tunnel

        tunnel_with_manager = tunnel.with_manager(mock_manager)

        # Use context manager
        with tunnel_with_manager as active_tunnel:
            assert active_tunnel.manager is mock_manager
            assert active_tunnel.status == TunnelStatus.CONNECTED
            mock_manager.start_tunnel.assert_called_once_with("test")

        # Verify cleanup was called
        mock_manager.stop_tunnel.assert_called_once_with("test")
        mock_manager.remove_tunnel.assert_called_once_with("test")

    def test_tunnel_context_manager_no_manager_error(self):
        """Test context manager fails without associated manager."""
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=3000)

        with pytest.raises(RuntimeError, match="No manager associated"):
            with tunnel:
                pass

    def test_tunnel_context_manager_start_failure(self):
        """Test context manager fails when tunnel start fails."""
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=3000)

        mock_manager = Mock()
        mock_manager.start_tunnel.return_value = False  # Start fails

        tunnel_with_manager = tunnel.with_manager(mock_manager)

        with pytest.raises(RuntimeError, match="Failed to start tunnel"):
            with tunnel_with_manager:
                pass

    def test_tunnel_context_manager_cleanup_on_exception(self):
        """Test context manager cleans up even when exception occurs."""
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=3000)

        mock_manager = Mock()
        mock_manager.start_tunnel.return_value = True

        # Mock registry to return connected tunnel
        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        mock_manager.registry.get_tunnel.return_value = connected_tunnel

        tunnel_with_manager = tunnel.with_manager(mock_manager)

        with pytest.raises(ValueError):
            with tunnel_with_manager:
                raise ValueError("Test exception")

        # Verify cleanup was still called
        mock_manager.stop_tunnel.assert_called_once_with("test")
        mock_manager.remove_tunnel.assert_called_once_with("test")

    def test_tunnel_context_manager_cleanup_suppresses_exceptions(self):
        """Test context manager suppresses cleanup exceptions."""
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=3000)

        mock_manager = Mock()
        mock_manager.start_tunnel.return_value = True
        mock_manager.stop_tunnel.side_effect = Exception("Cleanup error")

        # Mock registry to return connected tunnel
        connected_tunnel = tunnel.with_status(TunnelStatus.CONNECTED)
        mock_manager.registry.get_tunnel.return_value = connected_tunnel

        tunnel_with_manager = tunnel.with_manager(mock_manager)

        # Should not raise cleanup exception
        with tunnel_with_manager:
            pass

    def test_tunnel_context_manager_skip_stop_if_not_connected(self):
        """Test context manager skips stop if tunnel not connected."""
        tunnel = BaseTunnel(id="test", tunnel_type=TunnelType.TCP, local_port=3000)

        mock_manager = Mock()
        mock_manager.start_tunnel.return_value = True

        # Mock registry to return pending tunnel (not connected)
        pending_tunnel = tunnel.with_status(TunnelStatus.PENDING)
        mock_manager.registry.get_tunnel.return_value = pending_tunnel

        tunnel_with_manager = tunnel.with_manager(mock_manager)

        with tunnel_with_manager:
            pass

        # Stop should not be called for non-connected tunnel
        mock_manager.stop_tunnel.assert_not_called()
        mock_manager.remove_tunnel.assert_called_once_with("test")
