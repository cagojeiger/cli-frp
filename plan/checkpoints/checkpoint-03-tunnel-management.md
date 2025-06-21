# Checkpoint 3: 터널 생성/삭제 (함수형 접근)

## 개요
FRP 터널을 불변 데이터 구조로 추상화하고 순수 함수를 사용하여 생명주기를 관리하는 기능을 구현합니다. TCP 터널부터 시작하여 함수형 터널 관리 시스템을 구축합니다.

## 설계 원칙
- **불변 터널 상태**: 모든 터널 상태는 불변 객체로 관리
- **순수 함수**: 터널 생성/변환 로직은 부수 효과 없는 순수 함수
- **이벤트 소싱**: 터널 상태 변경을 이벤트로 추적
- **파이프라인 패턴**: 터널 작업을 함수 조합으로 구성

## 목표
- 불변 Tunnel 타입을 통한 터널 추상화
- Result 타입 기반 에러 처리
- TCP 터널 생성 및 삭제 기능
- 터널 상태 추적 및 정보 조회
- 다중 터널 관리

## 구현 범위

### 1. 도메인 모델 (불변 데이터)
```python
# src/domain/tunnel.py
from dataclasses import dataclass, frozen, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.domain.types import Result, Ok, Err

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
class TunnelConfig:
    """터널 설정 정보 (불변)"""
    local_port: Port
    tunnel_type: str  # 'tcp', 'http', 'udp'
    remote_port: Optional[Port] = None
    custom_domains: List[str] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)

@frozen
@dataclass
class Tunnel:
    """개별 터널을 나타내는 불변 타입"""
    id: TunnelId
    config: TunnelConfig
    client_id: ClientId
    status: str = "pending"  # pending, connecting, connected, disconnected, error, closed
    created_at: datetime = field(default_factory=datetime.now)
    connected_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def with_status(self, status: str, **kwargs) -> 'Tunnel':
        """새로운 상태를 가진 터널 반환"""
        return dataclasses.replace(self, status=status, **kwargs)

@frozen
@dataclass
class TCPTunnel(Tunnel):
    """TCP 터널 타입"""
    
    @property
    def endpoint(self) -> Optional[str]:
        """터널 엔드포인트 (host:port)"""
        if self.config.remote_port and self.status == "connected":
            return f"{self.server_host}:{self.config.remote_port.value}"
        return None

@frozen
@dataclass
class HTTPTunnel(Tunnel):
    """HTTP 터널 타입"""
    path: Optional[str] = None
    vhost: Optional[str] = None
    
    @property
    def url(self) -> Optional[str]:
        """터널 접속 URL"""
        if self.status == "connected" and self.path:
            return f"https://{self.server_host}/{self.path}/"
        return None
```

