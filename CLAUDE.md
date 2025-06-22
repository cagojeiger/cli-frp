# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FRP Python Wrapper is a self-hostable tunneling solution (like ngrok) that leverages FRP's native **locations** feature for path-based routing (https://example.com/myapp/). The design emphasizes:
- **Pythonic Design**: Clean, readable classes and intuitive APIs following Python conventions
- **Test-Driven Development**: Comprehensive test coverage with tests written before implementation
- **Simple Architecture**: Clear, minimal structure focusing on core functionality
- **Native FRP Features**: Direct use of FRP's locations parameter for path-based routing

## Development Commands

### Setting up the environment
```bash
# This project uses uv for dependency management
# Install all dependencies including dev and test extras
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install

# Install FRP binary (required external dependency)
# Download from: https://github.com/fatedier/frp/releases
```

### Running tests (TDD Approach)
```bash
# Run all tests with coverage (configured in pyproject.toml)
uv run pytest

# Run tests in watch mode for TDD
uv run pytest-watch

# Run specific test file
uv run pytest tests/test_process.py

# Run tests with verbose output
uv run pytest -v

# Run specific test method
uv run pytest tests/test_process.py::test_process_manager_start -v

# Run tests excluding integration tests
uv run pytest -m "not integration"

# Run async tests only
uv run pytest -m "asyncio"

# Check coverage report
uv run pytest --cov=src/frp_wrapper --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Linting and type checking
```bash
# Type checking with mypy (strict mode)
uv run mypy src/

# Linting with ruff
uv run ruff check src/

# Auto-formatting with ruff
uv run ruff format src/

# Run all pre-commit hooks
uv run pre-commit run --all-files
```

### Building and packaging
```bash
# Build package
uv build

# For PyPI upload (when ready)
uv run twine upload dist/*
```

## Architecture Overview

### Core Components

1. **FRPClient** (`core/client.py`)
   - Main entry point for users
   - Manages connection lifecycle to FRP server
   - Coordinates ProcessManager and TunnelManager
   - Provides context manager support

2. **ProcessManager** (`core/process.py`)
   - Manages FRP binary (frpc) lifecycle
   - Health monitoring with configurable startup timeout
   - Graceful shutdown with SIGTERM/SIGKILL fallback
   - Thread-safe operations

3. **TunnelManager** (`tunnels/manager.py`)
   - Creates and manages individual tunnels
   - Path conflict detection and resolution
   - Registry of active tunnels
   - Integrates with TunnelProcessManager for per-tunnel processes

4. **ConfigBuilder** (`core/config.py`)
   - Generates TOML configuration for FRP
   - Temporary file management with automatic cleanup
   - Server and proxy configuration

### Key Architectural Patterns

#### Protocol Pattern for Circular Dependencies
The project uses Protocol interfaces to solve circular import issues:
```python
# tunnels/interfaces.py defines protocols
class TunnelManagerProtocol(Protocol):
    def start_tunnel(self, tunnel_id: str) -> bool: ...
    def stop_tunnel(self, tunnel_id: str) -> bool: ...

# models.py uses protocol instead of importing manager
class BaseTunnel(BaseModel):
    _manager: TunnelManagerProtocol | None = None
```

#### Pydantic Models with Validation
All data models use Pydantic for runtime validation:
```python
class HTTPTunnel(BaseTunnel):
    type: Literal[TunnelType.HTTP] = TunnelType.HTTP
    local_port: int = Field(..., ge=1, le=65535)
    path: str = Field(..., min_length=1)
    custom_domains: list[str] = Field(default_factory=list)
```

#### Context Manager Pattern
Resource management through context managers:
```python
# Automatic cleanup
with FRPClient("example.com") as client:
    tunnel = client.expose_path(3000, "/app")
    # Use tunnel
# Automatic disconnect and cleanup

# Managed tunnels
with managed_tunnel("example.com", 3000, "/app") as url:
    # Use tunnel
# Automatic cleanup
```

### Component Interaction Flow

```
User Code
    ↓
FRPClient (orchestrator)
    ├── ConfigBuilder (generates TOML)
    ├── ProcessManager (manages frpc binary)
    └── TunnelManager (manages tunnels)
        ├── HTTPTunnel/TCPTunnel (data models)
        ├── TunnelProcessManager (per-tunnel processes)
        └── PathRouter (conflict detection)
```

## Critical Implementation Details

### State Management
- All stateful classes track their state with boolean methods (`is_running()`, `is_connected()`)
- State transitions are atomic and thread-safe
- Context managers ensure cleanup even on exceptions

### Error Handling
Custom exception hierarchy for clear error categorization:
- `FRPWrapperError` (base)
  - `BinaryNotFoundError` (FRP binary issues)
  - `ConnectionError` (network/server issues)
  - `AuthenticationError` (auth failures)
  - `ProcessError` (process management)
  - `TunnelError` (tunnel-specific issues)

### Testing Requirements
- **Minimum 95% coverage** enforced in pyproject.toml
- Mock all external dependencies (subprocess, filesystem)
- Integration tests marked with `@pytest.mark.integration`
- Critical pattern: Always mock `is_running()` when testing `is_connected()`

### Logging Strategy
- Structured logging with structlog
- JSON format for machine parsing
- Sensitive data sanitization (tokens, passwords)
- Log levels: DEBUG for development, INFO for production

## Common Development Tasks

### Adding a New Tunnel Type
1. Define model in `tunnels/models.py` inheriting from `BaseTunnel`
2. Add creation method to `TunnelManager`
3. Add high-level API function in `api.py`
4. Write tests first (TDD)
5. Update type exports in `__init__.py`

### Debugging Connection Issues
1. Check FRP binary path: `which frpc`
2. Enable debug logging: `setup_logging(level="DEBUG")`
3. Verify server connectivity: `telnet server 7000`
4. Check generated config: `cat /tmp/frpc_*.toml`

### Running Integration Tests
```bash
# Requires FRP server running
docker run -d -p 7000:7000 -p 80:80 snowdreamtech/frps

# Run integration tests
uv run pytest -m integration
```

## Implementation Status

**Current Phase**: Checkpoint 5 Complete (Context Manager Implementation)
- ✅ ProcessManager with health monitoring
- ✅ FRPClient with connection management
- ✅ TunnelManager with lifecycle management
- ✅ Path-based routing with conflict detection
- ✅ Context managers for automatic cleanup
- ✅ Async support (AsyncProcessManager)
- ✅ Tunnel groups for batch management
- ✅ 95%+ test coverage achieved

**Next Checkpoints**:
- Checkpoint 6: Server-side tools
- Checkpoint 7: Monitoring and metrics
- Checkpoint 8: Examples and documentation

## Environment Requirements

- **Python 3.11+** (uses union types, match statements)
- **uv** for dependency management (not pip/poetry)
- **FRP binary** must be downloaded separately
- **Pre-commit hooks** for code quality
- **Integration tests** require FRP server or mocks

## API Stability

The following APIs are considered stable:
- `create_tunnel()`, `create_tcp_tunnel()`
- `managed_tunnel()`, `managed_tcp_tunnel()`
- `FRPClient` context manager
- `TunnelManager` core methods

Internal APIs (process management, config generation) may change between versions.
