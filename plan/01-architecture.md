# FRP Python Wrapper 아키텍처 설계

## 설계 원칙

### 함수형 프로그래밍 원칙
- **불변성(Immutability)**: 모든 데이터 구조는 불변
- **순수 함수(Pure Functions)**: 부수 효과 없는 비즈니스 로직
- **함수 조합(Function Composition)**: 작은 함수들을 조합하여 복잡한 기능 구현
- **명시적 효과(Explicit Effects)**: I/O와 부수 효과를 명확히 분리

### Domain-Driven Design 원칙
- **도메인 중심**: 비즈니스 도메인을 코드의 중심에 배치
- **유비쿼터스 언어**: 도메인 전문가와 개발자가 같은 언어 사용
- **경계 컨텍스트**: 명확한 모듈 경계 설정
- **이벤트 소싱**: 상태 변경을 이벤트로 추적

## 전체 아키텍처

### 시스템 구성도

```
┌─────────────────┐     HTTPS       ┌──────────────────┐
│   외부 사용자    │ ─────────────> │   FRP Server     │
└─────────────────┘  example.com    │   (7000, 8080)   │
                      /myapp/*      │                  │
                                    │ locations 라우팅  │
                                    └────────┬─────────┘
                                             │
┌─────────────────┐     Control     ┌────────┴─────────┐
│   FRP Client    │ <─────────────> │  FRP Control     │
│   (Python)      │     (7000)      │   Connection     │
└────────┬────────┘                 └──────────────────┘
         │
┌────────┴────────┐
│  Local Service  │
│   (port 3000)   │
└─────────────────┘
```

### 레이어 아키텍처

```
┌─────────────────────────────────────────┐
│          API Layer (공개 인터페이스)      │
├─────────────────────────────────────────┤
│     Application Layer (유스케이스)       │
├─────────────────────────────────────────┤
│        Domain Layer (비즈니스 로직)      │
├─────────────────────────────────────────┤
│      Effects Layer (부수 효과 처리)      │
├─────────────────────────────────────────┤
│   Infrastructure Layer (외부 시스템)     │
└─────────────────────────────────────────┘
```

### 데이터 플로우

```
User Input
    │
    ▼
Pure Functions (Validation & Transformation)
    │
    ▼
Domain Events
    │
    ▼
Effect Handlers (I/O Operations)
    │
    ▼
Result<Success, Error>
```

### FRP 프록시 설정 플로우

```
API Call: create_tunnel(domain, port, path)
    │
    ▼
Generate FRP Config with locations
    │
    ▼
Write TOML Configuration
    │
    ▼
Start/Reload FRP Client
    │
    ▼
Return URL: https://domain/path/
```

## 핵심 도메인 모델

## 1. Process (프로세스 도메인)

### 도메인 모델 (불변 데이터)
```python
from dataclasses import dataclass, frozen
from typing import Optional
from datetime import datetime

# 값 객체
@frozen
@dataclass
class ProcessId:
    value: str

@frozen
@dataclass
class BinaryPath:
    value: str
    
    def __post_init__(self):
        if not os.path.exists(self.value):
            raise ValueError(f"Binary not found: {self.value}")

# 엔티티
@frozen
@dataclass
class Process:
    id: ProcessId
    binary_path: BinaryPath
    config_path: str
    status: str = "stopped"  # stopped, starting, running, stopping
    pid: Optional[int] = None
    started_at: Optional[datetime] = None
    
    def with_status(self, status: str, **kwargs) -> 'Process':
        """새로운 상태를 가진 프로세스 인스턴스 반환"""
        return dataclass.replace(self, status=status, **kwargs)
```

