from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from pydantic import BaseModel, Field, ConfigDict, field_validator

class CleanupStrategy(str, Enum):
    """Resource cleanup strategy"""
    GRACEFUL = "graceful"        # Try graceful shutdown first
    FORCE = "force"              # Force immediate shutdown
    GRACEFUL_THEN_FORCE = "graceful_then_force"  # Graceful with fallback

class ContextConfig(BaseModel):
    """Pydantic configuration for Context Manager behavior"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    connect_timeout: float = Field(default=10.0, ge=0.1, le=60.0, description="Connection timeout in seconds")
    cleanup_timeout: float = Field(default=5.0, ge=0.1, le=30.0, description="Cleanup timeout in seconds")
    graceful_shutdown_timeout: float = Field(default=3.0, ge=0.1, le=10.0, description="Graceful shutdown timeout")

    cleanup_strategy: CleanupStrategy = Field(default=CleanupStrategy.GRACEFUL_THEN_FORCE)
    suppress_cleanup_errors: bool = Field(default=True, description="Suppress errors during cleanup")
    log_cleanup_errors: bool = Field(default=True, description="Log cleanup errors")

    track_resources: bool = Field(default=True, description="Enable resource tracking")
    max_tracked_resources: int = Field(default=100, ge=1, le=1000, description="Maximum resources to track")

    @field_validator('connect_timeout', 'cleanup_timeout', 'graceful_shutdown_timeout')
    @classmethod
    def validate_positive_timeout(cls, v: float) -> float:
        """Ensure timeouts are positive"""
        if v <= 0:
            raise ValueError("Input should be greater than or equal to 0.1")
        return v

class TunnelGroupConfig(BaseModel):
    """Configuration for TunnelGroup context manager"""

    model_config = ConfigDict(str_strip_whitespace=True)

    group_name: str = Field(..., min_length=1, max_length=50, description="Group identifier")
    max_tunnels: int = Field(default=10, ge=1, le=50, description="Maximum tunnels in group")
    parallel_cleanup: bool = Field(default=True, description="Clean up tunnels in parallel")
    cleanup_order: str = Field(default="lifo", pattern="^(lifo|fifo)$", description="Cleanup order: lifo or fifo")

    @field_validator('group_name')
    @classmethod
    def validate_group_name(cls, v: str) -> str:
        """Validate group name format"""
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Group name must contain only alphanumeric characters, hyphens, and underscores")
        return v

class ResourceTracker(BaseModel):
    """Pydantic model for tracking resources"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    resources: Dict[str, Any] = Field(default_factory=dict)
    cleanup_callbacks: Dict[str, Callable] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    max_resources: int = Field(default=100, ge=1)

    def register_resource(self, resource_id: str, resource: Any, cleanup_callback: Callable) -> None:
        """Register a resource for tracking"""
        if len(self.resources) >= self.max_resources:
            raise ValueError(f"Maximum resources ({self.max_resources}) exceeded")

        self.resources[resource_id] = resource
        self.cleanup_callbacks[resource_id] = cleanup_callback

    def unregister_resource(self, resource_id: str) -> None:
        """Unregister a resource"""
        self.resources.pop(resource_id, None)
        self.cleanup_callbacks.pop(resource_id, None)

    def cleanup_all(self) -> List[Exception]:
        """Clean up all resources in LIFO order"""
        errors = []
        resource_ids = list(self.resources.keys())
        
        for resource_id in reversed(resource_ids):
            try:
                cleanup_callback = self.cleanup_callbacks.get(resource_id)
                if cleanup_callback:
                    cleanup_callback()
            except Exception as e:
                errors.append(e)
            finally:
                self.unregister_resource(resource_id)
        
        return errors
