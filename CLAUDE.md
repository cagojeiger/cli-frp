# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FRP Python Wrapper is evolving into a **Kubernetes-native distributed service proxy system** that leverages FRP for secure tunneling while providing enterprise-grade orchestration. The project currently provides a Python wrapper for FRP with plans to expand into K8s-native architecture.

### Core Vision
- **Python FRP Wrapper** (Current): Clean Python API for FRP with Pydantic models and context managers
- **K8s-Native Architecture** (Planned): Kubernetes deployment with CRDs, Operators, and native patterns
- **Distributed Service Proxy** (Future): General-purpose proxy supporting various services
- **Enterprise Security** (Roadmap): mTLS by default, Zero Trust networking principles

### Design Principles
- **Pythonic Design**: Clean, readable classes and intuitive APIs following Python conventions
- **Test-Driven Development**: Comprehensive test coverage (95%+ enforced, currently 96%)
- **Separation of Concerns**: Clear module boundaries and single responsibility
- **Type Safety**: Strict mypy checking with Pydantic validation throughout

## Development Commands

### Environment Setup
```bash
# Install all dependencies (uv is required)
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install

# Create new virtual environment if needed
uv venv
```

### Running Tests
```bash
# Run all tests with coverage
uv run pytest

# Run specific test file
uv run pytest tests/client/test_client.py -v

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
│   └── group.py     # TunnelGroup for batch operations
├── server/          # Server-side components (frps wrapper)
│   ├── server.py    # FRPServer main entry point
│   ├── config.py    # ServerConfigBuilder with dashboard support
│   └── process.py   # ServerProcessManager
├── common/          # Shared components
│   ├── context.py   # Context managers and timeout handling
│   ├── context_config.py # Configuration for context managers
│   ├── exceptions.py # Exception hierarchy
│   ├── logging.py   # Structured logging setup
│   ├── process.py   # ProcessManager for frpc/frps binary lifecycle
│   └── utils.py     # Port allocation and utilities
├── api.py           # High-level API functions (create_tunnel, etc.)
└── __init__.py      # Package exports

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
   - `ProcessManager`: Unified process management for frpc/frps binaries
   - `TimeoutContext`: Configurable timeout strategies
   - `FRPWrapperError`: Base exception with specific subclasses
   - `get_logger()`: Structured logging factory
   - `find_available_port()`: Port allocation utilities

4. **High-Level API** (`src/frp_wrapper/api.py`)
   - `create_tunnel()`: Simple one-line tunnel creation
   - `managed_tunnel()`: Context manager for tunnels
   - `create_tcp_tunnel()`: TCP-specific tunnel creation

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
- **95% minimum coverage** enforced (currently at 96%)
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
1. Write tests following TDD in appropriate test directory
2. Implement with Pydantic models for data validation
3. Update exports in `__init__.py`
4. Ensure 95%+ coverage maintained
5. Run all quality checks before committing

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
- ✅ ProcessManager moved to common module (layer violation fixed)

**Next Steps**:
- Checkpoints 7-11 are planned features (monitoring, CLI, TUI)
- Checkpoint 12 (K8s Distributed System) is in design phase
- See `plan/checkpoints/` for detailed roadmap

## API Stability

Stable APIs:
- `FRPClient`, `FRPServer` context managers
- `create_tunnel()`, `managed_tunnel()` functions
- `TunnelManager` core methods

Internal APIs may change between versions.

## Future K8s Integration (Design Phase)

The project plans to evolve into a Kubernetes-native distributed service proxy. Key planned features:

- Custom Resource Definitions (CRDs) for declarative service management
- Kubernetes Operator for automated lifecycle management
- Service discovery integration with K8s APIs
- mTLS certificate management with automatic rotation
- Horizontal scaling with FRP group load balancing

See `plan/checkpoints/checkpoint-12-k8s-distributed-system.md` for detailed design.

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
