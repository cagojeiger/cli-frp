# Checkpoint 2: 기본 클라이언트 API (함수형 접근)

## 개요
사용자가 FRP를 쉽게 사용할 수 있도록 함수형 프로그래밍 패러다임을 따르는 고수준 클라이언트 API를 구현합니다. 불변 상태와 순수 함수를 사용하여 FRP 프로세스를 관리합니다.

## 설계 원칙
- **불변 클라이언트 상태**: 모든 클라이언트 상태는 불변 객체로 관리
- **순수 함수**: 연결 로직은 부수 효과 없는 순수 함수로 구현
- **명시적 효과**: I/O 작업은 Effect 타입으로 격리
- **함수 조합**: 작은 함수들을 파이프라인으로 조합

## 목표
- 함수형 클라이언트 API 구현
- Result 타입 기반 에러 처리
- 서버 연결 설정 및 검증
- 기본 인증 처리
- 프로세스 생명주기 통합 관리

## 구현 범위

### 1. 도메인 모델 (불변 데이터)
```python
# src/domain/client.py
from dataclasses import dataclass, frozen
from typing import Optional
from datetime import datetime
from src.domain.types import Result, Ok, Err

@frozen
@dataclass
class ClientId:
    value: str

@frozen
@dataclass
class ServerAddress:
    host: str
    port: int = 7000
    
    def __post_init__(self):
        if not self.host:
            raise ValueError("Server host cannot be empty")
        if not 1 <= self.port <= 65535:
            raise ValueError(f"Invalid port: {self.port}")

@frozen
@dataclass
class AuthToken:
    value: str
    
    def masked(self) -> str:
        """토큰을 마스킹하여 반환"""
        if len(self.value) <= 8:
            return "***"
        return f"{self.value[:4]}...{self.value[-4:]}"

@frozen
@dataclass
class ConnectionState:
    """연결 상태 (불변)"""
    status: str = "disconnected"  # disconnected, connecting, connected, error
    server: Optional[ServerAddress] = None
    connected_at: Optional[datetime] = None
    last_error: Optional[str] = None
    
    def with_status(self, status: str, **kwargs) -> 'ConnectionState':
        """새로운 상태를 가진 ConnectionState 반환"""
        return dataclasses.replace(self, status=status, **kwargs)

@frozen
@dataclass
class Client:
    """FRP 클라이언트 (불변)"""
    id: ClientId
    server: ServerAddress
    auth_token: Optional[AuthToken] = None
    connection_state: ConnectionState = field(default_factory=ConnectionState)
    process_id: Optional[ProcessId] = None
    config_path: Optional[str] = None
    
    def with_connection(self, state: ConnectionState, **kwargs) -> 'Client':
        """새로운 연결 상태를 가진 클라이언트 반환"""
        return dataclasses.replace(self, connection_state=state, **kwargs)
```

