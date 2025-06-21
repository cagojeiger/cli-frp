# 파이프라인 패턴 가이드

파이프라인 패턴은 함수형 프로그래밍에서 여러 작업을 연결하여 복잡한 로직을 구성하는 강력한 방법입니다.

## 기본 개념

### 함수 조합 (Function Composition)

```python
from functools import reduce
from typing import Callable, TypeVar

T = TypeVar('T')
U = TypeVar('U')
V = TypeVar('V')

def compose(f: Callable[[U], V], g: Callable[[T], U]) -> Callable[[T], V]:
    """두 함수를 합성 (g 다음 f 실행)"""
    return lambda x: f(g(x))

def pipe(*functions: Callable) -> Callable:
    """함수들을 연결하는 파이프 (왼쪽에서 오른쪽으로)"""
    return reduce(lambda f, g: lambda x: g(f(x)), functions)
```

### 사용 예제

```python
# 기본 파이프라인
add_one = lambda x: x + 1
double = lambda x: x * 2
to_string = lambda x: str(x)

pipeline = pipe(add_one, double, to_string)
result = pipeline(5)  # "12"
```

## Result 타입과 파이프라인

### Result 조합자

```python
def map_result(f: Callable[[T], U]) -> Callable[[Result[T, E]], Result[U, E]]:
    """Result 타입에 대한 map 함수"""
    def wrapper(result: Result[T, E]) -> Result[U, E]:
        match result:
            case Ok(value):
                return Ok(f(value))
            case Err(error):
                return Err(error)
    return wrapper

def flat_map_result(f: Callable[[T], Result[U, E]]) -> Callable[[Result[T, E]], Result[U, E]]:
    """Result 타입에 대한 flat_map 함수"""
    def wrapper(result: Result[T, E]) -> Result[U, E]:
        match result:
            case Ok(value):
                return f(value)
            case Err(error):
                return Err(error)
    return wrapper
```

### Result 파이프라인 예제

```python
# 터널 생성 파이프라인
def create_tunnel_pipeline(server: str, port: int, path: str) -> Result[str, str]:
    return pipe(
        lambda _: create_client(server),
        flat_map_result(lambda c: c.expose_path(port, path)),
        map_result(lambda t: t.url)
    )(None)

# 사용
result = create_tunnel_pipeline("tunnel.example.com", 3000, "myapp")

match result:
    case Ok(url):
        print(f"터널 URL: {url}")
    case Err(error):
        print(f"에러: {error}")
```

## 실제 사용 패턴

### 1. 검증 파이프라인

```python
def validate_port(port: int) -> Result[int, str]:
    if 1 <= port <= 65535:
        return Ok(port)
    return Err(f"Invalid port: {port}")

def validate_path(path: str) -> Result[str, str]:
    if not path.startswith('/'):
        return Ok(path)
    return Err("Path must not start with /")

def validate_tunnel_params(port: int, path: str) -> Result[Tuple[int, str], str]:
    return pipe(
        lambda _: validate_port(port),
        flat_map_result(lambda p: validate_path(path).map(lambda pa: (p, pa)))
    )(None)
```

### 2. 변환 파이프라인

```python
def parse_config(content: str) -> Result[Dict, str]:
    """설정 파일 파싱"""
    try:
        return Ok(json.loads(content))
    except json.JSONDecodeError as e:
        return Err(f"Invalid JSON: {e}")

def validate_config(config: Dict) -> Result[Dict, str]:
    """설정 유효성 검증"""
    required_fields = ['server', 'port']
    missing = [f for f in required_fields if f not in config]
    
    if missing:
        return Err(f"Missing fields: {missing}")
    return Ok(config)

def normalize_config(config: Dict) -> Dict:
    """설정 정규화"""
    return {
        **config,
        'port': int(config.get('port', 7000)),
        'auth_token': config.get('auth_token', None)
    }

# 파이프라인 조합
config_pipeline = pipe(
    parse_config,
    flat_map_result(validate_config),
    map_result(normalize_config)
)
```

### 3. 비동기 작업 파이프라인

```python
def fetch_server_info(client: Client) -> Result[Dict, str]:
    """서버 정보 가져오기"""
    # 실제로는 비동기 작업
    return Ok({"version": "0.51.0", "status": "running"})

def check_compatibility(info: Dict) -> Result[Dict, str]:
    """호환성 확인"""
    if info.get("version", "").startswith("0.5"):
        return Ok(info)
    return Err(f"Incompatible version: {info.get('version')}")

def extract_features(info: Dict) -> List[str]:
    """지원 기능 추출"""
    return info.get("features", ["tcp", "http"])

# 서버 체크 파이프라인
server_check_pipeline = pipe(
    fetch_server_info,
    flat_map_result(check_compatibility),
    map_result(extract_features)
)
```

## 고급 패턴

### 1. 조건부 파이프라인

```python
def when(
    condition: Callable[[T], bool],
    true_path: Callable[[T], Result[U, E]],
    false_path: Callable[[T], Result[U, E]]
) -> Callable[[T], Result[U, E]]:
    """조건에 따른 분기"""
    def wrapper(value: T) -> Result[U, E]:
        if condition(value):
            return true_path(value)
        return false_path(value)
    return wrapper

# 사용 예
port_pipeline = when(
    lambda p: p < 1024,
    lambda p: Err(f"Privileged port: {p}"),
    lambda p: Ok(p)
)
```

### 2. 재시도 파이프라인

```python
def retry(
    f: Callable[[], Result[T, E]],
    max_attempts: int = 3,
    delay: float = 1.0
) -> Result[T, E]:
    """실패 시 재시도"""
    for attempt in range(max_attempts):
        result = f()
        if result.is_ok():
            return result
        
        if attempt < max_attempts - 1:
            time.sleep(delay * (2 ** attempt))  # 지수 백오프
    
    return result

# 사용 예
def connect_with_retry(server: str) -> Result[Client, str]:
    return retry(lambda: create_client(server))
```

