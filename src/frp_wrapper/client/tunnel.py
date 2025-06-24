"""Tunnel models, management, and routing for FRP client.

This module combines all tunnel-related functionality:
- Tunnel models (HTTP, TCP)
- Tunnel manager and registry
- Path routing and conflict detection
- Process management for tunnels
"""

import logging
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import lru_cache
from re import Pattern
from typing import TYPE_CHECKING, Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import ConfigBuilder
from .process import ProcessManager

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Tunnel Models (from models.py)
# =============================================================================


class TunnelType(str, Enum):
    """Tunnel type enumeration."""

    HTTP = "http"
    TCP = "tcp"


class TunnelStatus(str, Enum):
    """Tunnel status enumeration."""

    PENDING = "pending"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CLOSED = "closed"


class BaseTunnel(BaseModel):
    """Base tunnel model with immutable design pattern and context manager support."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="allow")

    id: str = Field(min_length=1, description="Unique tunnel identifier")
    tunnel_type: TunnelType = Field(description="Type of tunnel (HTTP/TCP)")
    local_port: int = Field(ge=1, le=65535, description="Local port to expose")
    status: TunnelStatus = Field(
        default=TunnelStatus.PENDING, description="Current tunnel status"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Tunnel creation timestamp"
    )
    connected_at: datetime | None = Field(
        default=None, description="Connection timestamp"
    )

    @property
    def manager(self) -> Any | None:
        """Get associated tunnel manager."""
        return getattr(self, "_manager", None)

    def with_status(self, status: TunnelStatus) -> "BaseTunnel":
        """Create new tunnel instance with updated status (immutable pattern).

        Args:
            status: New tunnel status

        Returns:
            New tunnel instance with updated status
        """
        update_data: dict[str, Any] = {"status": status}

        if status == TunnelStatus.CONNECTED and self.connected_at is None:
            update_data["connected_at"] = datetime.now()

        return self.model_copy(update=update_data)

    def with_manager(self, manager: Any) -> "BaseTunnel":
        """Associate tunnel with a manager for context management.

        Args:
            manager: TunnelManager instance to associate with

        Returns:
            New tunnel instance with manager association
        """
        new_tunnel = self.model_copy()
        object.__setattr__(new_tunnel, "_manager", manager)
        return new_tunnel

    def __enter__(self) -> "BaseTunnel":
        """Enter context manager - start the tunnel.

        Returns:
            Self for method chaining

        Raises:
            RuntimeError: If no manager is associated or tunnel start fails
        """
        if self.manager is None:
            raise RuntimeError(
                f"No manager associated with tunnel {self.id}. "
                "Use tunnel.with_manager(manager) first."
            )

        success = self.manager.start_tunnel(self.id)
        if not success:
            raise RuntimeError(f"Failed to start tunnel {self.id}")

        # Return updated tunnel instance from manager
        updated_tunnel = self.manager.registry.get_tunnel(self.id)
        if updated_tunnel is None:
            raise RuntimeError(f"Tunnel {self.id} not found after start")

        return cast(BaseTunnel, updated_tunnel.with_manager(self.manager))

    def __exit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Exit context manager - stop and remove the tunnel.

        Args:
            _exc_type: Exception type if an exception was raised
            _exc_val: Exception value if an exception was raised
            _exc_tb: Exception traceback if an exception was raised
        """
        if self.manager is not None:
            try:
                # Get current tunnel status from manager
                current_tunnel = self.manager.registry.get_tunnel(self.id)
                if current_tunnel and current_tunnel.status == TunnelStatus.CONNECTED:
                    self.manager.stop_tunnel(self.id)
                self.manager.remove_tunnel(self.id)
            except Exception:
                # Suppress exceptions during cleanup to avoid masking original exceptions
                pass


class TCPTunnel(BaseTunnel):
    """TCP tunnel for raw port forwarding."""

    tunnel_type: Literal[TunnelType.TCP] = TunnelType.TCP
    remote_port: int | None = Field(
        default=None, ge=1, le=65535, description="Remote port (auto-assigned if None)"
    )

    @property
    def endpoint(self) -> str | None:
        """Get tunnel endpoint URL.

        Returns:
            Endpoint URL if connected, None otherwise
        """
        if self.status != TunnelStatus.CONNECTED or self.remote_port is None:
            return None

        return f"{{server_host}}:{self.remote_port}"