### 2. 순수 함수 (클라이언트 연산)
```python
# src/core/client_operations.py
from typing import Tuple, Optional
from src.domain.client import Client, ClientId, ServerAddress, AuthToken, ConnectionState
from src.domain.process import Process
from src.domain.events import ClientCreated, ClientConnected, ClientDisconnected
from src.domain.types import Result, Ok, Err
import uuid

def create_client(
    server: str,
    port: int = 7000,
    auth_token: Optional[str] = None
) -> Result[Client, str]:
    """클라이언트 생성 - 순수 함수"""
    try:
        client = Client(
            id=ClientId(str(uuid.uuid4())),
            server=ServerAddress(server, port),
            auth_token=AuthToken(auth_token) if auth_token else None
        )
        return Ok(client)
    except ValueError as e:
        return Err(str(e))

def connect_client(
    client: Client,
    process_id: ProcessId,
    config_path: str
) -> Tuple[Client, ClientConnected]:
    """클라이언트 연결 - 새 상태와 이벤트 반환"""
    if client.connection_state.status != "disconnected":
        raise InvalidStateError(f"Cannot connect in {client.connection_state.status} state")
    
    new_state = ConnectionState(
        status="connected",
        server=client.server,
        connected_at=datetime.now()
    )
    
    new_client = client.with_connection(
        new_state,
        process_id=process_id,
        config_path=config_path
    )
    
    event = ClientConnected(
        client_id=client.id,
        server=client.server,
        occurred_at=datetime.now()
    )
    
    return new_client, event

def disconnect_client(
    client: Client,
    reason: Optional[str] = None
) -> Tuple[Client, ClientDisconnected]:
    """클라이언트 연결 해제 - 새 상태와 이벤트 반환"""
    if client.connection_state.status != "connected":
        raise InvalidStateError(f"Cannot disconnect in {client.connection_state.status} state")
    
    new_state = ConnectionState(
        status="disconnected",
        last_error=reason
    )
    
    new_client = client.with_connection(
        new_state,
        process_id=None,
        config_path=None
    )
    
    event = ClientDisconnected(
        client_id=client.id,
        reason=reason,
        occurred_at=datetime.now()
    )
    
    return new_client, event

def build_client_config(client: Client) -> Dict[str, Any]:
    """클라이언트 설정 생성 - 순수 함수"""
    config = {
        'common': {
            'server_addr': client.server.host,
            'server_port': client.server.port
        }
    }
    
    if client.auth_token:
        config['common']['token'] = client.auth_token.value
    
    return config
```

### 3. 바이너리 탐색 (순수 함수)
```python
# src/core/binary_finder.py
from typing import List, Optional
from src.domain.types import Result, Ok, Err
import os

def get_search_paths() -> List[str]:
    """바이너리 검색 경로 목록 - 순수 함수"""
    paths = []
    
    # PATH 환경변수
    if 'PATH' in os.environ:
        paths.extend(os.environ['PATH'].split(os.pathsep))
    
    # 일반적인 설치 위치
    common_paths = [
        '/usr/local/bin',
        '/usr/bin',
        '/opt/frp',
        '~/.local/bin',
        './bin'
    ]
    
    paths.extend(common_paths)
    return list(dict.fromkeys(paths))  # 중복 제거

def check_binary_exists(path: str) -> bool:
    """바이너리 존재 확인 - 순수 함수 (경로 문자열 조작)"""
    # 실제 파일 시스템 체크는 Effect로 분리
    return path.endswith('frpc') or path.endswith('frpc.exe')

def validate_binary_version(binary_path: str, min_version: str = "0.40.0") -> Result[str, str]:
    """바이너리 버전 검증 - 순수 함수"""
    # 버전 파싱 및 비교 로직 (실제 실행은 Effect)
    return Ok(binary_path)
```

### 4. 이펙트 인터페이스
```python
# src/effects/protocols.py
from typing import Protocol, Optional, List
from src.domain.types import Result

class BinarySearcher(Protocol):
    """바이너리 검색 인터페이스"""
    
    def file_exists(self, path: str) -> bool:
        """파일 존재 확인"""
        ...
    
    def is_executable(self, path: str) -> bool:
        """실행 가능 확인"""
        ...
    
    def get_version(self, binary_path: str) -> Result[str, str]:
        """바이너리 버전 확인"""
        ...

class ConnectionValidator(Protocol):
    """연결 검증 인터페이스"""
    
    def test_connection(self, host: str, port: int) -> Result[None, str]:
        """서버 연결 테스트"""
        ...
    
    def validate_auth(self, host: str, port: int, token: str) -> Result[None, str]:
        """인증 검증"""
        ...
```

