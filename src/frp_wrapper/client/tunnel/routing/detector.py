"""Path conflict detection for tunnel routing."""

from .conflicts import PathConflict, PathConflictType
from .patterns import PathPattern


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
