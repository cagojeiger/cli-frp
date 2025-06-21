# 함수형 프로그래밍 설계 가이드

FRP Python Wrapper는 함수형 프로그래밍 패러다임을 따라 설계되었습니다. 이 문서는 프로젝트에서 사용되는 함수형 패턴과 원칙을 설명합니다.

## 핵심 원칙

### 1. 불변성 (Immutability)
모든 데이터 구조는 불변으로 설계되어 있습니다.

```python
from dataclasses import dataclass, frozen

@frozen
@dataclass
class Client:
    """불변 클라이언트 객체"""
    id: ClientId
    server: ServerAddress
    connection_state: ConnectionState
    
    def with_connection(self, state: ConnectionState) -> 'Client':
        """새로운 연결 상태를 가진 클라이언트 반환"""
        return dataclasses.replace(self, connection_state=state)
```

### 2. 순수 함수 (Pure Functions)
비즈니스 로직은 부수 효과가 없는 순수 함수로 구현됩니다.

```python
def create_tcp_tunnel(
    client_id: ClientId,
    local_port: int,
    remote_port: Optional[int] = None
) -> Result[TCPTunnel, str]:
    """TCP 터널 생성 - 순수 함수"""
    # 같은 입력에 대해 항상 같은 출력
    # 외부 상태를 변경하지 않음
    # I/O 작업 없음
```

### 3. 명시적 효과 (Explicit Effects)
I/O와 부수 효과는 명확히 분리되고 인터페이스로 정의됩니다.

```python
class ProcessExecutor(Protocol):
    """프로세스 실행 인터페이스"""
    def spawn(self, command: List[str]) -> Result[int, str]:
        """프로세스 시작하고 PID 반환"""
        ...
```

## Result 타입

### 기본 사용법

```python
from typing import TypeVar, Generic, Union

T = TypeVar('T')
E = TypeVar('E')

@dataclass
class Ok(Generic[T]):
    value: T
    
    def is_ok(self) -> bool:
        return True
    
    def map(self, f: Callable[[T], U]) -> 'Result[U, E]':
        return Ok(f(self.value))
    
    def flat_map(self, f: Callable[[T], 'Result[U, E]']) -> 'Result[U, E]':
        return f(self.value)

@dataclass
class Err(Generic[E]):
    error: E
    
    def is_ok(self) -> bool:
        return False
    
    def map(self, f: Callable[[T], U]) -> 'Result[U, E]':
        return self
    
    def flat_map(self, f: Callable[[T], 'Result[U, E]']) -> 'Result[U, E]':
        return self

Result = Union[Ok[T], Err[E]]
```

### 패턴 매칭

Python 3.10+의 match 문을 사용한 우아한 에러 처리:

```python
result = create_client("tunnel.example.com")

match result:
    case Ok(client):
        print(f"연결됨: {client.server.host}")
    case Err(error):
        print(f"연결 실패: {error}")
```

### 연쇄 연산

```python
# map: 성공 값을 변환
url_result = client_result.map(lambda c: c.server.host)

# flat_map: Result를 반환하는 함수를 연결
tunnel_result = client_result.flat_map(
    lambda c: c.expose_path(3000, "app")
)

# 기본값 처리
url = tunnel_result.map(lambda t: t.url).unwrap_or("http://localhost:3000")
```

## 파이프라인 패턴

### 함수 조합

```python
from functools import reduce

def pipe(*functions: Callable) -> Callable:
    """함수들을 연결하는 파이프"""
    return reduce(lambda f, g: lambda x: g(f(x)), functions)

# 사용 예
tunnel_pipeline = pipe(
    create_client,
    lambda c: c.expose_path(3000, "app"),
    lambda t: t.url
)

url = tunnel_pipeline("tunnel.example.com")
```

### Result 파이프라인

```python
def map_result(f: Callable[[T], U]) -> Callable[[Result[T, E]], Result[U, E]]:
    """Result 타입에 대한 map 함수"""
    def wrapper(result: Result[T, E]) -> Result[U, E]:
        return result.map(f)
    return wrapper

def flat_map_result(f: Callable[[T], Result[U, E]]) -> Callable[[Result[T, E]], Result[U, E]]:
    """Result 타입에 대한 flat_map 함수"""
    def wrapper(result: Result[T, E]) -> Result[U, E]:
        return result.flat_map(f)
    return wrapper

# 사용 예
result = pipe(
    lambda _: create_client("tunnel.example.com"),
    flat_map_result(lambda c: c.expose_path(3000, "app")),
    map_result(lambda t: t.url)
)(None)
```

