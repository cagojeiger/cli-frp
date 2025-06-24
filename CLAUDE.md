# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FRP Python Wrapper is a self-hostable tunneling solution (like ngrok) that leverages FRP's native **locations** feature for path-based routing (https://example.com/myapp/). The design emphasizes:
- **Pythonic Design**: Clean, readable classes and intuitive APIs following Python conventions
- **Test-Driven Development**: Comprehensive test coverage with tests written before implementation
- **Simple Architecture**: Clear, minimal structure focusing on core functionality
- **Native FRP Features**: Direct use of FRP's locations parameter for path-based routing

## Development Commands

### Environment Setup
```bash
# Install all dependencies (uv is required)
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install

# Create new virtual environment if needed
uv venv

# Fix VIRTUAL_ENV conflicts
unset VIRTUAL_ENV
# Or use direct Python path: .venv/bin/python -m pytest
```

### Running Tests
```bash
# Run all tests with coverage
uv run pytest
# Or if VIRTUAL_ENV conflicts: .venv/bin/python -m pytest

# Run specific test file (note new test directory structure)
uv run pytest tests/client/test_client.py -v
uv run pytest tests/client/tunnel/test_models.py -v

# Run specific test method
uv run pytest tests/client/test_process.py::TestProcessManager::test_process_manager_starts_process -v

# Run tests excluding integration
uv run pytest -m "not integration"

# Check coverage report
uv run pytest --cov=src/frp_wrapper --cov-report=html
open htmlcov/index.html
```

### Code Quality
```bash
# Type checking (strict mode)
uv run mypy src/

# Linting and formatting
uv run ruff check src/
uv run ruff format src/

# Run all pre-commit hooks
uv run pre-commit run --all-files

# Build package
uv build
```

## Architecture Overview

### Directory Structure

```
src/frp_wrapper/
├── client/           # Client-side components (frpc wrapper)
│   ├── tunnel/      # Tunnel management subsystem
│   │   ├── models.py      # Pydantic models (HTTPTunnel, TCPTunnel)
│   │   ├── manager.py     # TunnelManager orchestrator
│   │   ├── registry.py    # TunnelRegistry for active tunnels
│   │   ├── process.py     # TunnelProcessManager
│   │   └── routing/       # Path-based routing logic
│   ├── client.py    # FRPClient main entry point
│   ├── config.py    # ConfigBuilder for TOML generation
│   ├── process.py   # ProcessManager for frpc binary
│   └── group.py     # TunnelGroup for batch operations
├── server/          # Server-side components (frps wrapper)
│   ├── server.py    # FRPServer main entry point
│   ├── config.py    # ServerConfigBuilder with dashboard support
│   └── process.py   # ServerProcessManager
└── common/          # Shared components
    ├── context.py   # Context managers and timeout handling
    ├── exceptions.py # Exception hierarchy
    └── logging.py   # Structured logging setup

tests/               # Mirrors src structure
├── client/
│   └── tunnel/
│       └── routing/
├── server/
└── common/
```

### Core Components

1. **Client Side** (`src/frp_wrapper/client/`)
   - `FRPClient`: Main entry point, orchestrates all components
   - `ProcessManager`: Manages frpc binary lifecycle
   - `ConfigBuilder`: Generates TOML configuration
   - `TunnelManager`: High-level tunnel management with registry
   - `HTTPTunnel`/`TCPTunnel`: Immutable Pydantic models
   - `TunnelGroup`: Batch tunnel management with LIFO/FIFO cleanup

2. **Server Side** (`src/frp_wrapper/server/`)
   - `FRPServer`: Server management following FRPClient pattern
   - `ServerProcessManager`: Extends ProcessManager for frps
   - `ServerConfigBuilder`: Server-specific TOML with dashboard support
   - `DashboardConfig`: Pydantic model with password validation

3. **Common Components** (`src/frp_wrapper/common/`)
   - `TimeoutContext`: Configurable timeout strategies
   - `FRPWrapperError`: Base exception with specific subclasses
   - `get_logger()`: Structured logging factory
   - `find_available_port()`: Port allocation utilities

### Key Architectural Patterns

#### Clean Separation of Concerns
- Client components handle frpc binary and tunnel management
- Server components handle frps binary and server configuration
- Common components provide shared functionality across both
- Tunnel subsystem split into focused modules after refactoring