### 순수 함수 (비즈니스 로직)
```python
# src/core/process_operations.py
from typing import Tuple, Optional
from src.domain.process import Process, ProcessId
from src.domain.events import ProcessStarted, ProcessStopped

def create_process(binary_path: str, config_path: str) -> Process:
    """프로세스 생성 - 순수 함수"""
    return Process(
        id=ProcessId(str(uuid.uuid4())),
        binary_path=BinaryPath(binary_path),
        config_path=config_path
    )

def start_process(process: Process, pid: int) -> Tuple[Process, ProcessStarted]:
    """프로세스 시작 - 새 상태와 이벤트 반환"""
    if process.status != "stopped":
        raise InvalidStateError(f"Cannot start process in {process.status} state")
    
    new_process = process.with_status(
        "running",
        pid=pid,
        started_at=datetime.now()
    )
    
    event = ProcessStarted(
        process_id=process.id,
        pid=pid,
        occurred_at=datetime.now()
    )
    
    return new_process, event
```

### 이펙트 핸들러 (부수 효과)
```python
# src/effects/process_effects.py
from typing import Protocol
import subprocess

class ProcessExecutor(Protocol):
    """프로세스 실행 인터페이스"""
    def spawn(self, command: List[str]) -> int:
        """프로세스 시작하고 PID 반환"""
        ...
    
    def terminate(self, pid: int) -> None:
        """프로세스 종료"""
        ...
    
    def is_alive(self, pid: int) -> bool:
        """프로세스 생존 확인"""
        ...

# 실제 구현
class SubprocessExecutor:
    def spawn(self, command: List[str]) -> int:
        process = subprocess.Popen(command)
        return process.pid
```

## 2. Configuration (설정 도메인)

### 도메인 모델
```python
# src/domain/config.py
from dataclasses import dataclass, frozen
from typing import Dict, List, Optional

@frozen
@dataclass
class ServerConfig:
    address: str
    port: int = 7000
    auth_token: Optional[str] = None

@frozen
@dataclass
class TunnelConfig:
    name: str
    tunnel_type: str  # "tcp", "udp", "http"
    local_port: int
    remote_config: Dict[str, Any]

@frozen
@dataclass
class FRPConfig:
    server: ServerConfig
    tunnels: List[TunnelConfig]
    
    def add_tunnel(self, tunnel: TunnelConfig) -> 'FRPConfig':
        """새 터널이 추가된 설정 반환"""
        return dataclass.replace(
            self,
            tunnels=self.tunnels + [tunnel]
        )
    
    def remove_tunnel(self, name: str) -> 'FRPConfig':
        """터널이 제거된 설정 반환"""
        return dataclass.replace(
            self,
            tunnels=[t for t in self.tunnels if t.name != name]
        )
```

### 순수 함수
```python
# src/core/config_builder.py
from typing import List, Dict
from src.domain.config import FRPConfig, TunnelConfig

def create_config(server_addr: str, port: int = 7000) -> FRPConfig:
    """설정 생성 - 순수 함수"""
    return FRPConfig(
        server=ServerConfig(address=server_addr, port=port),
        tunnels=[]
    )

def build_ini_content(config: FRPConfig) -> str:
    """설정을 INI 형식으로 변환 - 순수 함수"""
    lines = ['[common]']
    lines.append(f'server_addr = {config.server.address}')
    lines.append(f'server_port = {config.server.port}')
    
    if config.server.auth_token:
        lines.append(f'token = {config.server.auth_token}')
    
    for tunnel in config.tunnels:
        lines.append(f'\n[{tunnel.name}]')
        lines.append(f'type = {tunnel.tunnel_type}')
        lines.append(f'local_port = {tunnel.local_port}')
        
        for key, value in tunnel.remote_config.items():
            lines.append(f'{key} = {value}')
    
    return '\n'.join(lines)

def validate_config(config: FRPConfig) -> Result[FRPConfig, List[str]]:
    """설정 유효성 검증 - 순수 함수"""
    errors = []
    
    if not config.server.address:
        errors.append("Server address is required")
    
    for tunnel in config.tunnels:
        if tunnel.local_port < 1 or tunnel.local_port > 65535:
            errors.append(f"Invalid port for tunnel {tunnel.name}")
    
    return Ok(config) if not errors else Err(errors)
```

## 3. Tunnel (터널 도메인)