### 2. 순수 함수 (터널 연산)
```python
# src/core/tunnel_operations.py
from typing import Tuple, List, Optional
from src.domain.tunnel import Tunnel, TCPTunnel, TunnelId, Port, TunnelConfig
from src.domain.events import TunnelCreated, TunnelConnected, TunnelClosed
from src.domain.types import Result, Ok, Err
import uuid

def create_tcp_tunnel(
    client_id: ClientId,
    local_port: int,
    remote_port: Optional[int] = None
) -> Result[TCPTunnel, str]:
    """TCP 터널 생성 - 순수 함수"""
    try:
        config = TunnelConfig(
            local_port=Port(local_port),
            tunnel_type="tcp",
            remote_port=Port(remote_port) if remote_port else None
        )
        
        tunnel = TCPTunnel(
            id=TunnelId(str(uuid.uuid4())),
            config=config,
            client_id=client_id
        )
        
        return Ok(tunnel)
    except ValueError as e:
        return Err(str(e))

def connect_tunnel(
    tunnel: Tunnel,
    allocated_port: Optional[int] = None
) -> Tuple[Tunnel, TunnelConnected]:
    """터널 연결 - 새 상태와 이벤트 반환"""
    if tunnel.status != "pending":
        raise InvalidStateError(f"Cannot connect tunnel in {tunnel.status} state")
    
    # TCP 터널이고 원격 포트가 없으면 할당된 포트 사용
    if isinstance(tunnel, TCPTunnel) and not tunnel.config.remote_port and allocated_port:
        new_config = dataclasses.replace(
            tunnel.config,
            remote_port=Port(allocated_port)
        )
        connected_tunnel = dataclasses.replace(
            tunnel,
            config=new_config,
            status="connected",
            connected_at=datetime.now()
        )
    else:
        connected_tunnel = tunnel.with_status(
            "connected",
            connected_at=datetime.now()
        )
    
    event = TunnelConnected(
        tunnel_id=tunnel.id,
        occurred_at=datetime.now()
    )
    
    return connected_tunnel, event

def close_tunnel(
    tunnel: Tunnel,
    reason: Optional[str] = None
) -> Tuple[Tunnel, TunnelClosed]:
    """터널 종료 - 새 상태와 이벤트 반환"""
    if tunnel.status == "closed":
        raise InvalidStateError("Tunnel is already closed")
    
    closed_tunnel = tunnel.with_status(
        "closed",
        error_message=reason
    )
    
    event = TunnelClosed(
        tunnel_id=tunnel.id,
        reason=reason,
        occurred_at=datetime.now()
    )
    
    return closed_tunnel, event

def tunnel_to_config_entry(tunnel: Tunnel) -> Dict[str, Any]:
    """터널을 설정 엔트리로 변환 - 순수 함수"""
    entry = {
        'name': tunnel.id.value,
        'type': tunnel.config.tunnel_type,
        'local_ip': '127.0.0.1',
        'local_port': tunnel.config.local_port.value
    }
    
    if isinstance(tunnel, TCPTunnel) and tunnel.config.remote_port:
        entry['remote_port'] = tunnel.config.remote_port.value
    elif isinstance(tunnel, HTTPTunnel):
        if tunnel.vhost:
            entry['custom_domains'] = tunnel.vhost
        # 추가 HTTP 설정
    
    # 추가 옵션
    entry.update(tunnel.config.options)
    
    return entry

def validate_tunnel(tunnel: Tunnel) -> Result[Tunnel, List[str]]:
    """터널 유효성 검증 - 순수 함수"""
    errors = []
    
    # 포트 검증
    if tunnel.config.local_port.value < 1024:
        errors.append("Privileged ports (<1024) require root access")
    
    # TCP 터널 검증
    if isinstance(tunnel, TCPTunnel):
        if tunnel.config.remote_port and tunnel.config.remote_port.value < 1024:
            errors.append("Remote privileged ports not allowed")
    
    # HTTP 터널 검증
    if isinstance(tunnel, HTTPTunnel):
        if tunnel.path and len(tunnel.path) > 100:
            errors.append("Path too long (max 100 characters)")
    
    return Ok(tunnel) if not errors else Err(errors)
```

### 3. 터널 관리 함수
```python
# src/core/tunnel_manager.py
from typing import Dict, List, Optional
from src.domain.tunnel import Tunnel, TunnelId
from src.domain.types import Result, Ok, Err

def add_tunnel_to_registry(
    registry: Dict[str, Tunnel],
    tunnel: Tunnel
) -> Dict[str, Tunnel]:
    """터널을 레지스트리에 추가 - 순수 함수"""
    return {**registry, tunnel.id.value: tunnel}

def remove_tunnel_from_registry(
    registry: Dict[str, Tunnel],
    tunnel_id: TunnelId
) -> Dict[str, Tunnel]:
    """터널을 레지스트리에서 제거 - 순수 함수"""
    return {k: v for k, v in registry.items() if k != tunnel_id.value}

def update_tunnel_in_registry(
    registry: Dict[str, Tunnel],
    tunnel: Tunnel
) -> Dict[str, Tunnel]:
    """레지스트리의 터널 업데이트 - 순수 함수"""
    if tunnel.id.value not in registry:
        raise KeyError(f"Tunnel {tunnel.id.value} not found in registry")
    
    return {**registry, tunnel.id.value: tunnel}

def find_tunnels_by_status(
    registry: Dict[str, Tunnel],
    status: str
) -> List[Tunnel]:
    """상태별 터널 찾기 - 순수 함수"""
    return [t for t in registry.values() if t.status == status]

def find_tunnels_by_client(
    registry: Dict[str, Tunnel],
    client_id: ClientId
) -> List[Tunnel]:
    """클라이언트별 터널 찾기 - 순수 함수"""
    return [t for t in registry.values() if t.client_id == client_id]
```