### 3. 병렬 파이프라인

```python
def parallel_map(
    f: Callable[[T], Result[U, E]],
    items: List[T]
) -> Result[List[U], E]:
    """병렬로 함수 적용"""
    from concurrent.futures import ThreadPoolExecutor
    
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(f, item) for item in items]
        results = [future.result() for future in futures]
    
    return sequence(results)

# 사용 예
ports = [3000, 3001, 3002]
tunnels_result = parallel_map(
    lambda p: client.expose_tcp(p),
    ports
)
```

## 파이프라인 빌더

### 플루언트 인터페이스

```python
class Pipeline(Generic[T, E]):
    """파이프라인 빌더"""
    
    def __init__(self, value: Result[T, E]):
        self._value = value
    
    def map(self, f: Callable[[T], U]) -> 'Pipeline[U, E]':
        return Pipeline(self._value.map(f))
    
    def flat_map(self, f: Callable[[T], Result[U, E]]) -> 'Pipeline[U, E]':
        return Pipeline(self._value.flat_map(f))
    
    def filter(self, predicate: Callable[[T], bool]) -> 'Pipeline[T, E]':
        def filter_fn(value: T) -> Result[T, E]:
            if predicate(value):
                return Ok(value)
            return Err("Filter failed")
        
        return self.flat_map(filter_fn)
    
    def recover(self, f: Callable[[E], T]) -> 'Pipeline[T, E]':
        match self._value:
            case Ok(value):
                return self
            case Err(error):
                return Pipeline(Ok(f(error)))
    
    def run(self) -> Result[T, E]:
        return self._value

# 사용 예
result = (Pipeline(create_client("tunnel.example.com"))
    .flat_map(lambda c: c.expose_path(3000, "app"))
    .map(lambda t: t.url)
    .recover(lambda _: "http://localhost:3000")
    .run())
```

## 실전 예제

### 터널 생성 완전한 파이프라인

```python
def create_tunnel_with_validation(
    server: str,
    port: int,
    path: str,
    auth_token: Optional[str] = None
) -> Result[Tunnel, str]:
    """검증, 연결, 터널 생성을 포함한 완전한 파이프라인"""
    
    # 단계별 함수 정의
    def validate_inputs() -> Result[Tuple[int, str], str]:
        return validate_tunnel_params(port, path)
    
    def create_client_with_auth(_) -> Result[Client, str]:
        return create_client(server, auth_token=auth_token)
    
    def create_tunnel_on_client(client: Client) -> Result[Tunnel, str]:
        return client.expose_path(port, path)
    
    def log_success(tunnel: Tunnel) -> Tunnel:
        print(f"Tunnel created: {tunnel.url}")
        return tunnel
    
    def log_error(error: str) -> str:
        print(f"Failed to create tunnel: {error}")
        return error
    
    # 파이프라인 실행
    return pipe(
        validate_inputs,
        flat_map_result(create_client_with_auth),
        flat_map_result(create_tunnel_on_client),
        map_result(log_success)
    )(None).map_error(log_error)
```

### 다중 터널 관리 파이프라인

```python
def setup_development_environment(
    server: str,
    services: List[Tuple[int, str]]  # [(port, path), ...]
) -> Result[Dict[str, str], str]:
    """개발 환경을 위한 여러 터널 설정"""
    
    def create_client_step(_) -> Result[Client, str]:
        return create_client(server)
    
    def create_tunnels(client: Client) -> Result[List[Tunnel], str]:
        tunnel_results = [
            client.expose_path(port, path)
            for port, path in services
        ]
        return sequence(tunnel_results)
    
    def create_url_map(tunnels: List[Tunnel]) -> Dict[str, str]:
        return {
            tunnel.path: tunnel.url
            for tunnel in tunnels
            if hasattr(tunnel, 'path') and hasattr(tunnel, 'url')
        }
    
    return pipe(
        create_client_step,
        flat_map_result(create_tunnels),
        map_result(create_url_map)
    )(None)

# 사용
services = [
    (3000, "frontend"),
    (8000, "api"),
    (3001, "admin")
]

result = setup_development_environment("tunnel.example.com", services)

match result:
    case Ok(urls):
        for path, url in urls.items():
            print(f"{path}: {url}")
    case Err(error):
        print(f"Setup failed: {error}")
```

## 베스트 프랙티스

### 1. 명확한 단계 분리
각 파이프라인 단계는 하나의 책임만 가져야 합니다.

### 2. 에러 처리 일관성
모든 단계에서 Result 타입을 사용하여 에러를 전파합니다.

### 3. 테스트 용이성
각 단계를 독립적으로 테스트할 수 있도록 설계합니다.

### 4. 재사용성
공통 패턴을 함수로 추출하여 재사용합니다.

```python
# 재사용 가능한 유틸리티
def log_step(prefix: str) -> Callable[[T], T]:
    """로깅 단계 추가"""
    def logger(value: T) -> T:
        print(f"{prefix}: {value}")
        return value
    return logger

def time_step(f: Callable[[T], Result[U, E]]) -> Callable[[T], Result[U, E]]:
    """실행 시간 측정"""
    def timed(value: T) -> Result[U, E]:
        start = time.time()
        result = f(value)
        elapsed = time.time() - start
        print(f"Step took {elapsed:.2f}s")
        return result
    return timed
```

## 참고 자료

- [Railway Oriented Programming](https://fsharpforfunandprofit.com/rop/)
- [Functional Pipeline in Python](https://github.com/kachayev/fn.py)
- [Pipe Pattern](https://github.com/JulienPalard/Pipe)