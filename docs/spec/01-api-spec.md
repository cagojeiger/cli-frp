# API 명세

## 개요

FRP Python Wrapper의 공개 API를 정의합니다. 함수형 프로그래밍 패러다임을 따르며, 모든 함수는 순수하고 부수 효과는 명시적으로 격리됩니다.

## 목차

1. [핵심 타입](#핵심-타입)
2. [클라이언트 API](#클라이언트-api)
3. [터널 관리](#터널-관리)
4. [파이프라인 및 조합자](#파이프라인-및-조합자)
5. [이벤트 처리](#이벤트-처리)
6. [유틸리티 함수](#유틸리티-함수)
7. [예외 처리](#예외-처리)

## 핵심 타입

### Result 타입 (에러 처리)

```python
from typing import TypeVar, Generic, Union, Callable

T = TypeVar('T')
E = TypeVar('E')

class Ok(Generic[T]):
    """성공 결과를 나타내는 타입"""
    value: T
    
    def is_ok(self) -> bool: ...
    def is_err(self) -> bool: ...
    def map(self, f: Callable[[T], U]) -> 'Result[U, E]': ...
    def flat_map(self, f: Callable[[T], 'Result[U, E]']) -> 'Result[U, E]': ...
    def unwrap(self) -> T: ...
    def unwrap_or(self, default: T) -> T: ...

class Err(Generic[E]):
    """실패 결과를 나타내는 타입"""
    error: E
    
    def is_ok(self) -> bool: ...
    def is_err(self) -> bool: ...
    def map(self, f: Callable[[T], U]) -> 'Result[U, E]': ...
    def flat_map(self, f: Callable[[T], 'Result[U, E]']) -> 'Result[U, E]': ...
    def unwrap(self) -> T: ...  # Raises ValueError
    def unwrap_or(self, default: T) -> T: ...

Result = Union[Ok[T], Err[E]]
```

### 도메인 타입

```python
from dataclasses import dataclass, frozen
from datetime import datetime

@frozen
@dataclass
class TunnelId:
    """터널 고유 ID"""
    value: str

@frozen
@dataclass
class Port:
    """포트 번호 (유효성 검증 포함)"""
    value: int
    
    def __post_init__(self):
        if not 1 <= self.value <= 65535:
            raise ValueError(f"Invalid port: {self.value}")

@frozen
@dataclass
class Path:
    """URL 경로 (유효성 검증 포함)"""
    value: str
    
    def __post_init__(self):
        if self.value.startswith('/'):
            raise ValueError("Path must not start with /")
```

## 클라이언트 API

### 클라이언트 생성 함수

```python
def create_client(
    server: str,
    port: int = 7000,
    auth_token: Optional[str] = None,
    **options
) -> Result[Client, str]:
    """
FRP 클라이언트 생성
    
    Args:
        server: FRP 서버 주소
        port: FRP 서버 포트 (기본: 7000)
        auth_token: 인증 토큰 (선택)
        **options: 추가 옵션
    
    Returns:
        Result[Client, str]: 성공 시 Ok(client), 실패 시 Err(message)
    
    Example:
        >>> result = create_client("tunnel.example.com")
        >>> if result.is_ok():
        ...     client = result.unwrap()
        ...     # 클라이언트 사용
        ... else:
        ...     print(f"Error: {result.error}")
    """
```

### Client 타입

```python
class Client:
    """
FRP 클라이언트
    
    불변 객체로 설계되어 있으며, 모든 작업은 Result 타입을 반환합니다.
    """
    
    def expose_path(
        self,
        local_port: int,
        path: str,
        **options
    ) -> Result[Tunnel, str]:
        """
HTTP 경로 노출
        
        Args:
            local_port: 로컬 포트 번호
            path: URL 경로 (슬래시 없이)
            **options: 추가 옵션
                - strip_path: 프록시 시 경로 제거 (기본: True)
                - websocket: WebSocket 지원 (기본: True)
                - custom_headers: 커스텀 HTTP 헤더
        
        Returns:
            Result[Tunnel, str]: 성공 시 Ok(tunnel), 실패 시 Err(message)
        """
    
    def expose_tcp(
        self,
        local_port: int,
        remote_port: Optional[int] = None
    ) -> Result[Tunnel, str]:
        """
TCP 포트 노출
        
        Args:
            local_port: 로컬 포트 번호
            remote_port: 원격 포트 번호 (None이면 자동 할당)
        
        Returns:
            Result[Tunnel, str]: 성공 시 Ok(tunnel), 실패 시 Err(message)
        """
    
    def list_tunnels(self) -> List[Tunnel]:
        """활성 터널 목록 조회"""
    
    def close_tunnel(self, tunnel_id: TunnelId) -> Result[None, str]:
        """특정 터널 종료"""
    
    def with_tunnel(
        self,
        local_port: int,
        path: str,
        **options
    ) -> ContextManager[Tunnel]:
        """
Context manager로 임시 터널 생성
        
        Example:
            >>> with client.with_tunnel(3000, "demo") as tunnel:
            ...     print(f"URL: {tunnel.url}")
            ...     # 터널 사용
            ... # 자동 정리
        """
```

## 터널 관리

### Tunnel 타입

```python
from dataclasses import dataclass, frozen
from datetime import datetime
from typing import Optional

@frozen
@dataclass
class Tunnel:
    """터널 기본 타입 (불변)"""
    id: TunnelId
    local_port: Port
    tunnel_type: str  # "tcp", "udp", "http"
    status: str = "pending"  # pending, connecting, connected, disconnected
    created_at: datetime = field(default_factory=datetime.now)
    connected_at: Optional[datetime] = None
    
    def with_status(self, status: str, **kwargs) -> 'Tunnel':
        """새로운 상태를 가진 터널 반환"""
        return dataclass.replace(self, status=status, **kwargs)

@frozen
@dataclass
class HTTPTunnel(Tunnel):
    """HTTP 터널 타입 (불변)"""
    tunnel_type: str = "http"
    path: Optional[Path] = None
    vhost: Optional[str] = None
    strip_path: bool = True
    websocket: bool = True
    
    @property
    def url(self) -> str:
        """완전한 접속 URL"""
        base_url = "https://example.com"  # 설정에서 가져옴
        if self.path:
            return f"{base_url}/{self.path.value}/"
        return base_url
```

### 터널 생성 함수

```python
def create_http_tunnel(
    local_port: int,
    path: str,
    strip_path: bool = True,
    websocket: bool = True,
    **options
) -> Result[HTTPTunnel, str]:
    """
HTTP 터널 생성 (순수 함수)
    
    Args:
        local_port: 로컬 포트 번호
        path: URL 경로
        strip_path: 프록시 시 경로 제거 여부
        websocket: WebSocket 지원 여부
        **options: 추가 옵션
    
    Returns:
        Result[HTTPTunnel, str]: 성공 시 Ok(tunnel), 실패 시 Err(message)
    
    Example:
        >>> result = create_http_tunnel(3000, "myapp")
        >>> match result:
        ...     case Ok(tunnel):
        ...         print(f"Tunnel created: {tunnel.id.value}")
        ...     case Err(error):
        ...         print(f"Failed: {error}")
    """

def create_tcp_tunnel(
    local_port: int,
    remote_port: Optional[int] = None
) -> Result[Tunnel, str]:
    """
TCP 터널 생성 (순수 함수)
    
    Args:
        local_port: 로컬 포트 번호
        remote_port: 원격 포트 번호 (None이면 자동 할당)
    
    Returns:
        Result[Tunnel, str]: 성공 시 Ok(tunnel), 실패 시 Err(message)
    """

def validate_tunnel(tunnel: Tunnel) -> Result[Tunnel, List[str]]:
    """터널 유효성 검증 (순수 함수)
    
    Args:
        tunnel: 검증할 터널
    
    Returns:
        Result[Tunnel, List[str]]: 성공 시 Ok(tunnel), 실패 시 Err(errors)
    """
```

## 파이프라인 및 조합자

### 파이프라인 함수

```python
from functools import reduce
from typing import Callable, TypeVar

T = TypeVar('T')
U = TypeVar('U')

def pipe(*functions: Callable) -> Callable:
    """함수들을 연결하는 파이프
    
    Args:
        *functions: 연결할 함수들
    
    Returns:
        합성된 함수
    
    Example:
        >>> add_one = lambda x: x + 1
        >>> double = lambda x: x * 2
        >>> pipeline = pipe(add_one, double, str)
        >>> pipeline(5)  # "12"
    """
    return reduce(lambda f, g: lambda x: g(f(x)), functions)

def compose(*functions: Callable) -> Callable:
    """함수들을 역순으로 합성
    
    pipe와 반대 순서로 함수를 합성합니다.
    
    Example:
        >>> pipeline = compose(str, double, add_one)
        >>> pipeline(5)  # "12"
    """
    return reduce(lambda f, g: lambda x: f(g(x)), functions)
```

### Result 조합자

```python
def map_result(
    f: Callable[[T], U]
) -> Callable[[Result[T, E]], Result[U, E]]:
    """
Result 타입에 대한 map 함수
    
    Example:
        >>> result = Ok(5)
        >>> double = lambda x: x * 2
        >>> map_result(double)(result)  # Ok(10)
    """

def flat_map_result(
    f: Callable[[T], Result[U, E]]
) -> Callable[[Result[T, E]], Result[U, E]]:
    """
Result 타입에 대한 flat_map 함수
    
    Example:
        >>> def safe_divide(x: int) -> Result[float, str]:
        ...     return Ok(x / 2) if x != 0 else Err("Division by zero")
        >>> 
        >>> result = Ok(10)
        >>> flat_map_result(safe_divide)(result)  # Ok(5.0)
    """

def sequence(results: List[Result[T, E]]) -> Result[List[T], E]:
    """
Result 리스트를 Result<List>로 변환
    
    모든 Result가 Ok일 때만 Ok를 반환합니다.
    
    Example:
        >>> results = [Ok(1), Ok(2), Ok(3)]
        >>> sequence(results)  # Ok([1, 2, 3])
        >>> 
        >>> results = [Ok(1), Err("error"), Ok(3)]
        >>> sequence(results)  # Err("error")
    """

def traverse(
    f: Callable[[T], Result[U, E]],
    items: List[T]
) -> Result[List[U], E]:
    """
리스트의 각 항목에 함수를 적용하고 결과를 수집
    
    Example:
        >>> def validate_port(port: int) -> Result[int, str]:
        ...     return Ok(port) if 1 <= port <= 65535 else Err(f"Invalid port: {port}")
        >>> 
        >>> traverse(validate_port, [80, 443, 8080])  # Ok([80, 443, 8080])
        >>> traverse(validate_port, [80, 0, 8080])    # Err("Invalid port: 0")
    """
```

### 편의 함수

```python
def quick_tunnel(
    server: str,
    local_port: int,
    path: str,
    **options
) -> Result[str, str]:
    """빠른 터널 생성 및 URL 반환
    
    클라이언트 생성부터 터널 URL 획득까지 한 번에 처리합니다.
    
    Args:
        server: FRP 서버 주소
        local_port: 로컬 포트 번호
        path: URL 경로
        **options: 추가 옵션
    
    Returns:
        Result[str, str]: 성공 시 Ok(url), 실패 시 Err(message)
    
    Example:
        >>> result = quick_tunnel("tunnel.example.com", 3000, "myapp")
        >>> match result:
        ...     case Ok(url):
        ...         print(f"Tunnel URL: {url}")
        ...     case Err(error):
        ...         print(f"Failed: {error}")
    """

def temporary_tunnel(
    server: str,
    local_port: int,
    path: str,
    **options
) -> ContextManager[Tunnel]:
    """임시 터널 context manager
    
    클라이언트 생성부터 터널 종료까지 자동 관리합니다.
    
    Example:
        >>> with temporary_tunnel("tunnel.example.com", 3000, "demo") as tunnel:
        ...     print(f"URL: {tunnel.url}")
        ...     # 터널 사용
        ... # 자동 정리
    """

def tunnel_pipeline(
    *operations: Callable[[Tunnel], Result[Tunnel, str]]
) -> Callable[[Tunnel], Result[Tunnel, str]]:
    """터널 작업 파이프라인 생성
    
    여러 터널 작업을 순차적으로 적용합니다.
    
    Example:
        >>> add_auth = lambda t: Ok(t.with_auth("token"))
        >>> add_headers = lambda t: Ok(t.with_headers({"X-Custom": "value"}))
        >>> pipeline = tunnel_pipeline(add_auth, add_headers)
        >>> 
        >>> tunnel = create_http_tunnel(3000, "api").unwrap()
        >>> result = pipeline(tunnel)
    """
```

## 이벤트 처리

### 이벤트 타입

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class DomainEvent:
    """도메인 이벤트 기본 타입"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)

@dataclass
class TunnelCreated(DomainEvent):
    """터널 생성 이벤트"""
    tunnel_id: TunnelId
    local_port: int
    path: Optional[str]

@dataclass
class TunnelConnected(DomainEvent):
    """터널 연결 이벤트"""
    tunnel_id: TunnelId

@dataclass
class TunnelDisconnected(DomainEvent):
    """터널 연결 해제 이벤트"""
    tunnel_id: TunnelId
    reason: Optional[str] = None
```

### 이벤트 처리 함수

```python
def process_events(
    events: List[DomainEvent],
    handlers: Dict[type, Callable[[DomainEvent], None]]
) -> None:
    """이벤트 리스트 처리 (순수 함수)
    
    Args:
        events: 처리할 이벤트 목록
        handlers: 이벤트 타입별 핸들러
    
    Example:
        >>> handlers = {
        ...     TunnelCreated: lambda e: print(f"Tunnel {e.tunnel_id} created"),
        ...     TunnelConnected: lambda e: print(f"Tunnel {e.tunnel_id} connected")
        ... }
        >>> process_events(events, handlers)
    """

def fold_events(
    events: List[DomainEvent],
    initial_state: T,
    reducer: Callable[[T, DomainEvent], T]
) -> T:
    """이벤트를 통해 상태 재구성 (순수 함수)
    
    Event Sourcing 패턴을 사용하여 상태를 재구성합니다.
    
    Args:
        events: 이벤트 목록
        initial_state: 초기 상태
        reducer: 상태 변환 함수
    
    Returns:
        최종 상태
    
    Example:
        >>> def tunnel_reducer(state: Dict, event: DomainEvent) -> Dict:
        ...     match event:
        ...         case TunnelCreated(tunnel_id=tid):
        ...             return {**state, tid.value: "created"}
        ...         case TunnelConnected(tunnel_id=tid):
        ...             return {**state, tid.value: "connected"}
        ...         case _:
        ...             return state
        >>> 
        >>> final_state = fold_events(events, {}, tunnel_reducer)
    """
```

## 유틸리티 함수

### 바이너리 관리

```python
def find_frpc_binary() -> Result[str, str]:
    """시스템에서 frpc 바이너리 찾기
    
    Returns:
        Result[str, str]: 성공 시 Ok(path), 실패 시 Err(message)
    """

def download_frp_binary(
    version: str = "latest",
    platform: Optional[str] = None,
    target_dir: str = "/usr/local/bin"
) -> Result[str, str]:
    """
FRP 바이너리 다운로드
    
    GitHub에서 FRP 바이너리를 다운로드합니다.
    
    Args:
        version: 버전 (예: "0.51.0" 또는 "latest")
        platform: 플랫폼 (자동 감지)
        target_dir: 설치 디렉토리
    
    Returns:
        Result[str, str]: 성공 시 Ok(binary_path), 실패 시 Err(message)
    """

def ensure_frp_installed(
    version: str = "latest",
    auto_download: bool = True
) -> Result[str, str]:
    """
FRP 바이너리 확인 및 설치
    
    바이너리가 없으면 자동으로 다운로드할 수 있습니다.
    
    Args:
        version: 원하는 버전
        auto_download: 자동 다운로드 여부
    
    Returns:
        Result[str, str]: 성공 시 Ok(binary_path), 실패 시 Err(message)
    """
```

### 설정 헬퍼

```python
def load_config_file(
    path: str
) -> Result[Dict[str, Any], str]:
    """설정 파일 로드
    
    YAML, JSON, TOML 형식을 지원합니다.
    
    Args:
        path: 설정 파일 경로
    
    Returns:
        Result[Dict[str, Any], str]: 성공 시 Ok(config), 실패 시 Err(message)
    """

def validate_config(
    config: Dict[str, Any]
) -> Result[Dict[str, Any], List[str]]:
    """설정 유효성 검증
    
    필수 필드와 타입을 검증합니다.
    
    Args:
        config: 검증할 설정
    
    Returns:
        Result[Dict[str, Any], List[str]]: 성공 시 Ok(config), 실패 시 Err(errors)
    """

def merge_configs(
    *configs: Dict[str, Any]
) -> Dict[str, Any]:
    """여러 설정 병합
    
    나중 설정이 이전 설정을 덮어씁니다.
    
    Args:
        *configs: 병합할 설정들
    
    Returns:
        병합된 설정
    """
```

## 예외 처리

### Result 타입 패턴 매칭

```python
def handle_tunnel_result(
    result: Result[Tunnel, str],
    on_success: Callable[[Tunnel], None],
    on_error: Callable[[str], None]
) -> None:
    """
Result 타입 패턴 매칭
    
    Python 3.10+ match 문 사용:
    
    Example:
        >>> result = create_http_tunnel(3000, "api")
        >>> match result:
        ...     case Ok(tunnel):
        ...         print(f"Success: {tunnel.url}")
        ...     case Err(error):
        ...         print(f"Failed: {error}")
    """
    match result:
        case Ok(value):
            on_success(value)
        case Err(error):
            on_error(error)

def try_with_fallback(
    primary: Callable[[], Result[T, E]],
    fallback: Callable[[], Result[T, E]]
) -> Result[T, E]:
    """실패 시 fallback 실행
    
    Args:
        primary: 첫 번째 시도
        fallback: 실패 시 대체 함수
    
    Returns:
        첫 번째 성공 시 그 결과, 아니면 fallback 결과
    
    Example:
        >>> result = try_with_fallback(
        ...     lambda: create_client("primary.example.com"),
        ...     lambda: create_client("backup.example.com")
        ... )
    """
    primary_result = primary()
    if primary_result.is_ok():
        return primary_result
    return fallback()

def collect_errors(
    results: List[Result[T, E]]
) -> Tuple[List[T], List[E]]:
    """
Result 리스트에서 성공과 실패 분리
    
    Args:
        results: Result 리스트
    
    Returns:
        (성공한 값들, 에러들)
    
    Example:
        >>> results = [
        ...     Ok(1), Err("error1"), Ok(2), Err("error2")
        ... ]
        >>> values, errors = collect_errors(results)
        >>> # values: [1, 2]
        >>> # errors: ["error1", "error2"]
    """
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

### 디버깅 헬퍼

```python
def debug_pipeline(
    *functions: Callable,
    trace: bool = True
) -> Callable:
    """파이프라인 디버깅 래퍼
    
    각 단계의 입력과 출력을 출력합니다.
    
    Args:
        *functions: 디버깅할 함수들
        trace: 추적 출력 여부
    
    Returns:
        디버깅이 추가된 파이프라인
    
    Example:
        >>> pipeline = debug_pipeline(
        ...     create_http_tunnel,
        ...     validate_tunnel,
        ...     trace=True
        ... )
    """

def measure_time(
    f: Callable[..., Result[T, E]]
) -> Callable[..., Result[Tuple[T, float], E]]:
    """함수 실행 시간 측정
    
    Result 타입을 반환하는 함수의 실행 시간을 측정합니다.
    
    Args:
        f: 측정할 함수
    
    Returns:
        (result, elapsed_time) 형태로 반환하는 함수
    """

def retry_with_backoff(
    f: Callable[..., Result[T, E]],
    max_attempts: int = 3,
    base_delay: float = 1.0
) -> Callable[..., Result[T, E]]:
    """지수 백오프로 재시도
    
    실패 시 지수적으로 대기 시간을 늘려가며 재시도합니다.
    
    Args:
        f: 재시도할 함수
        max_attempts: 최대 시도 횟수
        base_delay: 기본 대기 시간(초)
    
    Returns:
        재시도 로직이 추가된 함수
    """
```

## 버전 관리

```python
__version__ = "1.0.0"
__all__ = [
    # 타입
    "Result", "Ok", "Err",
    "TunnelId", "Port", "Path",
    "Tunnel", "HTTPTunnel",
    "DomainEvent", "TunnelCreated", "TunnelConnected",
    
    # 함수
    "create_client",
    "create_http_tunnel",
    "create_tcp_tunnel",
    "validate_tunnel",
    "quick_tunnel",
    "temporary_tunnel",
    
    # 파이프라인
    "pipe", "compose",
    "map_result", "flat_map_result",
    "sequence", "traverse",
    
    # 유틸리티
    "find_frpc_binary",
    "download_frp_binary",
    "ensure_frp_installed",
]
```