### 4. 이펙트 인터페이스
```python
# src/effects/protocols.py
from typing import Protocol, Optional
from src.domain.types import Result

class PortAllocator(Protocol):
    """포트 할당 인터페이스"""
    
    def allocate_port(self, preferred: Optional[int] = None) -> Result[int, str]:
        """사용 가능한 포트 할당"""
        ...
    
    def release_port(self, port: int) -> Result[None, str]:
        """할당된 포트 해제"""
        ...
    
    def is_port_available(self, port: int) -> bool:
        """포트 사용 가능 여부 확인"""
        ...

class TunnelMonitor(Protocol):
    """터널 모니터링 인터페이스"""
    
    def check_tunnel_health(self, tunnel_id: str) -> Result[bool, str]:
        """터널 상태 확인"""
        ...
    
    def get_tunnel_metrics(self, tunnel_id: str) -> Result[Dict[str, Any], str]:
        """터널 메트릭 조회"""
        ...
```

### 5. 애플리케이션 서비스
```python
# src/application/tunnel_service.py
from typing import Dict, List, Optional
from src.domain.tunnel import Tunnel, TunnelId
from src.domain.client import Client
from src.domain.types import Result, Ok, Err
from src.core import tunnel_operations, tunnel_manager, config_builder
from src.effects.protocols import ProcessExecutor, FileWriter, PortAllocator, EventStore
from src.application.pipelines import pipe, flat_map_result, map_result

class TunnelService:
    """터널 관리 서비스 - 순수 함수들을 조합"""
    
    def __init__(
        self,
        process_executor: ProcessExecutor,
        file_writer: FileWriter,
        port_allocator: PortAllocator,
        event_store: EventStore
    ):
        self._process_executor = process_executor
        self._file_writer = file_writer
        self._port_allocator = port_allocator
        self._event_store = event_store
        self._tunnels: Dict[str, Tunnel] = {}
    
    def create_tcp_tunnel(
        self,
        client: Client,
        local_port: int,
        remote_port: Optional[int] = None
    ) -> Result[Tunnel, str]:
        """TCP 터널 생성 파이프라인"""
        
        # 1. 연결 상태 확인
        if client.connection_state.status != "connected":
            return Err("Client is not connected")
        
        # 2. 터널 생성 및 연결 파이프라인
        return pipe(
            lambda _: tunnel_operations.create_tcp_tunnel(
                client.id, local_port, remote_port
            ),
            flat_map_result(tunnel_operations.validate_tunnel),
            flat_map_result(lambda t: self._allocate_port_if_needed(t)),
            flat_map_result(lambda t: self._add_tunnel_to_config(t, client)),
            flat_map_result(lambda data: self._restart_and_connect(data)),
            map_result(lambda data: self._finalize_tunnel(data))
        )(None)
    
    def _allocate_port_if_needed(
        self,
        tunnel: Tunnel
    ) -> Result[Tunnel, str]:
        """필요시 원격 포트 할당"""
        if isinstance(tunnel, TCPTunnel) and not tunnel.config.remote_port:
            # 포트 할당 (Effect)
            port_result = self._port_allocator.allocate_port()
            if port_result.is_err():
                return Err(f"Failed to allocate port: {port_result.error}")
            
            allocated_port = port_result.unwrap()
            
            # 새 설정으로 터널 생성
            new_config = dataclasses.replace(
                tunnel.config,
                remote_port=Port(allocated_port)
            )
            new_tunnel = dataclasses.replace(tunnel, config=new_config)
            
            return Ok(new_tunnel)
        
        return Ok(tunnel)
    
    def _add_tunnel_to_config(
        self,
        tunnel: Tunnel,
        client: Client
    ) -> Result[Dict[str, Any], str]:
        """터널을 설정에 추가"""
        # 현재 설정 가져오기
        current_config = self._get_current_config(client)
        
        # 터널 설정 엔트리 생성 (순수)
        tunnel_entry = tunnel_operations.tunnel_to_config_entry(tunnel)
        
        # 설정에 터널 추가 (순수)
        new_config = config_builder.add_tunnel_to_config(
            current_config,
            tunnel_entry
        )
        
        # 설정 파일 작성 (Effect)
        config_content = config_builder.build_ini_content(new_config)
        write_result = self._file_writer.write_temp(config_content)
        
        if write_result.is_err():
            return Err(f"Failed to write config: {write_result.error}")
        
        config_path = write_result.unwrap()
        
        return Ok({
            'tunnel': tunnel,
            'client': client,
            'config': new_config,
            'config_path': config_path
        })
    
    def _restart_and_connect(
        self,
        data: Dict[str, Any]
    ) -> Result[Dict[str, Any], str]:
        """프로세스 재시작 및 터널 연결"""
        tunnel = data['tunnel']
        client = data['client']
        config_path = data['config_path']
        
        # 프로세스 재시작 (Effect)
        restart_result = self._restart_client_process(client, config_path)
        if restart_result.is_err():
            return restart_result
        
        # 터널 연결 대기
        if self._wait_for_tunnel(tunnel.id):
            # 터널 연결 상태 업데이트 (순수)
            connected_tunnel, event = tunnel_operations.connect_tunnel(tunnel)
            
            # 이벤트 저장
            self._event_store.append(event)
            
            return Ok({
                **data,
                'tunnel': connected_tunnel
            })
        else:
            return Err(f"Failed to connect tunnel {tunnel.id.value}")
    
    def _finalize_tunnel(self, data: Dict[str, Any]) -> Tunnel:
        """터널 생성 완료 처리"""
        tunnel = data['tunnel']
        
        # 레지스트리에 추가 (순수 함수로 새 레지스트리 생성)
        self._tunnels = tunnel_manager.add_tunnel_to_registry(
            self._tunnels,
            tunnel
        )
        
        # 생성 이벤트 발행
        event = TunnelCreated(
            tunnel_id=tunnel.id,
            tunnel_type=tunnel.config.tunnel_type,
            occurred_at=datetime.now()
        )
        self._event_store.append(event)
        
        return tunnel
    
    def close_tunnel(
        self,
        tunnel_id: TunnelId
    ) -> Result[Tunnel, str]:
        """터널 종료"""
        if tunnel_id.value not in self._tunnels:
            return Err(f"Tunnel {tunnel_id.value} not found")
        
        tunnel = self._tunnels[tunnel_id.value]
        
        # 터널 종료 (순수)
        closed_tunnel, event = tunnel_operations.close_tunnel(tunnel)
        
        # 설정에서 제거
        config_result = self._remove_tunnel_from_config(tunnel)
        if config_result.is_err():
            return config_result
        
        # 포트 해제 (TCP 터널의 경우)
        if isinstance(tunnel, TCPTunnel) and tunnel.config.remote_port:
            self._port_allocator.release_port(tunnel.config.remote_port.value)
        
        # 레지스트리에서 제거 (순수)
        self._tunnels = tunnel_manager.remove_tunnel_from_registry(
            self._tunnels,
            tunnel_id
        )
        
        # 이벤트 저장
        self._event_store.append(event)
        
        return Ok(closed_tunnel)
    
    def list_tunnels(self, client_id: Optional[ClientId] = None) -> List[Tunnel]:
        """터널 목록 조회"""
        if client_id:
            return tunnel_manager.find_tunnels_by_client(self._tunnels, client_id)
        return list(self._tunnels.values())
```

