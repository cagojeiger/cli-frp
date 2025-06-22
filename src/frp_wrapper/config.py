"""Configuration builder for FRP client."""

import tempfile
import os
from pathlib import Path
from types import TracebackType
from typing import Optional, Literal

from .logging import get_logger

logger = get_logger(__name__)


class ConfigBuilder:
    """Builder for FRP client configuration files."""
    
    def __init__(self):
        """Initialize ConfigBuilder with empty state."""
        self._server_addr: Optional[str] = None
        self._server_port: int = 7000
        self._auth_token: Optional[str] = None
        self._config_path: Optional[str] = None
        
        logger.debug("ConfigBuilder initialized")
    
    def add_server(
        self, 
        addr: str, 
        port: int = 7000, 
        token: Optional[str] = None
    ) -> "ConfigBuilder":
        """Add server configuration.
        
        Args:
            addr: Server address
            port: Server port (default: 7000)
            token: Authentication token
            
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If address is empty or port is invalid
        """
        if not addr or not addr.strip():
            raise ValueError("Server address cannot be empty")
            
        if not (1 <= port <= 65535):
            raise ValueError("Port must be between 1 and 65535")
            
        self._server_addr = addr.strip()
        self._server_port = port
        self._auth_token = token
        
        logger.debug(
            "Server configuration added",
            addr=self._server_addr,
            port=self._server_port,
            has_token=token is not None
        )
        
        return self
    
    def build(self) -> str:
        """Build configuration file and return path.
        
        Returns:
            Path to generated configuration file
            
        Raises:
            ValueError: If server address not set
        """
        if not self._server_addr:
            raise ValueError("Server address not set. Call add_server() first.")
            
        fd, temp_path = tempfile.mkstemp(suffix='.toml', prefix='frp_config_')
        
        try:
            with os.fdopen(fd, 'w') as f:
                f.write('[common]\n')
                f.write(f'server_addr = "{self._server_addr}"\n')
                f.write(f'server_port = {self._server_port}\n')
                
                if self._auth_token:
                    f.write(f'token = "{self._auth_token}"\n')
                    
                f.write('\n')
                
            self._config_path = temp_path
            
            logger.info("Configuration file built", path=self._config_path)
            return self._config_path
            
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
    
    def cleanup(self) -> None:
        """Clean up temporary configuration file."""
        if self._config_path and os.path.exists(self._config_path):
            try:
                os.unlink(self._config_path)
                logger.debug("Configuration file cleaned up", path=self._config_path)
            except OSError as e:
                logger.warning("Failed to cleanup config file", error=str(e))
            finally:
                self._config_path = None
    
    def __enter__(self) -> "ConfigBuilder":
        """Context manager entry.
        
        Returns:
            Self for use in with statement
        """
        logger.debug("Entering ConfigBuilder context")
        return self
    
    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> Literal[False]:
        """Context manager exit - automatically cleanup.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
            
        Returns:
            False to propagate any exception
        """
        logger.debug("Exiting ConfigBuilder context")
        try:
            self.cleanup()
        except Exception as e:
            logger.error("Error during context exit", error=str(e))
        return False  # Don't suppress exceptions
