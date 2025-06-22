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
├── __init__.py        # Public API exports
├── exceptions.py      # Custom exception hierarchy
├── logging.py         # Structured logging setup (structlog)
└── process.py         # ProcessManager - FRP binary lifecycle (implemented)

tests/
├── __init__.py
├── conftest.py        # Pytest fixtures and configuration
└── test_process.py    # ProcessManager tests (100% coverage)
```

### Planned Module Structure
```
src/frp_wrapper/
├── client.py          # Main FRPClient class
├── tunnel.py          # Tunnel management classes
├── config.py          # Configuration builder
└── utils.py           # Helper functions
```

### Key Design Principles

1. **Simple Class-Based Design**: Intuitive object-oriented API
   ```python
   # Main usage pattern
   client = FRPClient("example.com", auth_token="secret")
   client.connect()

   tunnel = client.expose_path(3000, "myapp")
   print(f"URL: {tunnel.url}")  # https://example.com/myapp/

   client.close()
   ```

2. **Standard Python Exception Handling**: Clear error messages and proper exception hierarchy

3. **Context Manager Support**: Automatic resource cleanup
   ```python
   with FRPClient("example.com") as client:
       with client.tunnel(3000, "myapp") as tunnel:
           print(f"URL: {tunnel.url}")
   # Automatic cleanup
   ```

4. **Test-Driven Development**: All code written with comprehensive test coverage (95%+ required)

## Core Concepts

### Main Classes
- **ProcessManager** (Implemented): Manages FRP binary process lifecycle with health checks
- **FRPClient** (Planned): Main client for connecting to FRP server
- **HTTPTunnel** (Planned): HTTP tunnel with path-based routing
- **TCPTunnel** (Planned): Simple TCP port forwarding
- **ConfigBuilder** (Planned): Generates FRP configuration files

### Path-Based Routing Mechanism
Uses FRP's native `locations` feature for clean URL routing:
```
User Request: https://example.com/myapp/api
    ↓
FRP Server: Route based on locations ["/myapp"]
    ↓
Local Service: Receive request on port 3000
```

FRP Configuration:
```toml
[[proxies]]
name = "myapp"
type = "http"
localPort = 3000
customDomains = ["example.com"]
locations = ["/myapp"]  # Native path routing!
```

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

### Code Style (ruff)
- Line length: 88 characters
- Target Python 3.11+
- Comprehensive rule set (E, W, F, I, B, C4, UP, ARG, PL)

### Pre-commit Hooks
- Automatic code formatting
- Type checking
- YAML/TOML validation
- Trailing whitespace removal

## Development Status

**Current Phase**: Implementation Phase (Checkpoint 1 of 8)
- ✅ Project setup complete (uv, pre-commit, structlog)
- ✅ ProcessManager implemented with full test coverage
- 🚧 Working towards Checkpoint 2 (Basic FRP Client)

**Roadmap Overview** (5 weeks total):
- Phase 1 (Weeks 1-2): Basic implementation
- Phase 2 (Weeks 3-4): Core features
- Phase 3 (Week 5): Production ready

## Common Tasks

### Adding a New Feature
1. Write comprehensive tests first (TDD)
2. Implement minimal code to pass tests
3. Refactor for clarity and maintainability
4. Update documentation and examples
5. Ensure 95%+ test coverage

### Working with ProcessManager
```python
from frp_wrapper.process import ProcessManager

# Basic usage
manager = ProcessManager("/path/to/frpc", config_path="/path/to/config.toml")
manager.start()
if manager.is_running():
    print("FRP is running!")
manager.stop()

# With context manager
with ProcessManager("/path/to/frpc", config_path="/path/to/config.toml") as manager:
    # Process runs here
    pass
# Automatically stopped
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
from frp_wrapper.process import ProcessManager
from frp_wrapper.exceptions import ProcessError

def test_process_manager_requires_binary():
    with pytest.raises(ValueError, match="binary_path is required"):
        ProcessManager("")

def test_process_manager_start_stop(tmp_path, mock_subprocess):
    manager = ProcessManager("/usr/bin/frpc", config_path=str(tmp_path / "config.toml"))
    manager.start()
    assert manager.is_running()
    manager.stop()
    assert not manager.is_running()
```

### Fixture Usage
```python
# From conftest.py
@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess.Popen for testing."""
    # Use this fixture to test process management without real processes
```

## Environment-Specific Notes

- Project uses Python 3.11+ features
- All dependencies managed by `uv` (not pip/poetry)
- Structured logging with structlog (JSON format)
- Comprehensive pre-commit hooks for code quality
- FRP binary must be downloaded separately (not bundled)