### 도메인 모델
```python
# src/domain/tunnel.py
from dataclasses import dataclass, frozen
from typing import Optional
from datetime import datetime

@frozen
@dataclass
class TunnelId:
    value: str

@frozen
@dataclass
class Port:
    value: int
    
    def __post_init__(self):
        if not 1 <= self.value <= 65535:
            raise ValueError(f"Invalid port: {self.value}")

@frozen
@dataclass
class Path:
    value: str
    
    def __post_init__(self):
        if self.value.startswith('/'):
            raise ValueError("Path must not start with /")

@frozen
@dataclass
class Tunnel:
    id: TunnelId
    local_port: Port
    tunnel_type: str
    path: Optional[Path] = None
    status: str = "pending"  # pending, connecting, connected, disconnected
    created_at: datetime = field(default_factory=datetime.now)
    connected_at: Optional[datetime] = None
    
    def with_status(self, status: str, **kwargs) -> 'Tunnel':
        """새로운 상태를 가진 터널 반환"""
        return dataclass.replace(self, status=status, **kwargs)

@frozen
@dataclass
class HTTPTunnel(Tunnel):
    """HTTP 전용 터널"""
    tunnel_type: str = "http"
    custom_domains: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    strip_path: bool = True
    websocket: bool = True
```

### 순수 함수
```python
# src/core/tunnel_operations.py
from typing import Tuple
from src.domain.tunnel import Tunnel, TunnelId, Port, Path
from src.domain.events import TunnelCreated, TunnelConnected

def create_http_tunnel(
    domain: str,
    local_port: int,
    path: str,
    strip_path: bool = True
) -> Tunnel:
    """HTTP 터널 생성 - 순수 함수"""
    return HTTPTunnel(
        id=TunnelId(str(uuid.uuid4())),
        local_port=Port(local_port),
        path=Path(path),
        custom_domains=[domain],
        locations=[path],
        strip_path=strip_path
    )

def connect_tunnel(
    tunnel: Tunnel
) -> Tuple[Tunnel, TunnelConnected]:
    """터널 연결 - 새 상태와 이벤트 반환"""
    if tunnel.status != "pending":
        raise InvalidStateError(f"Cannot connect tunnel in {tunnel.status} state")
    
    connected_tunnel = tunnel.with_status(
        "connected",
        connected_at=datetime.now()
    )
    
    event = TunnelConnected(
        tunnel_id=tunnel.id,
        occurred_at=datetime.now()
    )
    
    return connected_tunnel, event

def generate_tunnel_url(
    tunnel: HTTPTunnel,
    base_url: str = None
) -> str:
    """터널 URL 생성 - 순수 함수"""
    # 커스텀 도메인과 locations를 사용
    if tunnel.custom_domains and tunnel.locations:
        domain = tunnel.custom_domains[0]
        location = tunnel.locations[0]
        return f"https://{domain}{location}/"
    return base_url or "https://example.com/"
```

## 4. Application Services (애플리케이션 서비스)

### 서비스 레이어
```python
# src/application/tunnel_service.py
from typing import List, Optional
from src.domain.tunnel import Tunnel
from src.domain.events import DomainEvent
from src.core.tunnel_operations import create_http_tunnel, connect_tunnel
from src.effects.process_effects import ProcessExecutor
from src.effects.file_effects import FileWriter

class TunnelService:
    """터널 관리 서비스 - 순수 함수들을 조합"""
    
    def __init__(
        self,
        process_executor: ProcessExecutor,
        file_writer: FileWriter,
        event_store: EventStore
    ):
        self.process_executor = process_executor
        self.file_writer = file_writer
        self.event_store = event_store
        self._tunnels: Dict[str, Tunnel] = {}
    
    def create_tunnel(
        self,
        local_port: int,
        path: str,
        **options
    ) -> Result[Tunnel, Error]:
        """터널 생성 유스케이스"""
        # 1. 도메인 로직 (순수)
        tunnel = create_http_tunnel(local_port, path, **options)
        
        # 2. 설정 업데이트 (순수)
        new_config = self._current_config.add_tunnel(
            tunnel_to_config(tunnel)
        )
        
        # 3. 이펙트 실행
        result = pipe(
            lambda _: write_config(new_config, self.file_writer),
            flat_map(lambda path: restart_process(self.process, path, self.process_executor)),
            map(lambda _: tunnel)
        )(None)
        
        # 4. 성공 시 이벤트 저장
        if result.is_ok():
            self._tunnels[tunnel.id.value] = tunnel
            self.event_store.append(TunnelCreated(tunnel_id=tunnel.id))
        
        return result
```

