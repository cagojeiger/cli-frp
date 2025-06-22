"""Path-based routing system for FRP tunnels.

This module implements advanced path routing capabilities including:
- Path conflict detection between tunnels
- Wildcard pattern matching support
- Path validation and normalization
"""

import re
from dataclasses import dataclass
from enum import Enum
from re import Pattern


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
        escaped = re.escape(self.pattern)
        escaped = escaped.replace(r"\*\*", ".*")  # ** matches everything including /
        escaped = escaped.replace(r"\*", "[^/]*")  # * matches anything except /
        return re.compile(f"^{escaped}$")

    def matches(self, path: str) -> bool:
        """Check if path matches this pattern"""
        return bool(self._regex.match(path))

    def conflicts_with(self, other: "PathPattern") -> bool:
        """Check if this pattern conflicts with another pattern"""
        if self.pattern == other.pattern:
            return True

        if self.is_wildcard or other.is_wildcard:
            return self.matches(other.pattern.replace("*", "test")) or other.matches(
                self.pattern.replace("*", "test")
            )

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

        path = re.sub(r"/+", "/", path)

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