### 6. 공개 API
```python
# src/api/client.py (기존 Client 클래스에 추가)

class Client:
    """FRP 클라이언트 API 래퍼"""
    
    def __init__(self, container: Container):
        self._container = container
        self._tunnel_service = container.resolve(TunnelService)
        self._client_data = None  # 불변 Client 객체 참조
    
    def expose_tcp(
        self,
        local_port: int,
        remote_port: Optional[int] = None
    ) -> Result[Tunnel, str]:
        """
        TCP 포트를 외부에 노출
        
        Args:
            local_port: 로컬 포트 번호
            remote_port: 원격 포트 번호 (None이면 자동 할당)
        
        Returns:
            Result[Tunnel, str]: 성공 시 Ok(tunnel), 실패 시 Err(message)
        
        Example:
            >>> result = client.expose_tcp(3000, 8080)
            >>> match result:
            ...     case Ok(tunnel):
            ...         print(f"Tunnel endpoint: {tunnel.endpoint}")
            ...     case Err(error):
            ...         print(f"Failed: {error}")
        """
        return self._tunnel_service.create_tcp_tunnel(
            self._client_data,
            local_port,
            remote_port
        )
    
    def list_tunnels(self) -> List[Tunnel]:
        """활성 터널 목록 조회"""
        return self._tunnel_service.list_tunnels(self._client_data.id)
    
    def close_tunnel(self, tunnel_id: TunnelId) -> Result[None, str]:
        """특정 터널 종료"""
        result = self._tunnel_service.close_tunnel(tunnel_id)
        return Ok(None) if result.is_ok() else Err(result.error)
```

