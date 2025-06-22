"""FRP Python Wrapper - A self-hostable tunneling solution."""

from .logging import get_logger, setup_logging

# 패키지 초기화 시 로깅 설정
setup_logging(level="INFO")

# 패키지 레벨 로거
logger = get_logger(__name__)

__version__ = "0.1.0"
