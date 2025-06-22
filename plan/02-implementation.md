# FRP Python Wrapper 구현 계획

## 코드 구조

### 패키지 구조 (함수형 + DDD 기반)

```
src/
├── __init__.py           # 패키지 초기화, 버전 정보
├── domain/               # 도메인 모델 (불변 데이터)
│   ├── __init__.py
│   ├── tunnel.py         # Tunnel, HTTPTunnel, TunnelId, Port, Path
│   ├── process.py        # Process, ProcessId, BinaryPath
│   ├── config.py         # FRPConfig, ServerConfig, TunnelConfig
│   ├── events.py         # DomainEvent, TunnelCreated, ProcessStarted 등
│   └── types.py          # Result, Ok, Err, Option 타입
├── core/                 # 순수 함수 비즈니스 로직
│   ├── __init__.py
│   ├── tunnel_operations.py   # 터널 관련 순수 함수
│   ├── process_operations.py  # 프로세스 관련 순수 함수
│   ├── config_builder.py      # 설정 생성 순수 함수
│   ├── validators.py          # 유효성 검증 순수 함수
│   └── transformers.py        # 데이터 변환 순수 함수
├── effects/              # 부수 효과 처리 (인터페이스 + 구현)
│   ├── __init__.py
│   ├── protocols.py      # 이펙트 인터페이스 정의
│   ├── process_effects.py     # 프로세스 실행 이펙트
│   ├── file_effects.py        # 파일 I/O 이펙트
│   ├── network_effects.py     # 네트워크 이펙트
│   └── event_store.py         # 이벤트 저장소
├── application/          # 애플리케이션 서비스 (조합)
│   ├── __init__.py
│   ├── tunnel_service.py      # 터널 관리 서비스
│   ├── client_service.py      # 클라이언트 서비스
│   ├── pipelines.py           # 파이프라인 획득자
│   └── container.py           # 의존성 주입 컨테이너
├── infrastructure/       # 외부 시스템 통합
│   ├── __init__.py
│   ├── frpc_adapter.py        # FRP 바이너리 어댑터
│   ├── nginx_adapter.py       # Nginx 설정 어댑터
│   └── file_system.py         # 파일 시스템 구현
└── api/                  # 공개 API
    ├── __init__.py
    ├── client.py         # 메인 API 인터페이스
    ├── builders.py       # 함수형 빌더 API
    └── shortcuts.py      # 편의 함수
```

## 핵심 도메인 모델

### 1. Result 타입 (에러 처리)

```python
# src/domain/types.py
from typing import TypeVar, Generic, Union, Callable, Optional
from dataclasses import dataclass

T = TypeVar('T')
E = TypeVar('E')
U = TypeVar('U')

@dataclass
class Ok(Generic[T]):
    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def map(self, f: Callable[[T], U]) -> 'Result[U, E]':
        return Ok(f(self.value))

    def flat_map(self, f: Callable[[T], 'Result[U, E]']) -> 'Result[U, E]':
        return f(self.value)

    def unwrap(self) -> T:
        return self.value

@dataclass
class Err(Generic[E]):
    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def map(self, f: Callable[[T], U]) -> 'Result[U, E]':
        return self

    def flat_map(self, f: Callable[[T], 'Result[U, E]']) -> 'Result[U, E]':
        return self

    def unwrap(self) -> T:
        raise ValueError(f"Called unwrap on Err: {self.error}")

Result = Union[Ok[T], Err[E]]
```

### 2. 이벤트 시스템

```python
# src/domain/events.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from src.domain.tunnel import TunnelId
from src.domain.process import ProcessId

@dataclass
class DomainEvent:
    """도메인 이벤트 기본 클래스"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)

@dataclass
class TunnelCreated(DomainEvent):
    tunnel_id: TunnelId
    local_port: int
    path: Optional[str]

@dataclass
class TunnelConnected(DomainEvent):
    tunnel_id: TunnelId

@dataclass
class TunnelDisconnected(DomainEvent):
    tunnel_id: TunnelId
    reason: Optional[str] = None

@dataclass
class ProcessStarted(DomainEvent):
    process_id: ProcessId
    pid: int

@dataclass
class ProcessStopped(DomainEvent):
    process_id: ProcessId
    exit_code: Optional[int] = None
```

### 3. 순수 함수 레이어