#### Pydantic Validation Throughout
```python
# All configs use Pydantic with field validation
class ServerConfig(BaseModel):
    bind_port: int = Field(default=7000, ge=1, le=65535)
    auth_token: Optional[str] = Field(default=None, min_length=8)

# Immutable tunnel models
class HTTPTunnel(BaseTunnel):
    path: str = Field(..., pattern=r"^[a-zA-Z0-9][a-zA-Z0-9\-_/\*\.]*$")
    custom_domains: list[str] = Field(default_factory=list)
```

#### Context Manager Pattern
- Automatic resource cleanup for both client and server
- Nested context managers for complex scenarios
- Timeout contexts with configurable strategies
- Tunnels can be used as context managers with auto-start/stop

### Component Interaction Flow
```
FRPClient/FRPServer
    ├── ConfigBuilder (TOML generation)
    ├── ProcessManager (binary lifecycle)
    └── Tunnel Management (client only)
        ├── TunnelManager (orchestrator)
        ├── TunnelRegistry (active tunnel tracking)
        ├── TunnelProcessManager (FRP process per tunnel)
        ├── HTTPTunnel/TCPTunnel (immutable models)
        ├── TunnelGroup (batch operations)
        └── PathConflictDetector (routing validation)
```

## Critical Implementation Details

### State Management
- Boolean state methods: `is_running()`, `is_connected()`
- Thread-safe operations with proper locking
- Context managers ensure cleanup on exceptions
- Immutable tunnel models with `with_status()` method for state transitions

### Testing Strategy
- **95% minimum coverage** enforced (currently at 95.97%)
- Test files organized to mirror src structure
- Mock external dependencies (subprocess, filesystem)
- Integration tests marked with `@pytest.mark.integration`
- Always mock `_validate_paths` for process tests

### Pydantic Model Validation
- Use `Field(default=None)` for Optional fields, not `Field(None)`
- For model updates, create new instances to trigger validation:
  ```python
  # Don't use model_copy(update=...) - validation may not run
  current_dict = self._config.model_dump()
  current_dict.update(new_values)
  self._config = ConfigModel(**current_dict)  # Triggers validation
  ```
- Immutable models use frozen=True and provide builder methods

### Error Handling
- Custom exception hierarchy with `FRPWrapperError` base
- Specific exceptions: `BinaryNotFoundError`, `ConnectionError`, `ProcessError`
- Tunnel-specific: `TunnelManagerError`, `TunnelRegistryError`
- Always use structured logging with context

## Common Development Tasks

### Adding New Features
1. Write documentation first (`docs/qna/`)
2. Write tests following TDD in appropriate test directory
3. Implement with Pydantic models
4. Update exports in `__init__.py`
5. Ensure 95%+ coverage

### Debugging Issues
```bash
# Check FRP binary paths
which frpc frps

# Enable debug logging
export STRUCTLOG_LEVEL=DEBUG

# Check generated configs
cat /tmp/frpc_*.toml
cat /tmp/frps_*.toml

# Run specific test category
uv run pytest tests/client/tunnel/ -v
```

### Running Integration Tests
```bash
# Start FRP server for testing
docker run -d -p 7000:7000 -p 80:80 snowdreamtech/frps

# Run integration tests
uv run pytest -m integration
```

## Implementation Status

**Current Phase**: Checkpoint 6 Complete (Server Wrapper Implementation)
- ✅ Client-side wrapper (Checkpoints 1-5)
- ✅ Server-side wrapper with same patterns
- ✅ 95%+ test coverage maintained
- ✅ TDD approach with documentation first

**Key Insights from Checkpoint 6**:
- frps uses identical execution pattern as frpc (`./frps -c config.toml`)
- ProcessManager fully reusable, only binary path differs
- Pydantic validation prevents configuration errors
- Dashboard configuration with password strength validation

**Next Steps**:
- Checkpoint 7: Monitoring and metrics
- Checkpoint 8: Examples and documentation

## API Stability

Stable APIs:
- `FRPClient`, `FRPServer` context managers
- `create_tunnel()`, `managed_tunnel()` functions
- `TunnelManager` core methods

Internal APIs may change between versions.
