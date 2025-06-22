import pytest
import threading
import time
from unittest.mock import Mock, patch

from frp_wrapper.common.context import (
    NestedContextManager, ResourceLeakDetector, AsyncProcessManager,
    TimeoutContext, ContextManagerMixin, timeout_context
)
from frp_wrapper.common.context_config import ContextConfig, CleanupStrategy
from frp_wrapper.common.exceptions import FRPWrapperError

class TestNestedContextManager:
    def test_nested_context_manager_creation(self):
        """Test NestedContextManager creation"""
        manager = NestedContextManager()
        assert len(manager._stack) == 0

    def test_enter_context_success(self):
        """Test entering context successfully"""
        manager = NestedContextManager()
        
        mock_cm = Mock()
        mock_cm.__enter__ = Mock(return_value="test_result")
        
        result = manager.enter_context(mock_cm)
        
        assert result == "test_result"
        assert len(manager._stack) == 1
        assert manager._stack[0] == mock_cm
        mock_cm.__enter__.assert_called_once()

    def test_enter_context_failure(self):
        """Test entering context with failure"""
        manager = NestedContextManager()
        
        mock_cm = Mock()
        mock_cm.__enter__ = Mock(side_effect=ValueError("Enter failed"))
        
        with pytest.raises(ValueError, match="Enter failed"):
            manager.enter_context(mock_cm)
        
        assert len(manager._stack) == 0

    def test_context_manager_exit_lifo_order(self):
        """Test context manager exit in LIFO order"""
        exit_order = []
        
        def make_mock_cm(name):
            mock_cm = Mock()
            mock_cm.__enter__ = Mock(return_value=name)
            mock_cm.__exit__ = Mock(side_effect=lambda *args: exit_order.append(name))
            return mock_cm

        with NestedContextManager() as manager:
            manager.enter_context(make_mock_cm("first"))
            manager.enter_context(make_mock_cm("second"))
            manager.enter_context(make_mock_cm("third"))

        assert exit_order == ["third", "second", "first"]

    def test_context_manager_exit_with_errors(self):
        """Test context manager exit handling errors"""
        def make_mock_cm(name, should_fail=False):
            mock_cm = Mock()
            mock_cm.__enter__ = Mock(return_value=name)
            if should_fail:
                mock_cm.__exit__ = Mock(side_effect=ValueError(f"{name} exit failed"))
            else:
                mock_cm.__exit__ = Mock(return_value=None)
            return mock_cm

        with NestedContextManager() as manager:
            manager.enter_context(make_mock_cm("good1"))
            manager.enter_context(make_mock_cm("bad", should_fail=True))
            manager.enter_context(make_mock_cm("good2"))


class TestResourceLeakDetector:
    def test_resource_registration(self):
        """Test resource registration and unregistration"""
        initial_count = ResourceLeakDetector.get_active_count()
        
        resource = Mock()
        ResourceLeakDetector.register_resource(resource)
        
        assert ResourceLeakDetector.get_active_count() == initial_count + 1
        
        ResourceLeakDetector.unregister_resource(resource)
        assert ResourceLeakDetector.get_active_count() == initial_count

    def test_cleanup_leaked_resources(self):
        """Test cleanup of leaked resources"""
        resource1 = Mock(spec=['cleanup'])
        resource1.cleanup = Mock()
        
        resource2 = Mock(spec=['close'])
        resource2.close = Mock()
        
        resource3 = Mock(spec=['__exit__'])
        resource3.__exit__ = Mock()
        
        ResourceLeakDetector.register_resource(resource1)
        ResourceLeakDetector.register_resource(resource2)
        ResourceLeakDetector.register_resource(resource3)
        
        ResourceLeakDetector.cleanup_leaked()
        
        resource1.cleanup.assert_called_once()
        resource2.close.assert_called_once()
        resource3.__exit__.assert_called_once()

class TestTimeoutContext:
    def test_timeout_context_creation(self):
        """Test TimeoutContext creation"""
        ctx = TimeoutContext(5.0)
        assert ctx.timeout == 5.0
        assert ctx._start_time is None

    def test_timeout_context_normal_operation(self):
        """Test TimeoutContext normal operation"""
        with TimeoutContext(1.0) as ctx:
            assert ctx._start_time is not None
            time.sleep(0.1)  # Short operation
            ctx.check_timeout()  # Should not raise

    def test_timeout_context_timeout_exceeded(self):
        """Test TimeoutContext when timeout is exceeded"""
        with pytest.raises(FRPWrapperError, match="Operation timed out"):
            with TimeoutContext(0.1) as ctx:
                time.sleep(0.2)  # Longer than timeout
                ctx.check_timeout()

    def test_timeout_context_warning_on_exit(self):
        """Test TimeoutContext logs warning on exit if timeout exceeded"""
        with patch('frp_wrapper.common.context.logger') as mock_logger:
            with TimeoutContext(0.1):
                time.sleep(0.2)  # Exceed timeout
            
            mock_logger.warning.assert_called()

class TestContextManagerMixin:
    def test_context_manager_mixin_initialization(self):
        """Test ContextManagerMixin initialization"""
        class TestClass(ContextManagerMixin):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

        config = ContextConfig(cleanup_timeout=2.0)
        obj = TestClass(context_config=config)
        
        assert obj.context_config.cleanup_timeout == 2.0
        assert obj._in_context is False

    def test_context_manager_mixin_enter_exit(self):
        """Test ContextManagerMixin enter and exit"""
        class TestClass(ContextManagerMixin):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

        obj = TestClass()
        
        result = obj.__enter__()
        assert result == obj
        assert obj._in_context is True
        
        obj.__exit__(None, None, None)
        assert obj._in_context is False

    def test_context_manager_mixin_cleanup_errors_suppressed(self):
        """Test ContextManagerMixin with cleanup errors suppressed"""
        class TestClass(ContextManagerMixin):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

        config = ContextConfig(suppress_cleanup_errors=True)
        obj = TestClass(context_config=config)
        
        def failing_cleanup():
            raise ValueError("Cleanup failed")
        
        obj._resource_tracker.register_resource("test", "resource", failing_cleanup)
        
        with obj:
            pass

    def test_context_manager_mixin_cleanup_errors_not_suppressed(self):
        """Test ContextManagerMixin with cleanup errors not suppressed"""
        class TestClass(ContextManagerMixin):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

        config = ContextConfig(suppress_cleanup_errors=False, log_cleanup_errors=False)
        obj = TestClass(context_config=config)
        
        def failing_cleanup():
            raise ValueError("Cleanup failed")
        
        obj._resource_tracker.register_resource("test", "resource", failing_cleanup)
        
        with pytest.raises(ValueError, match="Cleanup failed"):
            with obj:
                pass

class TestTimeoutContextFunction:
    def test_timeout_context_function(self):
        """Test timeout_context convenience function"""
        with timeout_context(1.0) as ctx:
            assert isinstance(ctx, TimeoutContext)
            assert ctx.timeout == 1.0
            time.sleep(0.1)  # Short operation
            ctx.check_timeout()  # Should not raise

    def test_timeout_context_function_timeout(self):
        """Test timeout_context function with timeout"""
        with pytest.raises(FRPWrapperError):
            with timeout_context(0.1) as ctx:
                time.sleep(0.2)
                ctx.check_timeout()
