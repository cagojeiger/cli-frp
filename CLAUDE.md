# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FRP Python Wrapper is a self-hostable tunneling solution (like ngrok) that leverages FRP's native **locations** feature for path-based routing (https://example.com/myapp/). The design emphasizes:
- **Functional Programming**: Immutable data structures, pure functions, explicit effects
- **Domain-Driven Design**: Clear separation of business logic and side effects
- **AI-Friendly Architecture**: Minimal context coupling for easier understanding
- **Native FRP Features**: Direct use of FRP's locations parameter for simplicity

## Development Commands

**Note**: This project is currently in the design phase. The following commands will be available once implementation begins.

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
# Or use the provided installation script (to be created)
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

1. **Dual API Design**: Simple API for ease of use, Functional API for power users
   ```python
   # Simple API (기본)
   try:
       url = create_tunnel("example.com", 3000, "/myapp")
   except TunnelError as e:
       print(f"Error: {e}")
   
   # Functional API (고급)
   result = create_client("server.com")
   match result:
       case Ok(client): # handle success
       case Err(error): # handle error
   ```

2. **Result Monad** (내부 구현): All internal operations use `Result[T, E]` for explicit error handling

3. **Pipeline Pattern** (고급 기능): Function composition for complex operations
   ```python
   pipeline = pipe(
       create_http_tunnel,
       flat_map_result(validate_tunnel),
       map_result(generate_url)
   )
   ```

4. **Event Sourcing**: All state changes tracked as immutable events

### Directory Structure
```
src/
├── frp_wrapper/
│   ├── __init__.py      # Simple API exports (기본)
│   ├── simple/          # Simple Python API
│   │   ├── client.py    # 간단한 클라이언트 API
│   │   ├── tunnel.py    # 터널 관리 함수
│   │   └── exceptions.py # 예외 클래스
│   ├── functional/      # Advanced Functional API
│   │   ├── client.py    # Result 기반 클라이언트
│   │   ├── pipeline.py  # 파이프라인 패턴
│   │   └── result.py    # Result 타입 정의
│   ├── domain/          # Immutable domain models
│   ├── core/            # Pure business logic
│   ├── effects/         # Side effect protocols
│   ├── application/     # Service layer
│   └── infrastructure/  # External adapters
deploy/
├── docker/              # Docker 관련 파일
├── k8s/                 # Kubernetes 매니페스트
└── systemd/             # SystemD 서비스 파일
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
The wrapper uses FRP's native `locations` feature for path-based routing:
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

## Development Workflow

### Checkpoint-Based PRs
The project is divided into 8 checkpoints, organized in 3 phases:

#### Phase 1: Core Foundation
1. **Process Manager**
   - FRP binary process management
   - Process lifecycle management
   - Configuration file handling

2. **Basic Client**
   - FRP client connection management
   - Simple API design (예외 기반)
   - Connection state management

3. **Tunnel Management**
   - HTTP/TCP tunnel creation
   - Tunnel lifecycle management
   - Basic error handling

#### Phase 2: Advanced Features
4. **Path Routing**
   - FRP locations-based routing implementation
   - Direct path routing using FRP native features
   - Custom domains and locations

5. **Context Manager**
   - Automatic resource cleanup
   - Context manager patterns
   - Resource lifecycle management

6. **Server Tools**
   - FRP server configuration tools
   - SSL certificate management
   - Server installation scripts

#### Phase 3: Production Ready
7. **Monitoring & Observability**
   - Structured logging
   - Metrics collection
   - Error tracking

8. **Examples & Documentation**
   - Comprehensive examples
   - API documentation
   - Deployment guides

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

1. **Design Phase Project**: This is currently in the design and documentation phase. Implementation follows the checkpoint-based approach outlined below.
2. **External Dependencies**: Requires FRP binary (https://github.com/fatedier/frp) - the wrapper orchestrates FRP processes rather than reimplementing the protocol
3. **Korean Documentation**: Some documentation includes Korean annotations (도메인, 유스케이스, etc.) - this is intentional for the target audience
4. **Dual API Strategy**: 
   - Simple API (외부): Python exceptions for user-friendly interface
   - Functional Core (내부): Result[T, E] for internal operations
5. **Immutable First**: Create new instances instead of modifying existing ones
6. **FRP Configuration**: Uses TOML format with customDomains and locations for path-based routing

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

### Working with Documentation
```bash
# View architecture documentation
cat docs/architecture/domain-model.md
cat plan/01-architecture.md

# Review checkpoint progress
ls plan/checkpoints/

# View API specifications  
cat docs/spec/01-api-spec.md

# Check deployment configurations
ls deploy/docker/
ls deploy/k8s/
```

### Running Specific Checkpoint Tests (Future)
```bash
# Test specific checkpoint implementation (once implemented)
pytest tests/test_checkpoint_01_process_manager.py
pytest tests/test_checkpoint_02_basic_client.py
# etc...
```