```python
# src/core/tunnel_operations.py
from typing import List, Tuple
from src.domain.tunnel import Tunnel, HTTPTunnel, TunnelId, Port, Path
from src.domain.events import TunnelCreated, TunnelConnected
from src.domain.types import Result, Ok, Err
import uuid

def create_http_tunnel(
    local_port: int,
    path: str,
    strip_path: bool = True,
    websocket: bool = True
) -> Result[HTTPTunnel, str]:
    """
HTTP 터널 생성 - 순수 함수

    Args:
        local_port: 로컬 포트 번호
        path: URL 경로
        strip_path: 프록시 시 경로 제거 여부
        websocket: WebSocket 지원 여부

    Returns:
        Result[HTTPTunnel, str]: 성공 시 Ok(tunnel), 실패 시 Err(message)
    """
    try:
        tunnel = HTTPTunnel(
            id=TunnelId(str(uuid.uuid4())),
            local_port=Port(local_port),
            path=Path(path),
            strip_path=strip_path,
            websocket=websocket,
            vhost=f"{path}.local"
        )
        return Ok(tunnel)
    except ValueError as e:
        return Err(str(e))

def validate_tunnel(tunnel: Tunnel) -> Result[Tunnel, List[str]]:
    """터널 유효성 검증 - 순수 함수"""
    errors = []

    if tunnel.local_port.value < 1024:
        errors.append("Privileged ports (<1024) require root access")

    if isinstance(tunnel, HTTPTunnel) and tunnel.path:
        if len(tunnel.path.value) > 100:
            errors.append("Path too long (max 100 characters)")

    return Ok(tunnel) if not errors else Err(errors)

def tunnel_to_config(tunnel: Tunnel) -> dict:
    """터널을 설정 딕셔너리로 변환 - 순수 함수"""
    config = {
        "type": tunnel.tunnel_type,
        "local_port": tunnel.local_port.value
    }

    if isinstance(tunnel, HTTPTunnel):
        if tunnel.vhost:
            config["custom_domains"] = tunnel.vhost
        if tunnel.strip_path:
            config["route_by_http_user"] = tunnel.path.value if tunnel.path else ""

    return config
```

### 4. 이펙트 인터페이스

```python
# src/effects/protocols.py
from typing import Protocol, List, Optional
from src.domain.types import Result

class ProcessExecutor(Protocol):
    """프로세스 실행 인터페이스"""

    def spawn(self, command: List[str]) -> Result[int, str]:
        """프로세스 시작하고 PID 반환"""
        ...

    def terminate(self, pid: int) -> Result[None, str]:
        """프로세스 종료"""
        ...

    def is_alive(self, pid: int) -> bool:
        """프로세스 생존 확인"""
        ...

    def get_output(self, pid: int) -> Result[str, str]:
        """프로세스 출력 가져오기"""
        ...

class FileWriter(Protocol):
    """파일 작성 인터페이스"""

    def write(self, path: str, content: str) -> Result[str, str]:
        """파일 작성하고 경로 반환"""
        ...

    def write_temp(self, content: str, suffix: str = ".ini") -> Result[str, str]:
        """임시 파일 작성하고 경로 반환"""
        ...

    def delete(self, path: str) -> Result[None, str]:
        """파일 삭제"""
        ...

class EventStore(Protocol):
    """이벤트 저장소 인터페이스"""

    def append(self, event: DomainEvent) -> Result[None, str]:
        """이벤트 추가"""
        ...

    def get_events(self, entity_id: str) -> Result[List[DomainEvent], str]:
        """특정 엔티티의 이벤트 조회"""
        ...

    def get_all_events(self) -> Result[List[DomainEvent], str]:
        """모든 이벤트 조회"""
        ...
```

### 5. 파이프라인 패턴

```python
# src/application/pipelines.py
from functools import reduce
from typing import Callable, TypeVar, List
from src.domain.types import Result, Ok, Err

T = TypeVar('T')
U = TypeVar('U')
E = TypeVar('E')

def pipe(*functions: Callable) -> Callable:
    """함수들을 연결하는 파이프"""
    return reduce(lambda f, g: lambda x: g(f(x)), functions)

def map_result(f: Callable[[T], U]) -> Callable[[Result[T, E]], Result[U, E]]:
    """
Result 타입에 대한 map 함수"""
    def wrapper(result: Result[T, E]) -> Result[U, E]:
        return result.map(f)
    return wrapper

def flat_map_result(f: Callable[[T], Result[U, E]]) -> Callable[[Result[T, E]], Result[U, E]]:
    """Result 타입에 대한 flat_map 함수"""
    def wrapper(result: Result[T, E]) -> Result[U, E]:
        return result.flat_map(f)
    return wrapper

def sequence(results: List[Result[T, E]]) -> Result[List[T], E]:
    """Result 리스트를 Result<List>로 변환"""
    values = []
    for result in results:
        if result.is_err():
            return result
        values.append(result.unwrap())
    return Ok(values)

# 사용 예시
def create_and_validate_tunnel(
    local_port: int,
    path: str,
    effects: Effects
) -> Result[str, str]:
    """터널 생성 및 유효성 검증 파이프라인"""
    return pipe(
        lambda _: create_http_tunnel(local_port, path),
        flat_map_result(validate_tunnel),
        flat_map_result(lambda t: execute_tunnel_creation(t, effects)),
        map_result(lambda t: generate_tunnel_url(t, effects.base_url))
    )(None)
```