class HTTPTunnel(BaseTunnel):
    """HTTP tunnel with path-based routing using FRP locations feature."""

    tunnel_type: Literal[TunnelType.HTTP] = TunnelType.HTTP
    path: str = Field(description="URL path for routing (without leading slash)")
    custom_domains: list[str] = Field(
        default_factory=list, description="Custom domains for tunnel"
    )
    strip_path: bool = Field(
        default=True, description="Strip path prefix when forwarding"
    )
    websocket: bool = Field(default=True, description="Enable WebSocket support")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate path format."""
        if v.startswith("/"):
            raise ValueError(
                "Path should not start with '/' - it will be added automatically"
            )

        # Enhanced security: More restrictive character validation
        # Allow only: alphanumeric, hyphens, underscores, single slashes, single dots, and single wildcards
        if not re.match(r"^[a-zA-Z0-9/_\-.*]+$", v):
            raise ValueError(
                "Path must contain only alphanumeric characters, hyphens, underscores, slashes, dots, and wildcards (*)"
            )

        # Security checks for path traversal and malicious patterns
        security_checks = [
            ("..", "Path cannot contain '..' (directory traversal)"),
            ("./", "Path cannot contain './' (relative path)"),
            ("***", "Path cannot contain triple wildcards"),
            ("**/**", "Path cannot contain nested recursive wildcards"),
            ("/**/", "Path cannot contain standalone recursive wildcards"),
        ]

        for pattern, error_msg in security_checks:
            if pattern in v:
                raise ValueError(error_msg)

        # Path format validation
        if v.endswith("/"):
            raise ValueError("Path cannot end with '/'")

        if "//" in v:
            raise ValueError("Path cannot contain consecutive slashes")

        # Additional security: prevent control characters and ensure reasonable length
        MIN_PRINTABLE_CHAR = 32  # ASCII printable characters start at 32
        MAX_PATH_LENGTH = 200  # Reasonable path length limit

        if any(ord(char) < MIN_PRINTABLE_CHAR for char in v):
            raise ValueError("Path cannot contain control characters")

        if len(v) > MAX_PATH_LENGTH:
            raise ValueError(f"Path too long (maximum {MAX_PATH_LENGTH} characters)")

        return v

    @property
    def locations(self) -> list[str]:
        """Get FRP locations configuration.

        Returns:
            List of location paths for FRP configuration
        """
        return [f"/{self.path}"]

    @property
    def url(self) -> str | None:
        """Get tunnel public URL.

        Returns:
            Public URL if connected and has domains, None otherwise
        """
        if self.status != TunnelStatus.CONNECTED or not self.custom_domains:
            return None

        domain = self.custom_domains[0]
        return f"https://{domain}/{self.path}/"


class TunnelConfig(BaseModel):
    """Configuration for creating and managing tunnels."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    server_host: str = Field(min_length=1, description="FRP server hostname")
    auth_token: str | None = Field(None, description="Authentication token")
    default_domain: str | None = Field(
        None, description="Default domain for HTTP tunnels"
    )
    max_tunnels: int = Field(
        default=10, ge=1, le=100, description="Maximum concurrent tunnels"
    )

    @field_validator("server_host")
    @classmethod
    def validate_server_host(cls, v: str) -> str:
        """Validate server hostname format."""
        if not v.replace(".", "").replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Hostname must contain only alphanumeric characters, dots, hyphens, and underscores"
            )
        return v


# =============================================================================
# Path Routing (from routing.py)
# =============================================================================


# Cache sizes optimized for typical usage patterns:
# - Pattern compilation: 64 patterns should cover most common routing scenarios
# - Path normalization: 512 paths to handle high-traffic applications with many endpoints
@lru_cache(maxsize=64)
def _compile_pattern_cached(pattern: str) -> Pattern[str]:
    """Compile pattern to regex with caching for performance.

    Cache size: 64 patterns (typical applications use 10-50 unique path patterns)
    """
    escaped = re.escape(pattern)
    escaped = escaped.replace(r"\*\*", ".*")  # ** matches everything including /
    escaped = escaped.replace(r"\*", "[^/]*")  # * matches anything except /
    return re.compile(f"^{escaped}$")


