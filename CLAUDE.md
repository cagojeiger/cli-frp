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

### Current Module Structure
```
src/frp_wrapper/
├── __init__.py              # Public API exports
├── api.py                   # High-level API functions
├── core/                    # Core functionality
│   ├── client.py           # FRPClient - Main client class
│   ├── process.py          # ProcessManager - FRP binary lifecycle
│   └── config.py           # ConfigBuilder - Configuration generator
├── tunnels/                 # Tunnel management
│   ├── interfaces.py       # Protocol interfaces (circular dependency solution)
│   ├── models.py           # Pydantic tunnel models (HTTPTunnel, TCPTunnel)
│   ├── manager.py          # TunnelManager - Tunnel lifecycle management
│   ├── process.py          # TunnelProcessManager - Individual tunnel processes
│   └── routing.py          # Path validation and conflict detection
└── common/                  # Common utilities
    ├── exceptions.py       # Custom exception hierarchy
    ├── logging.py          # Structured logging setup (structlog)
    └── utils.py            # Helper functions

tests/
├── conftest.py             # Pytest fixtures and configuration
├── test_*.py               # Test modules for each component
└── test_*_integration.py   # Integration tests
```

### Architecture Highlights
- **Protocol Pattern**: Used in `tunnels/interfaces.py` to solve circular dependencies
- **Pydantic Models**: Strong typing and validation throughout
- **Path-based Routing**: Native FRP `locations` parameter support
- **Modular Design**: Clear separation of concerns

### Key Design Principles

1. **Simple Class-Based Design**: Intuitive object-oriented API
   ```python
   # Current usage pattern
   from frp_wrapper import FRPClient

   client = FRPClient("example.com", auth_token="secret")
   client.connect()

   # Future: tunnel = client.expose_path(3000, "myapp")
   # Future: print(f"URL: {tunnel.url}")  # https://example.com/myapp/

   client.disconnect()
   ```

2. **Standard Python Exception Handling**: Clear error messages and proper exception hierarchy

3. **Context Manager Support**: Automatic resource cleanup
   ```python
   from frp_wrapper import FRPClient

   with FRPClient("example.com") as client:
       # Future: with client.tunnel(3000, "myapp") as tunnel:
       #     print(f"URL: {tunnel.url}")
       pass
   # Automatic cleanup
   ```

4. **Test-Driven Development**: All code written with comprehensive test coverage (95%+ required)

## Architecture Patterns

### Core Component Interaction
The architecture follows a modular pattern where each component has clear responsibilities:

1. **FRPClient** orchestrates connections and manages overall state
2. **ConfigBuilder** generates TOML configurations with temporary file management
3. **ProcessManager** handles FRP binary lifecycle with health monitoring
4. **TunnelManager** manages tunnel lifecycle and registry
5. **Protocol Interfaces** prevent circular dependencies between models and managers

```python
# Critical dependency flow - components must be initialized in this order:
config_builder = ConfigBuilder()
config_path = config_builder.build()
process_manager = ProcessManager(binary_path, config_path)

# Protocol pattern usage for circular dependency resolution:
# models.py uses TunnelManagerProtocol instead of importing TunnelManager directly
```

### Exception Hierarchy Design
Custom exceptions provide clear error categorization:
- `BinaryNotFoundError`: FRP binary detection failures
- `ConnectionError`: Network/server connection issues
- `AuthenticationError`: FRP server authentication failures
- `ProcessError`: FRP process management failures

### State Management Pattern
All classes implement consistent state tracking:
- **Initialization validation** in `__init__` (fail fast)
- **Boolean state queries** (`is_connected()`, `is_running()`)
- **Context manager support** for automatic cleanup
- **Immutable configuration** once objects are created

### Testing Architecture
- **Unit tests**: Mock all external dependencies (subprocess, file system)
- **Integration tests**: Use `@pytest.mark.integration` marker
- **Mock patterns**: Always mock `is_running()` when testing `is_connected()`

## Development Workflow - TDD Approach

### Test-First Development
1. **Write failing test first**
2. **Write minimal code to make test pass**
3. **Refactor while keeping tests green**
4. **Repeat for each feature**

### Testing Strategy
1. **Unit Tests**: Test individual classes and methods
2. **Integration Tests**: Test FRP binary interaction (mark with `@pytest.mark.integration`)
3. **Property Tests**: Test with varied inputs using Hypothesis
4. **End-to-End Tests**: Full tunnel creation and usage

### Current Test Coverage Requirements
- Minimum 95% coverage enforced in pyproject.toml
- Coverage reports generated automatically
- HTML coverage reports for detailed analysis

## Important Configuration Details

### Logging (structlog)
- Structured JSON logging configured
- File output to `frp_wrapper.log`
- Configurable via environment variables

### Type Checking (mypy)
- Strict mode enabled
- All code must be fully typed
- No implicit Any types allowed
- Python 3.11+ union types (X | None) preferred over Optional[X]

