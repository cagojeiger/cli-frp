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
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (once pyproject.toml is created)
pip install -e ".[dev]"

# Install pre-commit hooks (once configured)
pre-commit install

# Install FRP binary (required external dependency)
# Download from: https://github.com/fatedier/frp/releases
```

### Running tests (TDD Approach)
```bash
# Run all tests
pytest

# Run tests with coverage (must maintain 95%+ coverage)
pytest --cov=src --cov-report=term-missing --cov-fail-under=95

# Run specific test file
pytest tests/test_client.py

# Run tests in watch mode for TDD
pytest-watch

# Run tests with verbose output
pytest -v
```

### Linting and type checking
```bash
# Type checking (required)
mypy src/

# Linting (required)
ruff check src/

# Auto-formatting
ruff format src/
```

### Building and packaging
```bash
# Build package
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

## Architecture Overview

### Simple Module Structure
```
src/frp_wrapper/
├── __init__.py     # Public API exports
├── client.py       # Main FRPClient class
├── tunnel.py       # Tunnel management classes
├── process.py      # FRP process handling
├── config.py       # Configuration builder
├── exceptions.py   # Custom exceptions
└── utils.py        # Helper functions

tests/
├── test_client.py
├── test_tunnel.py
├── test_process.py
├── test_config.py
└── test_integration.py
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

4. **Test-Driven Development**: All code written with comprehensive test coverage

### Directory Structure
```
src/
└── frp_wrapper/
    ├── __init__.py      # Main API exports
    ├── client.py        # FRPClient class
    ├── tunnel.py        # Tunnel classes (HTTPTunnel, TCPTunnel)
    ├── process.py       # ProcessManager class
    ├── config.py        # ConfigBuilder class
    ├── exceptions.py    # Custom exceptions
    └── utils.py         # Helper functions

tests/
├── __init__.py
├── test_client.py
├── test_tunnel.py
├── test_process.py
├── test_config.py
├── test_utils.py
└── test_integration.py
```

## Core Concepts

### Main Classes
- **FRPClient**: Main client for connecting to FRP server
- **HTTPTunnel**: HTTP tunnel with path-based routing
- **TCPTunnel**: Simple TCP port forwarding
- **ProcessManager**: Manages FRP binary process
- **ConfigBuilder**: Generates FRP configuration files

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
2. **Integration Tests**: Test FRP binary interaction
3. **Property Tests**: Test with varied inputs using Hypothesis
4. **End-to-End Tests**: Full tunnel creation and usage

### Example TDD Workflow
```python
# 1. Write failing test
def test_client_connection():
    client = FRPClient("test.example.com")
    assert not client.is_connected()

    client.connect()
    assert client.is_connected()

# 2. Implement minimal code
class FRPClient:
    def __init__(self, server):
        self.server = server
        self._connected = False

    def is_connected(self):
        return self._connected

    def connect(self):
        # Minimal implementation
        self._connected = True

# 3. Refactor and add real functionality
```

## Important Notes

1. **TDD is Required**: All code must be written test-first with high coverage
2. **Simple Over Complex**: Prefer clear, simple solutions over clever abstractions
3. **Python Conventions**: Follow PEP 8, use type hints, clear naming
4. **FRP Integration**: Direct use of FRP's native features, no unnecessary abstraction
5. **Error Handling**: Use standard Python exceptions with clear messages

## Common Tasks

### Adding a New Feature
1. Write comprehensive tests first (TDD)
2. Implement minimal code to pass tests
3. Refactor for clarity and maintainability
4. Update documentation and examples
5. Ensure 95%+ test coverage

### Working with FRP Configuration
- Use FRP's native TOML configuration format
- Leverage `locations` parameter for path routing
- Test with actual FRP binary when possible

### Running TDD Development
```bash
# Start TDD session
pytest-watch --clear --verbose

# In another terminal, edit tests and code
# Tests will run automatically on file changes
```

## Common Commands for TDD Development

```bash
# Install in development mode with test dependencies
pip install -e ".[dev,test]"

# Run tests continuously during development
pytest-watch

# Run specific test method
pytest tests/test_client.py::test_client_connection -v

# Check test coverage
pytest --cov=src --cov-report=html
open htmlcov/index.html  # View coverage report
```

## Key Testing Patterns

### Unit Test Example
```python
import pytest
from frp_wrapper import FRPClient
from frp_wrapper.exceptions import ConnectionError

def test_client_requires_server():
    with pytest.raises(ValueError):
        FRPClient("")  # Empty server should raise

def test_client_connection_success():
    client = FRPClient("example.com")
    # Mock successful connection
    assert client.connect() == True

def test_client_connection_failure():
    client = FRPClient("invalid.server")
    with pytest.raises(ConnectionError):
        client.connect()
```

### Integration Test Example
```python
@pytest.mark.integration
def test_real_tunnel_creation():
    # Requires actual FRP server for testing
    with FRPClient("test.server.com") as client:
        tunnel = client.expose_path(3000, "test")
        assert tunnel.url.startswith("https://")
        assert "test" in tunnel.url
```

This approach maintains the core innovative ideas (FRP locations, path routing) while making the codebase much more approachable and maintainable for Python developers, with TDD as a strong foundation.