## 애플리케이션 서비스

### 터널 서비스

```python
# src/application/tunnel_service.py
from typing import Dict, List, Optional
from src.domain.tunnel import Tunnel, TunnelId
from src.domain.config import FRPConfig
from src.domain.process import Process
from src.domain.types import Result, Ok, Err
from src.core import tunnel_operations, config_builder
from src.effects.protocols import ProcessExecutor, FileWriter, EventStore

class TunnelService:
    """터널 관리 서비스 - 순수 함수들을 조합"""

    def __init__(
        self,
        config: FRPConfig,
        process: Process,
        process_executor: ProcessExecutor,
        file_writer: FileWriter,
        event_store: EventStore
    ):
        self._config = config
        self._process = process
        self._process_executor = process_executor
        self._file_writer = file_writer
        self._event_store = event_store
        self._tunnels: Dict[str, Tunnel] = {}

    def create_http_tunnel(
        self,
        local_port: int,
        path: str,
        **options
    ) -> Result[Tunnel, str]:
        """
HTTP 터널 생성"""
        # 1. 터널 생성 (순수)
        tunnel_result = tunnel_operations.create_http_tunnel(
            local_port, path, **options
        )

        if tunnel_result.is_err():
            return tunnel_result

        tunnel = tunnel_result.unwrap()

        # 2. 유효성 검증 (순수)
        validation_result = tunnel_operations.validate_tunnel(tunnel)
        if validation_result.is_err():
            return Err("\n".join(validation_result.error))

        # 3. 설정 업데이트 (순수)
        tunnel_config = tunnel_operations.tunnel_to_config(tunnel)
        new_config = self._config.add_tunnel(
            config_builder.create_tunnel_config(
                tunnel.id.value,
                tunnel_config
            )
        )

        # 4. 이펙트 실행 - 설정 파일 작성
        config_content = config_builder.build_ini_content(new_config)
        write_result = self._file_writer.write_temp(config_content)

        if write_result.is_err():
            return Err(f"Failed to write config: {write_result.error}")

        config_path = write_result.unwrap()

        # 5. 이펙트 실행 - 프로세스 재시작
        restart_result = self._restart_process(config_path)
        if restart_result.is_err():
            return restart_result

        # 6. 상태 업데이트
        self._config = new_config
        self._tunnels[tunnel.id.value] = tunnel

        # 7. 이벤트 발행
        event = TunnelCreated(
            tunnel_id=tunnel.id,
            local_port=local_port,
            path=path
        )
        self._event_store.append(event)

        return Ok(tunnel)

    def _restart_process(self, config_path: str) -> Result[None, str]:
        """프로세스 재시작"""
        # 기존 프로세스 종료
        if self._process.pid:
            terminate_result = self._process_executor.terminate(self._process.pid)
            if terminate_result.is_err():
                return terminate_result

        # 새 프로세스 시작
        command = [self._process.binary_path.value, '-c', config_path]
        spawn_result = self._process_executor.spawn(command)

        if spawn_result.is_err():
            return Err(f"Failed to start process: {spawn_result.error}")

        # 프로세스 상태 업데이트
        new_pid = spawn_result.unwrap()
        self._process = self._process.with_status("running", pid=new_pid)

        return Ok(None)
```

## 테스트 전략

### 속성 기반 테스트

```python
# tests/test_properties.py
from hypothesis import given, strategies as st
from src.domain.tunnel import Port, Path
from src.core.tunnel_operations import create_http_tunnel

@given(
    port=st.integers(min_value=1, max_value=65535),
    path=st.text(min_size=1, max_size=100).filter(lambda x: not x.startswith('/'))
)
def test_create_tunnel_always_valid(port: int, path: str):
    """유효한 입력에 대해 항상 성공"""
    result = create_http_tunnel(port, path)
    assert result.is_ok()
    tunnel = result.unwrap()
    assert tunnel.local_port.value == port
    assert tunnel.path.value == path

@given(
    tunnels=st.lists(
        st.tuples(
            st.integers(min_value=1024, max_value=65535),
            st.text(min_size=1, max_size=50)
        ),
        min_size=0,
        max_size=10
    )
)
def test_tunnel_creation_idempotent(tunnels):
    """같은 입력에 대해 같은 결과"""
    results1 = [create_http_tunnel(port, path) for port, path in tunnels]
    results2 = [create_http_tunnel(port, path) for port, path in tunnels]

    for r1, r2 in zip(results1, results2):
        assert r1.is_ok() == r2.is_ok()
        if r1.is_ok():
            # ID는 다르지만 다른 속성은 같아야 함
            t1, t2 = r1.unwrap(), r2.unwrap()
            assert t1.local_port == t2.local_port
            assert t1.path == t2.path
```