### Code Style (ruff)
- Line length: 88 characters
- Target Python 3.11+
- Comprehensive rule set (E, W, F, I, B, C4, UP, ARG, PL)
- Magic numbers (65535 for ports) are acceptable

### Pre-commit Hooks
- Automatic code formatting
- Type checking
- YAML/TOML validation
- Trailing whitespace removal

## Implementation Status

**Current Phase**: Checkpoint 4 Complete (Path-based Routing)
- ✅ **ProcessManager**: Binary lifecycle management with health checks
- ✅ **FRPClient**: Server connection and authentication
- ✅ **ConfigBuilder**: TOML configuration generation
- ✅ **TunnelManager**: Complete tunnel lifecycle management
- ✅ **HTTPTunnel/TCPTunnel**: Pydantic-based tunnel models
- ✅ **Path Routing**: Native FRP `locations` parameter support
- ✅ **Protocol Pattern**: Circular dependency resolution
- ✅ **95%+ Test Coverage**: Comprehensive test suite

**Architecture Improvements**:
- ✅ Modular structure with clear separation (core/, tunnels/, common/)
- ✅ Protocol interfaces to prevent circular dependencies
- ✅ Path validation and conflict detection
- ✅ High-level API for simple usage

## Common Tasks

### Adding a New Feature
1. Write comprehensive tests first (TDD)
2. Implement minimal code to pass tests
3. Refactor for clarity and maintainability
4. Update documentation and examples
5. Ensure 95%+ test coverage

### Working with High-Level API
```python
from frp_wrapper import create_tunnel, create_tcp_tunnel

# Simple HTTP tunnel
url = create_tunnel("example.com", 3000, "/myapp", auth_token="secret")
print(f"Your app is available at: {url}")

# TCP tunnel
endpoint = create_tcp_tunnel("example.com", 5432, auth_token="secret")
print(f"Database endpoint: {endpoint}")
```

### Working with FRPClient and TunnelManager
```python
from frp_wrapper import FRPClient, TunnelManager, TunnelConfig

# Create tunnel configuration
config = TunnelConfig(
    server_host="example.com",
    auth_token="secret",
    default_domain="example.com"
)

# Create and manage tunnels
manager = TunnelManager(config)
tunnel = manager.create_http_tunnel("my-app", 3000, "/myapp")
manager.start_tunnel(tunnel.id)

# With context manager
with tunnel.with_manager(manager):
    print(f"Tunnel active at: {tunnel.url}")
# Automatic cleanup
```

### Running Continuous Testing (TDD)
```bash
# In one terminal
uv run pytest-watch --clear --verbose

# In another terminal, edit code
# Tests run automatically on save
```

## Key Testing Patterns

### Unit Test Example
```python
import pytest
from frp_wrapper import FRPClient
from frp_wrapper.exceptions import ConnectionError

def test_client_requires_server():
    with pytest.raises(ValueError, match="Server address cannot be empty"):
        FRPClient("")

def test_client_context_manager(mock_process_manager):
    with FRPClient("example.com") as client:
        assert client.is_connected()
    assert not client.is_connected()
```

### Critical Mock Patterns
```python
# CRITICAL: Always mock is_running() when testing is_connected()
@patch('frp_wrapper.client.ProcessManager')
def test_client_connection(mock_process_manager):
    mock_process = Mock()
    mock_process_manager.return_value = mock_process
    mock_process.start.return_value = True
    mock_process.wait_for_startup.return_value = True
    mock_process.is_running.return_value = True  # Required for is_connected()

    client = FRPClient("example.com")
    assert client.connect()
    assert client.is_connected()  # Will fail without is_running() mock
```

### Dependency Chain Testing
```python
# Test the full component initialization chain
def test_full_initialization_chain():
    config_builder = ConfigBuilder()
    config_builder.add_server("example.com", token="secret")
    config_path = config_builder.build()

    process_manager = ProcessManager("/usr/bin/frpc", config_path)
    assert process_manager.is_running() == False  # Not started yet
```

## Environment-Specific Notes

- Project uses Python 3.11+ features (union types, match statements)
- All dependencies managed by `uv` (not pip/poetry)
- Structured logging with structlog (JSON format)
- Comprehensive pre-commit hooks for code quality
- FRP binary must be downloaded separately (not bundled)
- Integration tests require FRP binary or use mocked processes

## Circular Dependency Resolution

The project uses Protocol pattern to resolve circular dependencies between `tunnels/models.py` and `tunnels/manager.py`:

1. **Problem**: BaseTunnel needs reference to TunnelManager, but TunnelManager imports tunnel models
2. **Solution**: Created `tunnels/interfaces.py` with Protocol definitions
3. **Implementation**:
   - Models use `TunnelManagerProtocol` instead of importing `TunnelManager`
   - Manager property implemented as `@property` with `getattr` for Pydantic compatibility
   - No `model_rebuild()` calls needed

This maintains type safety while preventing import cycles.
