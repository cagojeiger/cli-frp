import asyncio
import time
from unittest.mock import Mock, patch

import pytest

from frp_wrapper.common.context import (
    AsyncProcessManager,
    ContextManagerMixin,
    NestedContextManager,
    ResourceLeakDetector,
    TimeoutContext,
    timeout_context,
)
from frp_wrapper.common.context_config import ContextConfig
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

    def test_nested_context_manager_exception_suppression(self):
        """Test NestedContextManager exception suppression in __exit__"""
        nested = NestedContextManager()
        
        mock_cm1 = Mock()
        mock_cm1.__enter__ = Mock(return_value="result1")
        mock_cm1.__exit__ = Mock(return_value=True)  # Suppress exception
        
        mock_cm2 = Mock()
        mock_cm2.__enter__ = Mock(return_value="result2")
        mock_cm2.__exit__ = Mock(return_value=False)  # Don't suppress
        
        with nested:
            nested.enter_context(mock_cm1)
            nested.enter_context(mock_cm2)
        
        mock_cm1.__exit__.assert_called_once()
        mock_cm2.__exit__.assert_called_once()

    def test_nested_context_manager_cleanup_exception(self):
        """Test NestedContextManager handles cleanup exceptions"""
        nested = NestedContextManager()
        
        mock_cm = Mock()
        mock_cm.__enter__ = Mock(return_value="result")
        mock_cm.__exit__ = Mock(side_effect=Exception("Cleanup failed"))
        
        with patch('frp_wrapper.common.context.logger') as mock_logger:
            with nested:
                nested.enter_context(mock_cm)
            
            mock_logger.error.assert_called_once()
            assert "Error during nested context cleanup" in str(mock_logger.error.call_args)


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
        resource1 = Mock(spec=["cleanup"])
        resource1.cleanup = Mock()

        resource2 = Mock(spec=["close"])
        resource2.close = Mock()

        resource3 = Mock(spec=["__exit__"])
        resource3.__exit__ = Mock()

        ResourceLeakDetector.register_resource(resource1)
        ResourceLeakDetector.register_resource(resource2)
        ResourceLeakDetector.register_resource(resource3)

        ResourceLeakDetector.cleanup_leaked()

        resource1.cleanup.assert_called_once()
        resource2.close.assert_called_once()
        resource3.__exit__.assert_called_once()

    def test_resource_leak_detector_cleanup_with_close_method(self):
        """Test ResourceLeakDetector cleanup with close method"""
        class MockResource:
            def __init__(self):
                self.close_called = False
            
            def close(self):
                self.close_called = True

        mock_resource = MockResource()
        ResourceLeakDetector.register_resource(mock_resource)

        with patch('frp_wrapper.common.context.logger') as mock_logger:
            ResourceLeakDetector.cleanup_leaked()

            assert mock_resource.close_called
            mock_logger.warning.assert_called()
            assert "Cleaned up leaked resource" in str(mock_logger.warning.call_args)

    def test_resource_leak_detector_cleanup_with_exit_method(self):
        """Test ResourceLeakDetector cleanup with __exit__ method"""
        class MockResource:
            def __init__(self):
                self.exit_called = False
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.exit_called = True

        mock_resource = MockResource()
        ResourceLeakDetector.register_resource(mock_resource)

        with patch('frp_wrapper.common.context.logger') as mock_logger:
            ResourceLeakDetector.cleanup_leaked()

            assert mock_resource.exit_called
            mock_logger.warning.assert_called()
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any("MockResource" in call for call in warning_calls)

    def test_resource_leak_detector_cleanup_failure(self):
        """Test ResourceLeakDetector handles cleanup failures"""
        mock_resource = Mock()
        mock_resource.cleanup = Mock(side_effect=Exception("Cleanup failed"))
        
        ResourceLeakDetector.register_resource(mock_resource)
        
        with patch('frp_wrapper.common.context.logger') as mock_logger:
            ResourceLeakDetector.cleanup_leaked()
            
            mock_logger.error.assert_called_once()
            assert "Failed to clean up leaked resource" in str(mock_logger.error.call_args)


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
        with patch("frp_wrapper.common.context.logger") as mock_logger:
            with TimeoutContext(0.1):
                time.sleep(0.2)  # Exceed timeout

            mock_logger.warning.assert_called()

    def test_timeout_context_check_timeout_within_limit(self):
        """Test TimeoutContext check_timeout when within limit"""
        with TimeoutContext(1.0) as ctx:
            time.sleep(0.1)
            ctx.check_timeout()

    def test_timeout_context_exit_with_timeout_warning(self):
        """Test TimeoutContext __exit__ logs warning when timeout exceeded"""
        with patch('frp_wrapper.common.context.logger') as mock_logger:
            with TimeoutContext(0.1):
                time.sleep(0.2)
            
            mock_logger.warning.assert_called_once()
            assert "Context exceeded timeout" in str(mock_logger.warning.call_args)


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

    def test_context_manager_mixin_cleanup_errors_suppressed_with_logging(self):
        """Test ContextManagerMixin with cleanup errors suppressed and logged"""
        
        class TestClass(ContextManagerMixin):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
        
        config = ContextConfig(suppress_cleanup_errors=True, log_cleanup_errors=True)
        obj = TestClass(context_config=config)
        
        def failing_cleanup():
            raise Exception("Cleanup failed")
        
        obj._resource_tracker.register_resource("test", "resource", failing_cleanup)
        
        with patch('frp_wrapper.common.context.logger') as mock_logger:
            try:
                with obj:
                    pass
            except Exception:
                pass  # Should be suppressed
            
            # Should log the error but not raise - check for any error logging
            assert mock_logger.error.call_count >= 1

    def test_context_manager_mixin_cleanup_exception_handling(self):
        """Test ContextManagerMixin handles cleanup exceptions"""
        
        class TestClass(ContextManagerMixin):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
        
        config = ContextConfig(suppress_cleanup_errors=False, log_cleanup_errors=True)
        obj = TestClass(context_config=config)
        
        def failing_cleanup():
            raise Exception("Tracker failed")
        
        obj._resource_tracker.register_resource("test", "resource", failing_cleanup)
        
        with patch('frp_wrapper.common.context.logger') as mock_logger:
            with pytest.raises(Exception, match="Tracker failed"):
                with obj:
                    pass
            
            mock_logger.error.assert_called()


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


