"""Path conflict types and definitions."""

from dataclasses import dataclass
from enum import Enum


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