@lru_cache(maxsize=512)
def _normalize_slashes_cached(path: str) -> str:
    """Normalize multiple slashes with caching for performance.

    Cache size: 512 paths (handles high-traffic apps with many unique endpoints)
    """
    return re.sub(r"/+", "/", path)


class PathConflictType(str, Enum):
    """Types of path conflicts"""

    EXACT_MATCH = "exact_match"
    WILDCARD_OVERLAP = "wildcard_overlap"
    PARENT_CHILD = "parent_child"


@dataclass
class PathConflict:
    """Represents a path conflict between tunnels"""

    conflict_type: PathConflictType
    existing_path: str
    new_path: str
    existing_tunnel_id: str
    message: str


class PathPattern:
    """Represents a path pattern with wildcard support"""

    def __init__(self, pattern: str):
        """Initialize path pattern.

        Args:
            pattern: Path pattern (e.g., "/api/*", "/app/**", "/exact")
        """
        self.pattern = pattern
        self.is_wildcard = "*" in pattern
        self.is_recursive = "**" in pattern
        self._regex = self._compile_pattern()

    def _compile_pattern(self) -> Pattern[str]:
        """Compile pattern to regex for matching"""
        return _compile_pattern_cached(self.pattern)

    def matches(self, path: str) -> bool:
        """Check if path matches this pattern"""
        return bool(self._regex.match(path))

    def conflicts_with(self, other: "PathPattern") -> bool:
        """Check if this pattern conflicts with another pattern"""
        if self.pattern == other.pattern:
            return True

        if self.is_wildcard or other.is_wildcard:
            # Check if patterns can potentially match the same paths
            return self._patterns_overlap(other)

        return False

    def _patterns_overlap(self, other: "PathPattern") -> bool:
        """Check if two patterns can potentially match overlapping paths"""
        # Extract base paths (non-wildcard parts)
        self_base = self.pattern.split("*")[0].rstrip("/")
        other_base = other.pattern.split("*")[0].rstrip("/")

        # If one is a prefix of the other, they might conflict
        if self_base.startswith(other_base) or other_base.startswith(self_base):
            return True

        # Test with common path segments that could exist
        test_segments = ["api", "app", "admin", "static", "content", "data"]

        for segment in test_segments:
            test_path = f"{self_base}/{segment}" if self_base else segment
            if self.matches(test_path) and other.matches(test_path):
                return True

        return False

    def __str__(self) -> str:
        return self.pattern

    def __repr__(self) -> str:
        return f"PathPattern('{self.pattern}')"


class PathConflictDetector:
    """Detects path conflicts between tunnels"""

    def __init__(self) -> None:
        self._active_paths: dict[str, str] = {}  # path -> tunnel_id

    def register_path(self, path: str, tunnel_id: str) -> None:
        """Register a path as active for a tunnel"""
        self._active_paths[path] = tunnel_id

    def unregister_path(self, path: str) -> None:
        """Unregister a path"""
        self._active_paths.pop(path, None)

    def check_conflict(self, new_path: str, existing_paths: list[str]) -> str | None:
        """Check if new path conflicts with existing paths.

        Args:
            new_path: Path to check for conflicts
            existing_paths: List of existing paths to check against

        Returns:
            Conflict message if conflict found, None otherwise
        """
        new_pattern = PathPattern(new_path)

        for existing_path in existing_paths:
            existing_pattern = PathPattern(existing_path)

            if new_pattern.conflicts_with(existing_pattern):
                return (
                    f"Path '{new_path}' conflicts with existing path '{existing_path}'"
                )

        return None

    def detect_conflicts(self, new_path: str) -> list[PathConflict]:
        """Detect all conflicts for a new path.

        Args:
            new_path: New path to check

        Returns:
            List of detected conflicts
        """
        conflicts = []
        new_pattern = PathPattern(new_path)

        for existing_path, existing_tunnel_id in self._active_paths.items():
            existing_pattern = PathPattern(existing_path)

            if new_pattern.conflicts_with(existing_pattern):
                if new_path == existing_path:
                    conflict_type = PathConflictType.EXACT_MATCH
                elif new_pattern.is_wildcard or existing_pattern.is_wildcard:
                    conflict_type = PathConflictType.WILDCARD_OVERLAP
                else:
                    conflict_type = PathConflictType.PARENT_CHILD

                conflict = PathConflict(
                    conflict_type=conflict_type,
                    existing_path=existing_path,
                    new_path=new_path,
                    existing_tunnel_id=existing_tunnel_id,
                    message=f"Path '{new_path}' conflicts with existing path '{existing_path}' (tunnel: {existing_tunnel_id})",
                )
                conflicts.append(conflict)

        return conflicts

    def get_active_paths(self) -> dict[str, str]:
        """Get all active paths and their tunnel IDs"""
        return self._active_paths.copy()

    def clear(self) -> None:
        """Clear all registered paths"""
        self._active_paths.clear()