class TestAsyncProcessManager:
    @pytest.mark.asyncio
    async def test_async_process_manager_start_success(self):
        """Test AsyncProcessManager successful start"""
        manager = AsyncProcessManager("/usr/bin/echo", "/tmp/test.conf")
        
        with patch('asyncio.create_subprocess_exec') as mock_create:
            mock_process = Mock()
            mock_create.return_value = mock_process
            
            result = await manager.start()
            
            assert result is True
            assert manager._process == mock_process
            mock_create.assert_called_once_with(
                "/usr/bin/echo", "-c", "/tmp/test.conf",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

    @pytest.mark.asyncio
    async def test_async_process_manager_start_failure(self):
        """Test AsyncProcessManager start failure"""
        manager = AsyncProcessManager("/nonexistent/binary", "/tmp/test.conf")
        
        with patch('asyncio.create_subprocess_exec', side_effect=Exception("Start failed")):
            with patch('frp_wrapper.common.context.logger') as mock_logger:
                result = await manager.start()
                
                assert result is False
                mock_logger.error.assert_called_once()
                assert "Failed to start async process" in str(mock_logger.error.call_args)

    @pytest.mark.asyncio
    async def test_async_process_manager_stop_with_timeout(self):
        """Test AsyncProcessManager stop with timeout"""
        manager = AsyncProcessManager("/usr/bin/echo", "/tmp/test.conf")
        
        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.kill = Mock()
        mock_process.wait = Mock(return_value=None)
        manager._process = mock_process
        
        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
            with patch.object(mock_process, 'wait', return_value=asyncio.Future()) as mock_wait:
                mock_wait.return_value.set_result(None)
                
                result = await manager.stop()
                
                assert result is True
                mock_process.terminate.assert_called_once()
                mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_process_manager_stop_failure(self):
        """Test AsyncProcessManager stop failure"""
        manager = AsyncProcessManager("/usr/bin/echo", "/tmp/test.conf")
        
        mock_process = Mock()
        mock_process.terminate = Mock(side_effect=Exception("Stop failed"))
        manager._process = mock_process
        
        with patch('frp_wrapper.common.context.logger') as mock_logger:
            result = await manager.stop()
            
            assert result is False
            mock_logger.error.assert_called_once()
            assert "Failed to stop async process" in str(mock_logger.error.call_args)

    @pytest.mark.asyncio
    async def test_async_process_manager_context_manager(self):
        """Test AsyncProcessManager as async context manager"""
        manager = AsyncProcessManager("/usr/bin/echo", "/tmp/test.conf")
        
        with patch.object(manager, 'start', return_value=True) as mock_start:
            with patch.object(manager, 'stop', return_value=True) as mock_stop:
                async with manager as ctx:
                    assert ctx == manager
                
                mock_start.assert_called_once()
                mock_stop.assert_called_once()