### 5. 애플리케이션 서비스
```python
# src/application/client_service.py
from typing import Optional, Dict, Any
from src.domain.client import Client
from src.domain.process import Process
from src.domain.types import Result, Ok, Err
from src.core import client_operations, process_operations, config_builder
from src.effects.protocols import ProcessExecutor, FileWriter, BinarySearcher, EventStore
from src.application.pipelines import pipe, flat_map_result, map_result

class ClientService:
    """클라이언트 관리 서비스 - 순수 함수들을 조합"""
    
    def __init__(
        self,
        binary_searcher: BinarySearcher,
        process_executor: ProcessExecutor,
        file_writer: FileWriter,
        event_store: EventStore
    ):
        self._binary_searcher = binary_searcher
        self._process_executor = process_executor
        self._file_writer = file_writer
        self._event_store = event_store
        self._clients: Dict[str, Client] = {}
        self._processes: Dict[str, Process] = {}
    
    def create_and_connect(
        self,
        server: str,
        port: int = 7000,
        auth_token: Optional[str] = None,
        binary_path: Optional[str] = None
    ) -> Result[Client, str]:
        """클라이언트 생성 및 연결 파이프라인"""
        
        # 1. 바이너리 찾기 또는 검증
        binary_result = self._resolve_binary(binary_path)
        if binary_result.is_err():
            return binary_result
        
        resolved_binary = binary_result.unwrap()
        
        # 2. 클라이언트 생성 및 연결 파이프라인
        return pipe(
            lambda _: client_operations.create_client(server, port, auth_token),
            flat_map_result(lambda c: self._create_process_and_config(c, resolved_binary)),
            flat_map_result(lambda data: self._start_and_connect(data)),
            map_result(lambda data: self._finalize_connection(data))
        )(None)
    
    def _resolve_binary(self, binary_path: Optional[str]) -> Result[str, str]:
        """바이너리 경로 확인 - Effect 사용"""
        if binary_path:
            if self._binary_searcher.file_exists(binary_path):
                return Ok(binary_path)
            return Err(f"Binary not found: {binary_path}")
        
        # 자동 탐색
        search_paths = get_search_paths()
        for base_path in search_paths:
            frpc_path = os.path.join(base_path, "frpc")
            if self._binary_searcher.file_exists(frpc_path):
                if self._binary_searcher.is_executable(frpc_path):
                    return Ok(frpc_path)
        
        return Err("frpc binary not found in PATH")
    
    def _create_process_and_config(
        self,
        client: Client,
        binary_path: str
    ) -> Result[Dict[str, Any], str]:
        """프로세스와 설정 생성"""
        # 설정 생성 (순수)
        config = build_client_config(client)
        config_content = config_builder.build_ini_content(config)
        
        # 설정 파일 작성 (Effect)
        config_result = self._file_writer.write_temp(config_content)
        if config_result.is_err():
            return Err(f"Failed to write config: {config_result.error}")
        
        config_path = config_result.unwrap()
        
        # 프로세스 생성 (순수)
        process_result = process_operations.create_process(binary_path, config_path)
        if process_result.is_err():
            return process_result
        
        process = process_result.unwrap()
        
        return Ok({
            'client': client,
            'process': process,
            'config_path': config_path
        })
    
    def _start_and_connect(self, data: Dict[str, Any]) -> Result[Dict[str, Any], str]:
        """프로세스 시작 및 연결"""
        client = data['client']
        process = data['process']
        config_path = data['config_path']
        
        # 프로세스 시작 (Effect)
        command = [process.binary_path.value, '-c', config_path]
        spawn_result = self._process_executor.spawn(command)
        
        if spawn_result.is_err():
            return Err(f"Failed to start process: {spawn_result.error}")
        
        pid = spawn_result.unwrap()
        
        # 프로세스 상태 업데이트 (순수)
        new_process, process_event = process_operations.start_process(process, pid)
        
        # 클라이언트 연결 (순수)
        connected_client, client_event = client_operations.connect_client(
            client, process.id, config_path
        )
        
        # 이벤트 저장
        self._event_store.append(process_event)
        self._event_store.append(client_event)
        
        return Ok({
            'client': connected_client,
            'process': new_process
        })
    
    def _finalize_connection(self, data: Dict[str, Any]) -> Client:
        """연결 완료 처리"""
        client = data['client']
        process = data['process']
        
        # 상태 저장
        self._clients[client.id.value] = client
        self._processes[process.id.value] = process
        
        return client
```