class PathValidator:
    """Validates and normalizes paths for FRP tunnels"""

    @staticmethod
    def normalize_path(path: str) -> str:
        """Normalize path for consistent handling.

        Args:
            path: Raw path string

        Returns:
            Normalized path
        """
        path = path.strip("/")

        if not path:
            return ""

        path = _normalize_slashes_cached(path)

        return path

    @staticmethod
    def validate_path(path: str) -> bool:
        """Validate path format for FRP compatibility.

        Args:
            path: Path to validate

        Returns:
            True if valid, False otherwise
        """
        if not path:
            return False

        invalid_chars = set('<>"|?\\')
        if any(char in path for char in invalid_chars):
            return False

        if "***" in path:  # Triple asterisk not allowed
            return False

        if "**/*" in path or "*/**" in path:
            return False

        return True

    @staticmethod
    def extract_base_path(pattern: str) -> str:
        """Extract base path from wildcard pattern.

        Args:
            pattern: Path pattern with potential wildcards

        Returns:
            Base path without wildcards
        """
        wildcard_pos = pattern.find("*")
        if wildcard_pos == -1:
            return pattern

        base = pattern[:wildcard_pos].rstrip("/")
        return base if base else ""


# =============================================================================
# Exceptions
# =============================================================================


class TunnelRegistryError(Exception):
    """Exception raised for tunnel registry operations."""

    pass


class TunnelManagerError(Exception):
    """Exception raised for tunnel manager operations."""

    pass


# =============================================================================
# Tunnel Registry and Manager (from manager.py)
# =============================================================================


