import asyncio
import atexit
import logging
import threading
import time
import weakref
from collections.abc import Iterator
from contextlib import contextmanager
from types import TracebackType
from typing import Any, Literal

from .context_config import ContextConfig, ResourceTracker
from .exceptions import FRPWrapperError

logger = logging.getLogger(__name__)


class NestedContextManager:
    """Handles nested context managers with proper cleanup"""

    def __init__(self) -> None:
        self._stack: list[Any] = []
        self._lock = threading.Lock()

    def enter_context(self, context_manager: Any) -> Any:
        """Enter a context manager and add to cleanup stack"""
        with self._lock:
            try:
                result = context_manager.__enter__()
                self._stack.append(context_manager)
                return result
            except Exception:
                raise

    def __enter__(self) -> "NestedContextManager":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Exit all contexts in LIFO order"""
        with self._lock:
            suppressed_exception = False

            while self._stack:
                context_manager = self._stack.pop()
                try:
                    if context_manager.__exit__(exc_type, exc_val, exc_tb):
                        suppressed_exception = True
                        exc_type = exc_val = exc_tb = None
                except Exception as cleanup_exc:
                    logger.error(f"Error during nested context cleanup: {cleanup_exc}")

            return suppressed_exception


class ResourceLeakDetector:
    """Detects and prevents resource leaks"""

    _active_resources: weakref.WeakSet[Any] = weakref.WeakSet()
    _lock = threading.Lock()

    @classmethod
    def register_resource(cls, resource: Any) -> None:
        """Register a resource for leak detection"""
        with cls._lock:
            cls._active_resources.add(resource)

    @classmethod
    def unregister_resource(cls, resource: Any) -> None:
        """Unregister a resource"""
        with cls._lock:
            cls._active_resources.discard(resource)

    @classmethod
    def get_active_count(cls) -> int:
        """Get count of active resources"""
        with cls._lock:
            return len(cls._active_resources)

    @classmethod
    def cleanup_leaked(cls) -> None:
        """Clean up any leaked resources"""
        with cls._lock:
            leaked_resources = list(cls._active_resources)

        for resource in leaked_resources:
            try:
                if hasattr(resource, "cleanup"):
                    resource.cleanup()
                elif hasattr(resource, "close"):
                    resource.close()
                elif hasattr(resource, "__exit__"):
                    resource.__exit__(None, None, None)
                logger.warning(f"Cleaned up leaked resource: {type(resource).__name__}")
            except Exception as e:
                logger.error(f"Failed to clean up leaked resource: {e}")


atexit.register(ResourceLeakDetector.cleanup_leaked)


class AsyncProcessManager:
    """Async version of ProcessManager"""

    def __init__(self, binary_path: str, config_path: str):
        self.binary_path = binary_path
        self.config_path = config_path
        self._process: asyncio.subprocess.Process | None = None

    async def __aenter__(self) -> "AsyncProcessManager":
        """Async context entry"""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context exit"""
        await self.stop()

    async def start(self) -> bool:
        """Start the async process"""
        try:
            self._process = await asyncio.create_subprocess_exec(
                self.binary_path,
                "-c",
                self.config_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to start async process: {e}")
            return False

    async def stop(self) -> bool:
        """Stop the async process"""
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
                return True
            except TimeoutError:
                self._process.kill()
                await self._process.wait()
                return True
            except Exception as e:
                logger.error(f"Failed to stop async process: {e}")
                return False
        return True


class TimeoutContext:
    """Context manager with timeout support"""

    def __init__(self, timeout: float):
        self.timeout = timeout
        self._start_time: float | None = None

    def __enter__(self) -> "TimeoutContext":
        self._start_time = time.time()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        if self._start_time:
            elapsed = time.time() - self._start_time
            if elapsed > self.timeout:
                logger.warning(
                    f"Context exceeded timeout: {elapsed:.2f}s > {self.timeout:.2f}s"
                )
        return False

    def check_timeout(self) -> None:
        """Check if timeout has been exceeded"""
        if self._start_time:
            elapsed = time.time() - self._start_time
            if elapsed > self.timeout:
                raise FRPWrapperError(f"Operation timed out after {elapsed:.2f}s")


class ContextManagerMixin:
    """Mixin to add enhanced context manager capabilities"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        context_config = kwargs.pop("context_config", None)
        super().__init__(*args, **kwargs)
        self.context_config = context_config or ContextConfig()
        self._resource_tracker = ResourceTracker()
        self._in_context = False

    def __enter__(self) -> Any:
        """Enhanced context manager entry"""
        self._in_context = True
        ResourceLeakDetector.register_resource(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        """Enhanced context manager exit with error handling"""
        self._in_context = False
        ResourceLeakDetector.unregister_resource(self)

        try:
            cleanup_errors = self._resource_tracker.cleanup_all()

            if cleanup_errors and not self.context_config.suppress_cleanup_errors:
                if self.context_config.log_cleanup_errors:
                    for error in cleanup_errors:
                        logger.error(f"Cleanup error: {error}")

                if cleanup_errors:
                    raise cleanup_errors[0]

        except Exception as cleanup_exc:
            if self.context_config.log_cleanup_errors:
                logger.error(f"Context manager cleanup failed: {cleanup_exc}")

            if not self.context_config.suppress_cleanup_errors:
                raise cleanup_exc

        return False


@contextmanager
def timeout_context(timeout: float) -> Iterator[TimeoutContext]:
    """Convenience function for timeout context"""
    with TimeoutContext(timeout) as ctx:
        yield ctx