## 테스트 시나리오

### 순수 함수 테스트

1. **TCP 터널 생성 테스트**
   ```python
   def test_create_tcp_tunnel():
       client_id = ClientId("test-client")
       result = create_tcp_tunnel(client_id, 3000, 8080)
       
       assert result.is_ok()
       tunnel = result.unwrap()
       assert tunnel.config.local_port.value == 3000
       assert tunnel.config.remote_port.value == 8080
       assert tunnel.status == "pending"
   ```

2. **터널 상태 전환 테스트**
   ```python
   def test_tunnel_state_transitions():
       # 터널 생성
       tunnel = create_tcp_tunnel(ClientId("test"), 3000).unwrap()
       
       # 연결 테스트
       connected_tunnel, event = connect_tunnel(tunnel, 8080)
       assert connected_tunnel.status == "connected"
       assert connected_tunnel.connected_at is not None
       assert isinstance(event, TunnelConnected)
       
       # 종료 테스트
       closed_tunnel, event = close_tunnel(connected_tunnel, "test complete")
       assert closed_tunnel.status == "closed"
       assert isinstance(event, TunnelClosed)
   ```

3. **터널 설정 변환 테스트**
   ```python
   def test_tunnel_to_config_entry():
       tunnel = create_tcp_tunnel(ClientId("test"), 3000, 8080).unwrap()
       entry = tunnel_to_config_entry(tunnel)
       
       assert entry['name'] == tunnel.id.value
       assert entry['type'] == 'tcp'
       assert entry['local_port'] == 3000
       assert entry['remote_port'] == 8080
   ```

### 속성 기반 테스트