### 파이프라인 사용
```python
# src/application/pipelines.py
from functools import reduce
from typing import Callable, TypeVar

T = TypeVar('T')
U = TypeVar('U')

def pipe(*functions: Callable) -> Callable:
    """함수들을 연결하는 파이프"""
    return reduce(lambda f, g: lambda x: g(f(x)), functions)

def create_and_connect_tunnel(
    local_port: int,
    path: str,
    effects: Effects
) -> Result[str, Error]:
    """터널 생성 및 연결 파이프라인"""
    return pipe(
        lambda _: create_http_tunnel(local_port, path),
        lambda tunnel: execute_tunnel_creation(tunnel, effects),
        flat_map(lambda tunnel: wait_for_connection(tunnel, effects)),
        map(lambda tunnel: generate_tunnel_url(tunnel, effects.base_url))
    )(None)
```

## 서브패스 라우팅 메커니즘

### FRP의 locations 기능 활용
FRP는 `locations` 파라미터를 통해 경로 기반 라우팅을 네이티브로 지원합니다.

### 구현 방식

1. **FRP locations 설정**
   ```toml
   [[proxies]]
   name = "myapp"
   type = "http"
   localPort = 3000
   customDomains = ["example.com"]
   locations = ["/myapp"]  # 경로 기반 라우팅
   ```

2. **Python 클라이언트 구현**
   ```python
   def create_tunnel(domain: str, port: int, path: str) -> str:
       config = {
           "name": f"tunnel_{path}",
           "type": "http",
           "localPort": port,
           "customDomains": [domain],
           "locations": [path]
       }
       return frp_client.create_proxy(config)
   ```

3. **요청 흐름**
   ```
   https://example.com/myapp/api → FRP Server → Local:3000/api
   ```

## 데이터 흐름

### 터널 생성 과정

1. **API 호출**
   ```python
   tunnel = client.expose_path(3000, "myapp")
   ```

2. **설정 생성**
   - ConfigBuilder가 INI 파일 생성
   - 가상 호스트 `myapp.local` 설정

3. **프로세스 재시작**
   - 새 설정으로 FRP 클라이언트 재시작
   - 서버와 터널 연결 수립

4. **URL 반환**
   - `https://tunnel.example.com/myapp/` 형태

### 요청 처리 과정

1. **외부 요청**
   - `https://example.com/myapp/api/users`

2. **FRP 서버 처리**
   - locations 기반 라우팅: `/myapp` → 해당 프록시
   - 해당 클라이언트로 전달

3. **로컬 서비스**
   - 요청 수신: `/api/users` (strip_path 옵션에 따라)
   - 응답 생성

## 에러 처리 전략

### 연결 실패
- Exponential backoff으로 재연결
- 최대 재시도 횟수 제한
- 사용자 콜백 지원

### 프로세스 충돌
- 자동 재시작
- 상태 복원
- 로그 보존

### 설정 오류
- 사전 유효성 검증
- 명확한 에러 메시지
- 롤백 지원

## 확장성 고려사항

### 다중 터널
- 터널 ID 기반 관리
- 동시 연결 수 제한
- 리소스 풀링

### 비동기 지원
- 선택적 asyncio 통합
- 이벤트 기반 알림
- Non-blocking 작업

### 플러그인 시스템
- 커스텀 프로토콜 지원
- 미들웨어 체인
- 확장 포인트