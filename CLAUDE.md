# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FRP Python Wrapper is a self-hostable tunneling solution (like ngrok) focusing on **subpath routing** (https://example.com/myapp/) instead of subdomain routing. The design emphasizes:
- **Functional Programming**: Immutable data structures, pure functions, explicit effects
- **Domain-Driven Design**: Clear separation of business logic and side effects
- **AI-Friendly Architecture**: Minimal context coupling for easier understanding

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
```

### Running tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_core/test_tunnel_operations.py

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run property-based tests
pytest -k "test_properties" --hypothesis-show-statistics
```

### Linting and type checking
```bash
# Type checking
mypy src/

# Linting
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

### Layer Structure
```
┌─────────────────────────────────────────┐
│          API Layer (公개 인터페이스)      │  # Public interfaces: create_client(), expose_path()
├─────────────────────────────────────────┤
│     Application Layer (유스케이스)       │  # Service orchestration: TunnelService, ClientService
├─────────────────────────────────────────┤
│        Domain Layer (비즈니스 로직)      │  # Pure business logic: tunnel_operations, config_builder
├─────────────────────────────────────────┤
│      Effects Layer (부수 효과 처리)      │  # Side effect interfaces: ProcessExecutor, FileWriter
├─────────────────────────────────────────┤
│   Infrastructure Layer (외부 시스템)     │  # External integrations: frpc_adapter, nginx_adapter
└─────────────────────────────────────────┘
```

### Key Design Patterns

1. **Result Monad**: All operations return `Result[T, E]` for explicit error handling
   ```python
   result = create_client("server.com")
   match result:
       case Ok(client): # handle success
       case Err(error): # handle error
   ```

2. **Pipeline Pattern**: Function composition for complex operations
   ```python
   pipeline = pipe(
       create_http_tunnel,
       flat_map_result(validate_tunnel),
       map_result(generate_url)
   )
   ```

3. **Event Sourcing**: All state changes tracked as immutable events

### Directory Structure
```
src/
├── domain/       # Immutable domain models (@frozen dataclasses)
├── core/         # Pure business logic functions
├── effects/      # Side effect protocols and implementations
├── application/  # Service layer combining pure functions with effects
├── infrastructure/ # External system adapters
└── api/          # Public API functions
```

## Core Concepts

### Domain Models
- **Process**: FRP binary process management
- **Client**: Connection to FRP server
- **Tunnel**: Exposed local service (TCPTunnel, HTTPTunnel)
- **Config**: FRP configuration management

### Functional Principles
1. **Immutability**: All domain objects use `@frozen` dataclasses
2. **Pure Functions**: Business logic has no side effects
3. **Explicit Effects**: I/O operations isolated in protocols
4. **Function Composition**: Complex operations built from simple functions

### Subpath Routing Mechanism
The wrapper implements subpath routing using virtual host mapping:
```
User Request: https://example.com/myapp/api
    ↓
Nginx: Extract path, set Host header to "myapp.local"
    ↓
FRP Server: Route based on vhost
    ↓
Local Service: Receive request on port 3000
```

## Development Workflow

### Checkpoint-Based PRs
The project is divided into 8 checkpoints, each representing a PR-sized unit:
1. Process Manager (도메인 모델, 프로세스 관리)
2. Basic Client (클라이언트 API)
3. Tunnel Management (터널 생성/삭제)
4. Path Routing (서브패스 라우팅)
5. Context Manager (리소스 자동 관리)
6. Server Tools (서버 설정 도구)
7. Monitoring (로깅, 상태 추적)
8. Examples & Docs (예제, 문서화)

### Testing Strategy
1. **Pure Function Tests**: Simple input/output validation
2. **Property-Based Tests**: Using Hypothesis for invariant testing
3. **Effect Mocking**: Mock protocols for testing services
4. **Integration Tests**: Docker-based FRP server testing

### Key Testing Patterns
```python
# Property-based testing
@given(port=st.integers(min_value=1, max_value=65535))
def test_port_validation(port):
    result = create_tcp_tunnel(ClientId("test"), port)
    assert result.is_ok() == (1 <= port <= 65535)

# Effect mocking
process_executor = Mock(spec=ProcessExecutor)
process_executor.spawn.return_value = Ok(12345)
```

## Important Notes

1. **No Code Yet**: This is a design-phase project. Implement following the functional patterns in docs/
2. **Korean Comments**: Some documentation includes Korean (도메인, 유스케이스, etc.)
3. **Result Type First**: Always use Result[T, E] instead of exceptions
4. **Immutable First**: Create new instances instead of modifying existing ones
5. **Test Pure Functions**: Focus testing on pure functions, mock effects

## Common Tasks

### Adding a New Domain Model
1. Create in `src/domain/` as a frozen dataclass
2. Add validation in `__post_init__` if needed
3. Create pure functions in `src/core/` for operations
4. Add events in `src/domain/events.py` for state changes

### Adding a New Feature
1. Start with domain model and pure functions
2. Define effect protocols if I/O is needed
3. Implement service in application layer
4. Expose through API layer
5. Write tests: pure functions → mocked effects → integration

### Running Specific Checkpoint Tests
```bash
# Test specific checkpoint implementation
pytest tests/test_checkpoint_01_process_manager.py
pytest tests/test_checkpoint_02_basic_client.py
# etc...
```