### 6. 공개 API
```python
# src/api/client.py
from typing import Optional
from src.domain.types import Result
from src.application.container import Container

def create_client(
    server: str,
    port: int = 7000,
    auth_token: Optional[str] = None,
    binary_path: Optional[str] = None,
    **options
) -> Result[Client, str]:
    """
    FRP 클라이언트 생성 및 연결
    
    Args:
        server: FRP 서버 주소
        port: FRP 서버 포트 (기본: 7000)
        auth_token: 인증 토큰 (선택)
        binary_path: frpc 바이너리 경로 (선택, 자동 탐색)
        **options: 추가 옵션
    
    Returns:
        Result[Client, str]: 성공 시 Ok(client), 실패 시 Err(message)
    
    Example:
        >>> result = create_client("tunnel.example.com", auth_token="secret")
        >>> match result:
        ...     case Ok(client):
        ...         print(f"Connected to {client.server.host}")
        ...     case Err(error):
        ...         print(f"Connection failed: {error}")
    """
    container = Container()
    client_service = container.resolve(ClientService)
    
    return client_service.create_and_connect(
        server, port, auth_token, binary_path, **options
    )

def disconnect_client(client: Client) -> Result[Client, str]:
    """
    클라이언트 연결 해제
    
    Args:
        client: 연결을 해제할 클라이언트
    
    Returns:
        Result[Client, str]: 성공 시 Ok(disconnected_client), 실패 시 Err(message)
    """
    container = Container()
    client_service = container.resolve(ClientService)
    
    return client_service.disconnect(client)
```

## 테스트 시나리오

### 순수 함수 테스트

1. **클라이언트 생성 테스트**
   ```python
   def test_create_client():
       result = create_client("example.com", 7000, "secret123")
       
       assert result.is_ok()
       client = result.unwrap()
       assert client.server.host == "example.com"
       assert client.server.port == 7000
       assert client.auth_token.value == "secret123"
       assert client.connection_state.status == "disconnected"
   ```

2. **연결 상태 전환 테스트**
   ```python
   def test_client_state_transitions():
       # 클라이언트 생성
       client = create_client("example.com").unwrap()
       process_id = ProcessId("test-process")
       
       # 연결 테스트
       connected_client, event = connect_client(client, process_id, "/tmp/config.ini")
       assert connected_client.connection_state.status == "connected"
       assert connected_client.process_id == process_id
       assert isinstance(event, ClientConnected)
       
       # 연결 해제 테스트
       disconnected_client, event = disconnect_client(connected_client, "test complete")
       assert disconnected_client.connection_state.status == "disconnected"
       assert disconnected_client.process_id is None
       assert isinstance(event, ClientDisconnected)
   ```

3. **설정 생성 테스트**
   ```python
   def test_build_client_config():
       client = create_client("example.com", 7000, "secret").unwrap()
       config = build_client_config(client)
       
       assert config['common']['server_addr'] == "example.com"
       assert config['common']['server_port'] == 7000
       assert config['common']['token'] == "secret"
   ```

### 속성 기반 테스트

```python
from hypothesis import given, strategies as st

@given(
    server=st.text(min_size=1, max_size=255),
    port=st.integers(min_value=1, max_value=65535),
    token=st.text(min_size=0, max_size=100)
)
def test_client_creation_properties(server, port, token):
    """유효한 입력에 대한 클라이언트 생성"""
    result = create_client(server, port, token if token else None)
    
    # 유효한 서버 주소인 경우
    if server and not server.isspace():
        assert result.is_ok()
        client = result.unwrap()
        assert client.server.host == server
        assert client.server.port == port
        if token:
            assert client.auth_token.value == token
    else:
        assert result.is_err()
```