## 이벤트 소싱

모든 상태 변경은 이벤트로 추적됩니다:

```python
@dataclass
class DomainEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)

@dataclass
class TunnelCreated(DomainEvent):
    tunnel_id: TunnelId
    tunnel_type: str

def connect_tunnel(tunnel: Tunnel) -> Tuple[Tunnel, TunnelConnected]:
    """터널 연결 - 새 상태와 이벤트 반환"""
    connected_tunnel = tunnel.with_status("connected")
    event = TunnelConnected(tunnel_id=tunnel.id)
    return connected_tunnel, event
```

## 의존성 주입

이펙트는 인터페이스를 통해 주입됩니다:

```python
class TunnelService:
    def __init__(
        self,
        process_executor: ProcessExecutor,
        file_writer: FileWriter,
        port_allocator: PortAllocator,
        event_store: EventStore
    ):
        # 모든 이펙트는 인터페이스로 주입
        self._process_executor = process_executor
        self._file_writer = file_writer
        self._port_allocator = port_allocator
        self._event_store = event_store
```

## 테스트 전략

### 순수 함수 테스트

```python
def test_create_tcp_tunnel():
    # 순수 함수는 쉽게 테스트 가능
    result = create_tcp_tunnel(ClientId("test"), 3000, 8080)
    
    assert result.is_ok()
    tunnel = result.unwrap()
    assert tunnel.config.local_port.value == 3000
    assert tunnel.config.remote_port.value == 8080
```

### 속성 기반 테스트

```python
from hypothesis import given, strategies as st

@given(
    port=st.integers(min_value=1, max_value=65535),
    path=st.text(min_size=1, max_size=100)
)
def test_create_tunnel_properties(port: int, path: str):
    """유효한 입력에 대해 항상 성공"""
    result = create_http_tunnel(ClientId("test"), port, path)
    
    if 1 <= port <= 65535 and not path.startswith('/'):
        assert result.is_ok()
        tunnel = result.unwrap()
        assert tunnel.config.local_port.value == port
        assert tunnel.path == path
```

### 이펙트 모킹

```python
def test_tunnel_service_with_mocks():
    # Mock 생성
    process_executor = Mock(spec=ProcessExecutor)
    process_executor.spawn.return_value = Ok(12345)
    
    # 서비스 테스트
    service = TunnelService(
        process_executor=process_executor,
        # ... 다른 mock들
    )
    
    result = service.create_tcp_tunnel(client, 3000)
    assert result.is_ok()
```

## 실용적인 팁

### 1. 에러 누적

여러 작업의 에러를 수집:

```python
def collect_errors(results: List[Result[T, E]]) -> Tuple[List[T], List[E]]:
    """Result 리스트에서 성공과 실패 분리"""
    values = []
    errors = []
    
    for result in results:
        match result:
            case Ok(value):
                values.append(value)
            case Err(error):
                errors.append(error)
    
    return values, errors
```

### 2. 시퀀스 처리

```python
def sequence(results: List[Result[T, E]]) -> Result[List[T], E]:
    """Result 리스트를 Result<List>로 변환"""
    values = []
    for result in results:
        if result.is_err():
            return result
        values.append(result.unwrap())
    return Ok(values)
```

### 3. 트래버스

```python
def traverse(
    f: Callable[[T], Result[U, E]],
    items: List[T]
) -> Result[List[U], E]:
    """리스트의 각 항목에 함수를 적용하고 결과를 수집"""
    return sequence([f(item) for item in items])
```

## 장점

1. **예측 가능성**: 순수 함수는 테스트하기 쉽고 버그가 적습니다
2. **조합성**: 작은 함수들을 조합하여 복잡한 로직 구성
3. **병렬성**: 불변 데이터는 동시성 문제가 없습니다
4. **디버깅**: 상태 변경이 명시적이어서 추적이 쉽습니다

## 주의사항

1. **학습 곡선**: 함수형 패러다임에 익숙하지 않은 개발자에게는 어려울 수 있습니다
2. **메모리 사용**: 불변성으로 인한 객체 복사가 많을 수 있습니다 (구조적 공유로 최적화)
3. **타입 복잡성**: 제네릭과 고차 함수로 인한 타입 시그니처가 복잡할 수 있습니다

## 참고 자료

- [Functional Programming in Python](https://docs.python.org/3/howto/functional.html)
- [Railway Oriented Programming](https://fsharpforfunandprofit.com/rop/)
- [Algebraic Data Types in Python](https://github.com/python/typing/issues/1021)