```python
from hypothesis import given, strategies as st

@given(
    local_port=st.integers(min_value=1024, max_value=65535),
    remote_port=st.integers(min_value=1024, max_value=65535)
)
def test_tcp_tunnel_properties(local_port, remote_port):
    """유효한 포트에 대한 TCP 터널 생성"""
    result = create_tcp_tunnel(ClientId("test"), local_port, remote_port)
    
    assert result.is_ok()
    tunnel = result.unwrap()
    assert tunnel.config.local_port.value == local_port
    assert tunnel.config.remote_port.value == remote_port
    
    # 불변성 테스트
    with pytest.raises(dataclasses.FrozenInstanceError):
        tunnel.status = "connected"
```

### 이펙트 모킹 테스트

```python
def test_tunnel_service_with_mocks():
    # Mock 생성
    port_allocator = Mock(spec=PortAllocator)
    port_allocator.allocate_port.return_value = Ok(8080)
    
    process_executor = Mock(spec=ProcessExecutor)
    file_writer = Mock(spec=FileWriter)
    file_writer.write_temp.return_value = Ok("/tmp/test.ini")
    
    event_store = Mock(spec=EventStore)
    
    # 서비스 테스트
    service = TunnelService(
        process_executor=process_executor,
        file_writer=file_writer,
        port_allocator=port_allocator,
        event_store=event_store
    )
    
    # 연결된 클라이언트 생성
    client = create_test_connected_client()
    
    # TCP 터널 생성
    result = service.create_tcp_tunnel(client, 3000)
    
    assert result.is_ok()
    tunnel = result.unwrap()
    assert tunnel.config.remote_port.value == 8080
    assert port_allocator.allocate_port.called
    assert file_writer.write_temp.called
```

### 통합 테스트

1. **실제 TCP 터널 테스트**
   - 로컬 TCP 서버 시작
   - Docker 컨테이너에서 FRP 서버 실행
   - 터널 생성 및 연결 테스트
   - 외부에서 연결 확인

2. **다중 터널 관리**
   - 여러 터널 생성
   - 터널 목록 조회
   - 선택적 터널 종료
   - 상태 일관성 확인

## 파일 구조
```
src/
├── domain/
│   ├── __init__.py
│   ├── tunnel.py           # Tunnel, TCPTunnel, HTTPTunnel
│   └── events.py           # TunnelCreated, TunnelConnected
├── core/
│   ├── __init__.py
│   ├── tunnel_operations.py  # 터널 관련 순수 함수
│   └── tunnel_manager.py      # 터널 관리 순수 함수
├── effects/
│   ├── __init__.py
│   ├── protocols.py        # PortAllocator, TunnelMonitor
│   └── port_effects.py     # NetworkPortAllocator 구현
├── application/
│   ├── __init__.py
│   └── tunnel_service.py   # TunnelService (조합)
└── api/
    └── client.py           # Client 터널 메서드 추가

tests/
├── __init__.py
├── test_domain/
│   └── test_tunnel.py      # 도메인 모델 테스트
├── test_core/
│   ├── test_tunnel_operations.py  # 순수 함수 테스트
│   └── test_tunnel_manager.py     # 관리 함수 테스트
└── test_application/
    └── test_tunnel_service.py      # 서비스 테스트
```

## 완료 기준

### 필수 기능
- [x] 터널 도메인 모델 정의
- [x] TCP 터널 생성 순수 함수
- [x] 터널 상태 전환 순수 함수
- [x] 터널 관리 순수 함수
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
- 터널 관리 함수: 3시간
- 서비스 계층 구현: 5시간
- 테스트 작성: 5시간
- 문서화: 2시간

**총 예상 시간**: 22시간 (4.5일)

## 다음 단계 준비
- HTTPTunnel 도메인 모델
- 서브패스 라우팅 설계
- URL 생성 로직

## 참고 사항
- 터널 상태는 완전히 불변
- 모든 상태 변경은 새 인스턴스 생성
- 포트 할당은 Effect로 격리
- 터널 ID는 UUID로 자동 생성
- 이벤트 소싱으로 상태 변경 추적