### 이펙트 모킹 테스트

```python
from unittest.mock import Mock
from src.domain.types import Ok, Err

def test_client_service_with_mocks():
    # Mock 생성
    binary_searcher = Mock(spec=BinarySearcher)
    binary_searcher.file_exists.return_value = True
    binary_searcher.is_executable.return_value = True
    
    process_executor = Mock(spec=ProcessExecutor)
    process_executor.spawn.return_value = Ok(12345)
    
    file_writer = Mock(spec=FileWriter)
    file_writer.write_temp.return_value = Ok("/tmp/test.ini")
    
    event_store = Mock(spec=EventStore)
    
    # 서비스 테스트
    service = ClientService(
        binary_searcher=binary_searcher,
        process_executor=process_executor,
        file_writer=file_writer,
        event_store=event_store
    )
    
    result = service.create_and_connect("example.com", 7000, "secret")
    
    assert result.is_ok()
    client = result.unwrap()
    assert client.connection_state.status == "connected"
    assert binary_searcher.file_exists.called
    assert process_executor.spawn.called
    assert file_writer.write_temp.called
```

### 통합 테스트

1. **실제 서버 연결**
   - Docker 컨테이너에서 FRP 서버 실행
   - 실제 frpc 바이너리로 연결 테스트
   - 연결 상태 확인

2. **재연결 시나리오**
   - 연결 후 프로세스 종료
   - 재연결 시도
   - 상태 복원 확인

## 파일 구조
```
src/
├── domain/
│   ├── __init__.py
│   ├── client.py           # Client, ConnectionState, ServerAddress
│   └── events.py           # ClientCreated, ClientConnected
├── core/
│   ├── __init__.py
│   ├── client_operations.py  # 클라이언트 관련 순수 함수
│   └── binary_finder.py       # 바이너리 탐색 순수 함수
├── effects/
│   ├── __init__.py
│   ├── protocols.py        # BinarySearcher, ConnectionValidator
│   └── binary_effects.py   # FilesystemSearcher 구현
├── application/
│   ├── __init__.py
│   └── client_service.py   # ClientService (조합)
└── api/
    ├── __init__.py
    └── client.py           # 공개 API

tests/
├── __init__.py
├── test_domain/
│   └── test_client.py      # 도메인 모델 테스트
├── test_core/
│   ├── test_client_operations.py  # 순수 함수 테스트
│   └── test_binary_finder.py      # 바이너리 탐색 테스트
└── test_application/
    └── test_client_service.py      # 서비스 테스트
```

## 완료 기준

### 필수 기능
- [x] 클라이언트 도메인 모델 정의
- [x] 클라이언트 연결 순수 함수
- [x] 바이너리 탐색 순수 함수
- [x] 이펙트 인터페이스 정의
- [x] Result 타입 기반 에러 처리

### 테스트
- [x] 순수 함수 단위 테스트
- [x] 속성 기반 테스트
- [x] 이펙트 모킹 테스트
- [x] 상태 전환 검증

### 문서
- [x] 모든 함수에 타입 힌트와 docstring
- [x] 함수형 사용 예제
- [x] 도메인 모델 설명

## 예상 작업 시간
- 도메인 모델 설계: 3시간
- 순수 함수 구현: 4시간
- 이펙트 인터페이스 및 구현: 3시간
- 서비스 계층 구현: 4시간
- 테스트 작성: 4시간
- 문서화: 2시간

**총 예상 시간**: 20시간 (4일)

## 다음 단계 준비
- Tunnel 도메인 모델 설계
- 터널 생성 순수 함수 구현
- 동적 설정 업데이트 방안

## 참고 사항
- 클라이언트 상태는 완전히 불변
- 모든 상태 변경은 새 인스턴스 생성
- 이펙트는 최소화하고 명시적으로 관리
- Result 타입으로 모든 실패 가능성 표현
- 함수 조합으로 복잡한 로직 구성