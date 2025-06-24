"""Path validation for tunnel routing."""

from .patterns import _normalize_slashes_cached


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
