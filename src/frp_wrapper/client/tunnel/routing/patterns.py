"""Path pattern matching for tunnel routing."""

import re
from functools import lru_cache
from re import Pattern


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