### 순수 함수 테스트

```python
# tests/test_pure_functions.py
import pytest
from src.core.config_builder import build_ini_content, validate_config
from src.domain.config import FRPConfig, ServerConfig

def test_build_ini_content_pure():
    """같은 입력에 대해 항상 같은 출력"""
    config = FRPConfig(
        server=ServerConfig("example.com", 7000),
        tunnels=[]
    )

    result1 = build_ini_content(config)
    result2 = build_ini_content(config)

    assert result1 == result2

def test_validate_config_no_side_effects():
    """유효성 검증이 입력을 변경하지 않음"""
    config = FRPConfig(
        server=ServerConfig("", 7000),  # Invalid
        tunnels=[]
    )

    original_server = config.server.address
    result = validate_config(config)

    assert result.is_err()
    assert config.server.address == original_server  # 변경 없음
```

### 이펙트 모킹

```python
# tests/test_effects.py
from unittest.mock import Mock
from src.domain.types import Ok, Err
from src.effects.protocols import ProcessExecutor, FileWriter

def test_tunnel_service_with_mocked_effects():
    """모킹된 이펙트로 서비스 테스트"""
    # Mock 생성
    process_executor = Mock(spec=ProcessExecutor)
    process_executor.spawn.return_value = Ok(12345)
    process_executor.terminate.return_value = Ok(None)

    file_writer = Mock(spec=FileWriter)
    file_writer.write_temp.return_value = Ok("/tmp/test.ini")

    # 서비스 테스트
    service = TunnelService(
        config=create_test_config(),
        process=create_test_process(),
        process_executor=process_executor,
        file_writer=file_writer,
        event_store=Mock()
    )

    result = service.create_http_tunnel(3000, "test")

    assert result.is_ok()
    assert process_executor.spawn.called
    assert file_writer.write_temp.called
```

## 공개 API 설계

### 함수형 인터페이스

```python
# src/api/client.py
from typing import Optional, Dict, Any
from src.domain.types import Result
from src.domain.tunnel import Tunnel
from src.application.container import Container

def create_client(
    server: str,
    port: int = 7000,
    auth_token: Optional[str] = None,
    **options
) -> Result[Client, str]:
    """클라이언트 생성"""
    container = Container()
    container.configure(server, port, auth_token, **options)

    return Ok(Client(container))

class Client:
    """클라이언트 API 래퍼"""

    def __init__(self, container: Container):
        self._container = container
        self._tunnel_service = container.resolve(TunnelService)

    def expose_path(
        self,
        local_port: int,
        path: str,
        **options
    ) -> Result[Tunnel, str]:
        """
HTTP 경로 노출"""
        return self._tunnel_service.create_http_tunnel(
            local_port, path, **options
        )

    def with_tunnel(self, local_port: int, path: str, **options):
        """
Context manager로 임시 터널"""
        from contextlib import contextmanager

        @contextmanager
        def tunnel_context():
            result = self.expose_path(local_port, path, **options)
            if result.is_err():
                raise RuntimeError(result.error)

            tunnel = result.unwrap()
            try:
                yield tunnel
            finally:
                self._tunnel_service.close_tunnel(tunnel.id)

        return tunnel_context()
```

### 편의 함수

```python
# src/api/shortcuts.py
from src.api.client import create_client
from src.application.pipelines import pipe

def quick_tunnel(server: str, local_port: int, path: str) -> Result[str, str]:
    """빠른 터널 생성 및 URL 반환"""
    return pipe(
        lambda _: create_client(server),
        flat_map_result(lambda c: c.expose_path(local_port, path)),
        map_result(lambda t: generate_tunnel_url(t, f"https://{server}"))
    )(None)

def temporary_tunnel(server: str, local_port: int, path: str, **options):
    """임시 터널 context manager"""
    from contextlib import contextmanager

    @contextmanager
    def temp_tunnel():
        client_result = create_client(server, **options)
        if client_result.is_err():
            raise RuntimeError(client_result.error)

        client = client_result.unwrap()
        with client.with_tunnel(local_port, path) as tunnel:
            yield tunnel

    return temp_tunnel()
```

## 성능 고려사항

### 불변성과 성능
- 구조적 공유를 통한 메모리 효율성
- 변경이 적은 데이터는 frozen dataclass 사용
- 큰 데이터는 참조만 전달

### 이펙트 최적화
- 이펙트는 배치 처리 가능하도록 설계
- 비동기 I/O 지원
- 연결 풀링

### 함수 조합 최적화
- 자주 사용되는 파이프라인은 미리 정의
- 부분 적용(partial application) 활용
- 메모이제이션 적용 가능
