"""FRP Python Wrapper - A self-hostable tunneling solution."""

from .logging import get_logger, setup_logging

# Setup logging on package initialization
setup_logging(level="INFO")

# Package level logger
logger = get_logger(__name__)

__version__ = "0.1.0"