class TunnelRegistry(BaseModel):
    """In-memory store for active tunnels with add/remove/query operations."""

    tunnels: dict[str, BaseTunnel] = Field(
        default_factory=dict, description="Active tunnels by ID"
    )
    max_tunnels: int = Field(
        default=10, ge=1, le=100, description="Maximum number of tunnels"
    )

    def add_tunnel(self, tunnel: BaseTunnel) -> None:
        """Add tunnel to registry with validation.

        Args:
            tunnel: Tunnel to add

        Raises:
            TunnelRegistryError: If tunnel ID already exists or validation fails
        """
        if tunnel.id in self.tunnels:
            raise TunnelRegistryError(f"Tunnel with ID '{tunnel.id}' already exists")

        if len(self.tunnels) >= self.max_tunnels:
            raise TunnelRegistryError(
                f"Maximum tunnel limit ({self.max_tunnels}) reached"
            )

        if tunnel.tunnel_type == TunnelType.TCP:
            for existing_tunnel in self.tunnels.values():
                if (
                    existing_tunnel.tunnel_type == TunnelType.TCP
                    and existing_tunnel.local_port == tunnel.local_port
                ):
                    raise TunnelRegistryError(
                        f"Local port {tunnel.local_port} already in use"
                    )

        if tunnel.tunnel_type == TunnelType.HTTP and isinstance(tunnel, HTTPTunnel):
            for existing_tunnel in self.tunnels.values():
                if (
                    existing_tunnel.tunnel_type == TunnelType.HTTP
                    and isinstance(existing_tunnel, HTTPTunnel)
                    and existing_tunnel.path == tunnel.path
                ):
                    raise TunnelRegistryError(
                        f"HTTP path '{tunnel.path}' already in use"
                    )

        self.tunnels[tunnel.id] = tunnel
        logger.info(f"Added tunnel {tunnel.id} to registry")

    def remove_tunnel(self, tunnel_id: str) -> BaseTunnel:
        """Remove tunnel from registry.

        Args:
            tunnel_id: ID of tunnel to remove

        Returns:
            Removed tunnel

        Raises:
            TunnelRegistryError: If tunnel not found
        """
        if tunnel_id not in self.tunnels:
            raise TunnelRegistryError(f"Tunnel '{tunnel_id}' not found")

        tunnel = self.tunnels.pop(tunnel_id)
        logger.info(f"Removed tunnel {tunnel_id} from registry")
        return tunnel

    def get_tunnel(self, tunnel_id: str) -> BaseTunnel | None:
        """Get tunnel by ID.

        Args:
            tunnel_id: ID of tunnel to retrieve

        Returns:
            Tunnel if found, None otherwise
        """
        return self.tunnels.get(tunnel_id)

    def update_tunnel_status(self, tunnel_id: str, status: TunnelStatus) -> None:
        """Update tunnel status.

        Args:
            tunnel_id: ID of tunnel to update
            status: New status

        Raises:
            TunnelRegistryError: If tunnel not found
        """
        if tunnel_id not in self.tunnels:
            raise TunnelRegistryError(f"Tunnel '{tunnel_id}' not found")

        tunnel = self.tunnels[tunnel_id]
        updated_tunnel = tunnel.with_status(status)
        self.tunnels[tunnel_id] = updated_tunnel
        logger.info(f"Updated tunnel {tunnel_id} status to {status}")

    def list_tunnels(
        self, tunnel_type: TunnelType | None = None, status: TunnelStatus | None = None
    ) -> list[BaseTunnel]:
        """List tunnels with optional filtering.

        Args:
            tunnel_type: Filter by tunnel type
            status: Filter by status

        Returns:
            List of matching tunnels
        """
        tunnels = list(self.tunnels.values())

        if tunnel_type is not None:
            tunnels = [t for t in tunnels if t.tunnel_type == tunnel_type]

        if status is not None:
            tunnels = [t for t in tunnels if t.status == status]

        return tunnels

    def clear(self) -> None:
        """Clear all tunnels from registry."""
        self.tunnels.clear()
        logger.info("Cleared all tunnels from registry")

    def to_dict(self) -> dict[str, Any]:
        """Serialize registry to dictionary.

        Returns:
            Dictionary representation of registry
        """
        return {
            "tunnels": [tunnel.model_dump() for tunnel in self.tunnels.values()],
            "max_tunnels": self.max_tunnels,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TunnelRegistry":
        """Deserialize registry from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            TunnelRegistry instance
        """
        registry = cls(max_tunnels=data.get("max_tunnels", 10))

        for tunnel_data in data.get("tunnels", []):
            tunnel: BaseTunnel
            if tunnel_data["tunnel_type"] == TunnelType.HTTP:
                tunnel = HTTPTunnel(**tunnel_data)
            elif tunnel_data["tunnel_type"] == TunnelType.TCP:
                tunnel = TCPTunnel(**tunnel_data)
            else:
                continue

            registry.tunnels[tunnel.id] = tunnel

        return registry


class TunnelProcessManager:
    """Manages FRP processes for individual tunnels."""

    def __init__(self, config: TunnelConfig, frp_binary_path: str):
        """Initialize tunnel process manager.

        Args:
            config: Tunnel configuration with server details
            frp_binary_path: Path to FRP binary
        """
        self.config = config
        self._frp_binary_path = frp_binary_path
        self._processes: dict[str, ProcessManager] = {}

    def start_tunnel_process(self, tunnel: BaseTunnel) -> bool:
        """Start FRP process for tunnel.

        Args:
            tunnel: Tunnel to start process for

        Returns:
            True if process started successfully
        """
        try:
            logger.debug(f"Starting FRP process for tunnel {tunnel.id}")

            # Create configuration for this tunnel
            with ConfigBuilder() as config_builder:
                config_builder.add_server(
                    self.config.server_host,
                    token=self.config.auth_token,
                )

                # Add tunnel-specific configuration
                if isinstance(tunnel, HTTPTunnel):
                    config_builder.add_http_proxy(
                        name=tunnel.id,
                        local_port=tunnel.local_port,
                        locations=tunnel.locations,
                        custom_domains=tunnel.custom_domains,
                    )
                elif isinstance(tunnel, TCPTunnel):
                    config_builder.add_tcp_proxy(
                        name=tunnel.id,
                        local_port=tunnel.local_port,
                        remote_port=tunnel.remote_port,
                    )
                else:
                    logger.error(f"Unsupported tunnel type: {type(tunnel)}")
                    return False

                config_path = config_builder.build()

            # Start FRP process
            process_manager = ProcessManager(self._frp_binary_path, config_path)
            success = process_manager.start()

            if success:
                # Wait for startup
                startup_success = process_manager.wait_for_startup(timeout=10)
                if startup_success and process_manager.is_running():
                    self._processes[tunnel.id] = process_manager
                    logger.info(
                        f"Successfully started FRP process for tunnel {tunnel.id}"
                    )
                    return True
                else:
                    logger.error(
                        f"FRP process for tunnel {tunnel.id} failed to start properly"
                    )
                    process_manager.stop()
                    return False
            else:
                logger.error(f"Failed to start FRP process for tunnel {tunnel.id}")
                return False

        except Exception as e:
            logger.error(f"Exception starting FRP process for tunnel {tunnel.id}: {e}")
            return False

    def stop_tunnel_process(self, tunnel_id: str) -> bool:
        """Stop FRP process for tunnel.

        Args:
            tunnel_id: ID of tunnel to stop process for

        Returns:
            True if process stopped successfully
        """
        try:
            logger.debug(f"Stopping FRP process for tunnel {tunnel_id}")

            if tunnel_id not in self._processes:
                logger.warning(f"No FRP process found for tunnel {tunnel_id}")
                return True

            process_manager = self._processes[tunnel_id]
            success = process_manager.stop()

            if success:
                logger.info(f"Successfully stopped FRP process for tunnel {tunnel_id}")
            else:
                logger.warning(
                    f"FRP process for tunnel {tunnel_id} may not have stopped cleanly"
                )

            # Remove from processes dict regardless of stop success
            del self._processes[tunnel_id]
            return success

        except Exception as e:
            logger.error(f"Exception stopping FRP process for tunnel {tunnel_id}: {e}")
            # Still remove from processes dict to avoid leaks
            if tunnel_id in self._processes:
                del self._processes[tunnel_id]
            return False

    def is_process_running(self, tunnel_id: str) -> bool:
        """Check if FRP process is running for tunnel.

        Args:
            tunnel_id: ID of tunnel to check

        Returns:
            True if process is running
        """
        if tunnel_id not in self._processes:
            return False
        return self._processes[tunnel_id].is_running()

    def cleanup_all_processes(self) -> bool:
        """Stop all running FRP processes.

        Returns:
            True if all processes stopped successfully
        """
        success = True
        tunnel_ids = list(self._processes.keys())

        for tunnel_id in tunnel_ids:
            try:
                if not self.stop_tunnel_process(tunnel_id):
                    success = False
            except Exception as e:
                logger.error(f"Error stopping process for tunnel {tunnel_id}: {e}")
                success = False

        return success

    def get_running_process_count(self) -> int:
        """Get count of currently running processes.

        Returns:
            Number of running processes
        """
        return len(
            [
                tunnel_id
                for tunnel_id, process in self._processes.items()
                if process.is_running()
            ]
        )


class TunnelManager:
    """Registry for active tunnels with lifecycle management."""

    def __init__(self, config: TunnelConfig, frp_binary_path: str | None = None):
        """Initialize tunnel manager.

        Args:
            config: Tunnel configuration with server details
            frp_binary_path: Path to FRP binary (auto-detected if None)
        """
        self.config = config
        self.registry = TunnelRegistry(max_tunnels=config.max_tunnels)
        self._frp_binary_path = frp_binary_path or self._find_frp_binary()
        self._path_detector: PathConflictDetector = PathConflictDetector()
        self._process_manager = TunnelProcessManager(config, self._frp_binary_path)
        logger.info(
            f"Initialized TunnelManager with server={config.server_host}, max_tunnels={config.max_tunnels}"
        )

    @property
    def _processes(self) -> dict[str, Any]:
        """Backward compatibility property for tests."""
        return self._process_manager._processes

    def _find_frp_binary(self) -> str:
        """Find FRP binary in system PATH.

        Returns:
            Path to FRP binary

        Raises:
            RuntimeError: If FRP binary not found
        """
        frp_binary = shutil.which("frpc")
        if frp_binary is None:
            raise RuntimeError(
                "FRP client binary 'frpc' not found in system PATH. "
                "Please install FRP from https://github.com/fatedier/frp/releases "
                "and ensure 'frpc' is available in your PATH."
            )
        return frp_binary

    def create_http_tunnel(
        self,
        tunnel_id: str,
        local_port: int,
        path: str,
        custom_domains: list[str] | None = None,
        strip_path: bool = True,
        websocket: bool = True,
    ) -> HTTPTunnel:
        """Create HTTP tunnel and add to registry.

        Args:
            tunnel_id: Unique tunnel identifier
            local_port: Local port to expose
            path: URL path for routing
            custom_domains: Custom domains for tunnel
            strip_path: Strip path prefix when forwarding
            websocket: Enable WebSocket support

        Returns:
            Created HTTP tunnel

        Raises:
            TunnelManagerError: If path conflicts with existing tunnels or is invalid
        """
        normalized_path = PathValidator.normalize_path(path)
        if not PathValidator.validate_path(normalized_path):
            raise TunnelManagerError(
                f"Invalid path format '{path}': Path must contain only valid characters"
            )

        # Check for path conflicts with existing tunnels
        conflicts = self._path_detector.detect_conflicts(normalized_path)
        if conflicts:
            conflict_messages = [conflict.message for conflict in conflicts]
            raise TunnelManagerError(
                f"Path conflicts detected: {'; '.join(conflict_messages)}"
            )

        # Use default domain if no custom domains provided
        if custom_domains is None and self.config.default_domain:
            custom_domains = [self.config.default_domain]

        tunnel = HTTPTunnel(
            id=tunnel_id,
            local_port=local_port,
            path=normalized_path,
            custom_domains=custom_domains or [],
            strip_path=strip_path,
            websocket=websocket,
        )

        self.registry.add_tunnel(tunnel)

        self._path_detector.register_path(normalized_path, tunnel_id)

        logger.info(f"Created HTTP tunnel {tunnel_id} for path /{normalized_path}")
        return tunnel

    def create_tcp_tunnel(
        self, tunnel_id: str, local_port: int, remote_port: int | None = None
    ) -> TCPTunnel:
        """Create TCP tunnel and add to registry.

        Args:
            tunnel_id: Unique tunnel identifier
            local_port: Local port to expose
            remote_port: Remote port (auto-assigned if None)

        Returns:
            Created TCP tunnel
        """
        tunnel = TCPTunnel(id=tunnel_id, local_port=local_port, remote_port=remote_port)

        self.registry.add_tunnel(tunnel)
        logger.info(f"Created TCP tunnel {tunnel_id} for port {local_port}")
        return tunnel

    def start_tunnel(self, tunnel_id: str) -> bool:
        """Start tunnel process.

        Args:
            tunnel_id: ID of tunnel to start

        Returns:
            True if started successfully

        Raises:
            TunnelManagerError: If tunnel not found or start fails
        """
        tunnel = self.registry.get_tunnel(tunnel_id)
        if tunnel is None:
            raise TunnelManagerError(f"Tunnel '{tunnel_id}' not found")

        if tunnel.status == TunnelStatus.CONNECTED:
            logger.warning(f"Tunnel {tunnel_id} is already connected")
            return True

        self.registry.update_tunnel_status(tunnel_id, TunnelStatus.CONNECTING)

        try:
            success = self._process_manager.start_tunnel_process(tunnel)

            if success:
                self.registry.update_tunnel_status(tunnel_id, TunnelStatus.CONNECTED)
                logger.info(f"Started tunnel {tunnel_id}")
                return True
            else:
                self.registry.update_tunnel_status(tunnel_id, TunnelStatus.ERROR)
                logger.error(f"Failed to start tunnel {tunnel_id}")
                return False

        except Exception as e:
            self.registry.update_tunnel_status(tunnel_id, TunnelStatus.ERROR)
            logger.error(f"Error starting tunnel {tunnel_id}: {e}")
            raise TunnelManagerError(f"Failed to start tunnel: {e}") from e

    def stop_tunnel(self, tunnel_id: str) -> bool:
        """Stop tunnel process.

        Args:
            tunnel_id: ID of tunnel to stop

        Returns:
            True if stopped successfully

        Raises:
            TunnelManagerError: If tunnel not found or stop fails
        """
        tunnel = self.registry.get_tunnel(tunnel_id)
        if tunnel is None:
            raise TunnelManagerError(f"Tunnel '{tunnel_id}' not found")

        if tunnel.status != TunnelStatus.CONNECTED:
            logger.warning(f"Tunnel {tunnel_id} is not connected")
            return True

        try:
            success = self._process_manager.stop_tunnel_process(tunnel_id)

            if success:
                self.registry.update_tunnel_status(tunnel_id, TunnelStatus.DISCONNECTED)
                logger.info(f"Stopped tunnel {tunnel_id}")
                return True
            else:
                logger.error(f"Failed to stop tunnel {tunnel_id}")
                return False

        except Exception as e:
            logger.error(f"Error stopping tunnel {tunnel_id}: {e}")
            raise TunnelManagerError(f"Failed to stop tunnel: {e}") from e

    def remove_tunnel(self, tunnel_id: str) -> BaseTunnel:
        """Remove tunnel from manager.

        Args:
            tunnel_id: ID of tunnel to remove

        Returns:
            Removed tunnel
        """
        tunnel = self.registry.get_tunnel(tunnel_id)
        if tunnel and tunnel.status == TunnelStatus.CONNECTED:
            self.stop_tunnel(tunnel_id)

        removed_tunnel = self.registry.remove_tunnel(tunnel_id)

        if tunnel_id in self._process_manager._processes:
            del self._process_manager._processes[tunnel_id]

        # Unregister path from conflict detector if it's an HTTP tunnel
        if isinstance(removed_tunnel, HTTPTunnel):
            self._path_detector.unregister_path(removed_tunnel.path)

        logger.info(f"Removed tunnel {tunnel_id}")
        return removed_tunnel

    def list_active_tunnels(self) -> list[BaseTunnel]:
        """List only active (connected) tunnels.

        Returns:
            List of connected tunnels
        """
        return self.registry.list_tunnels(status=TunnelStatus.CONNECTED)

    def get_tunnel_info(self, tunnel_id: str) -> dict[str, Any]:
        """Get detailed tunnel information.

        Args:
            tunnel_id: ID of tunnel

        Returns:
            Dictionary with tunnel information

        Raises:
            TunnelManagerError: If tunnel not found
        """
        tunnel = self.registry.get_tunnel(tunnel_id)
        if tunnel is None:
            raise TunnelManagerError(f"Tunnel '{tunnel_id}' not found")

        info: dict[str, Any] = {
            "id": tunnel.id,
            "type": tunnel.tunnel_type.value,
            "local_port": tunnel.local_port,
            "status": tunnel.status.value,
            "created_at": tunnel.created_at.isoformat(),
            "connected_at": tunnel.connected_at.isoformat()
            if tunnel.connected_at
            else None,
        }

        if tunnel.tunnel_type == TunnelType.HTTP and isinstance(tunnel, HTTPTunnel):
            info.update(
                {
                    "path": tunnel.path,
                    "custom_domains": tunnel.custom_domains,
                    "url": tunnel.url,
                }
            )
        elif tunnel.tunnel_type == TunnelType.TCP and isinstance(tunnel, TCPTunnel):
            info.update(
                {"remote_port": tunnel.remote_port, "endpoint": tunnel.endpoint}
            )

        return info

    def shutdown_all(self) -> bool:
        """Shutdown all active tunnels.

        Returns:
            True if all tunnels stopped successfully
        """
        active_tunnels = self.list_active_tunnels()
        success = True

        for tunnel in active_tunnels:
            try:
                if not self.stop_tunnel(tunnel.id):
                    success = False
            except Exception as e:
                logger.error(f"Error stopping tunnel {tunnel.id}: {e}")
                success = False

        logger.info(f"Shutdown all tunnels, success={success}")
        return success


# Export main classes
__all__ = [
    # Models
    "TunnelType",
    "TunnelStatus",
    "BaseTunnel",
    "HTTPTunnel",
    "TCPTunnel",
    "TunnelConfig",
    # Manager
    "TunnelManager",
    "TunnelRegistry",
    "TunnelRegistryError",
    "TunnelManagerError",
    # Routing
    "PathConflictDetector",
    "PathValidator",
    "PathPattern",
    "PathConflict",
    "PathConflictType",
]
