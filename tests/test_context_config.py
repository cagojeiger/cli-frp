import pytest
from pydantic import ValidationError

from frp_wrapper.common.context_config import (
    ContextConfig, TunnelGroupConfig, ResourceTracker, CleanupStrategy
)

class TestContextConfig:
    def test_context_config_creation_with_defaults(self):
        """Test ContextConfig creation with default values"""
        config = ContextConfig()

        assert config.connect_timeout == 10.0
        assert config.cleanup_timeout == 5.0
        assert config.graceful_shutdown_timeout == 3.0
        assert config.cleanup_strategy == CleanupStrategy.GRACEFUL_THEN_FORCE
        assert config.suppress_cleanup_errors is True
        assert config.log_cleanup_errors is True
        assert config.track_resources is True
        assert config.max_tracked_resources == 100

    def test_context_config_validation_errors(self):
        """Test ContextConfig validation with invalid values"""
        with pytest.raises(ValidationError, match="greater than or equal to 0.1"):
            ContextConfig(connect_timeout=-1.0)

        with pytest.raises(ValidationError, match="less than or equal to 1000"):
            ContextConfig(max_tracked_resources=1001)

        with pytest.raises(ValidationError, match="Input should be greater than or equal to 0.1"):
            ContextConfig(cleanup_timeout=0.0)

    def test_context_config_custom_values(self):
        """Test ContextConfig with custom values"""
        config = ContextConfig(
            connect_timeout=15.0,
            cleanup_timeout=8.0,
            cleanup_strategy=CleanupStrategy.FORCE,
            suppress_cleanup_errors=False,
            max_tracked_resources=50
        )

        assert config.connect_timeout == 15.0
        assert config.cleanup_timeout == 8.0
        assert config.cleanup_strategy == CleanupStrategy.FORCE
        assert config.suppress_cleanup_errors is False
        assert config.max_tracked_resources == 50

class TestTunnelGroupConfig:
    def test_tunnel_group_config_creation_with_defaults(self):
        """Test TunnelGroupConfig creation with default values"""
        config = TunnelGroupConfig(group_name="test-group")

        assert config.group_name == "test-group"
        assert config.max_tunnels == 10
        assert config.parallel_cleanup is True
        assert config.cleanup_order == "lifo"

    def test_tunnel_group_config_validation(self):
        """Test TunnelGroupConfig validation"""
        config = TunnelGroupConfig(group_name="test-group-1")
        assert config.group_name == "test-group-1"
        assert config.max_tunnels == 10
        assert config.cleanup_order == "lifo"

        with pytest.raises(ValidationError, match="alphanumeric characters"):
            TunnelGroupConfig(group_name="test@group")

        with pytest.raises(ValidationError, match="fifo"):
            TunnelGroupConfig(group_name="test", cleanup_order="invalid")

    def test_tunnel_group_config_custom_values(self):
        """Test TunnelGroupConfig with custom values"""
        config = TunnelGroupConfig(
            group_name="custom_group",
            max_tunnels=20,
            parallel_cleanup=False,
            cleanup_order="fifo"
        )

        assert config.group_name == "custom_group"
        assert config.max_tunnels == 20
        assert config.parallel_cleanup is False
        assert config.cleanup_order == "fifo"

class TestResourceTracker:
    def test_resource_tracker_creation(self):
        """Test ResourceTracker creation and basic operations"""
        tracker = ResourceTracker(max_resources=5)

        assert len(tracker.resources) == 0
        assert len(tracker.cleanup_callbacks) == 0
        assert tracker.max_resources == 5

    def test_resource_registration(self):
        """Test resource registration and cleanup"""
        tracker = ResourceTracker()

        mock_resource = "test_resource"
        cleanup_called = False

        def cleanup_callback():
            nonlocal cleanup_called
            cleanup_called = True

        tracker.register_resource("res1", mock_resource, cleanup_callback)

        assert len(tracker.resources) == 1
        assert tracker.resources["res1"] == mock_resource
        assert "res1" in tracker.cleanup_callbacks

        errors = tracker.cleanup_all()
        assert len(errors) == 0
        assert cleanup_called is True
        assert len(tracker.resources) == 0

    def test_resource_cleanup_all(self):
        """Test cleanup all resources"""
        tracker = ResourceTracker()

        cleanup_calls = []

        def make_cleanup(resource_id):
            def cleanup():
                cleanup_calls.append(resource_id)
            return cleanup

        tracker.register_resource("res1", "resource1", make_cleanup("res1"))
        tracker.register_resource("res2", "resource2", make_cleanup("res2"))
        tracker.register_resource("res3", "resource3", make_cleanup("res3"))

        errors = tracker.cleanup_all()

        assert len(errors) == 0
        assert len(cleanup_calls) == 3
        assert cleanup_calls == ["res3", "res2", "res1"]
        assert len(tracker.resources) == 0

    def test_resource_cleanup_with_errors(self):
        """Test cleanup handling errors"""
        tracker = ResourceTracker()

        def good_cleanup():
            pass

        def bad_cleanup():
            raise ValueError("Cleanup failed")

        tracker.register_resource("good", "resource1", good_cleanup)
        tracker.register_resource("bad", "resource2", bad_cleanup)

        errors = tracker.cleanup_all()

        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)
        assert str(errors[0]) == "Cleanup failed"
        assert len(tracker.resources) == 0

    def test_max_resources_limit(self):
        """Test maximum resources limit"""
        tracker = ResourceTracker(max_resources=2)

        tracker.register_resource("res1", "resource1", lambda: None)
        tracker.register_resource("res2", "resource2", lambda: None)

        with pytest.raises(ValueError, match="Maximum resources"):
            tracker.register_resource("res3", "resource3", lambda: None)

    def test_unregister_resource(self):
        """Test resource unregistration"""
        tracker = ResourceTracker()

        tracker.register_resource("res1", "resource1", lambda: None)
        assert len(tracker.resources) == 1

        tracker.unregister_resource("res1")
        assert len(tracker.resources) == 0
        assert len(tracker.cleanup_callbacks) == 0

        tracker.unregister_resource("nonexistent")
