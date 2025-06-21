# Checkpoint 1: FRP 프로세스 관리 (함수형 접근)

## 개요
FRP 바이너리(frpc)를 Python에서 안정적으로 실행하고 관리하는 기반 구조를 함수형 프로그래밍 패러다임으로 구현합니다.

## 설계 원칙
- **불변성**: 모든 프로세스 상태는 불변 객체로 관리
- **순수 함수**: 프로세스 상태 변환은 순수 함수로 처리
- **이펙트 격리**: I/O 작업은 명시적으로 분리
- **이벤트 소싱**: 모든 상태 변경을 이벤트로 추적

## 목표
- FRP 프로세스의 생명주기 관리 (시작, 종료, 재시작)
- 프로세스 출력 스트림 처리
- 설정 파일 동적 생성 및 관리
- 프로세스 상태 모니터링

## 구현 범위

### 1. 도메인 모델 (불변 데이터)
```python
# src/domain/process.py
from dataclasses import dataclass, frozen
from typing import Optional
from datetime import datetime

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

### 2. 순수 함수 (비즈니스 로직)
```python
# src/core/process_operations.py
from typing import Tuple, Optional
from src.domain.process import Process, ProcessId
from src.domain.events import ProcessStarted, ProcessStopped
from src.domain.types import Result, Ok, Err

def create_process(
    binary_path: str,
    config_path: str
) -> Result[Process, str]:
    """프로세스 생성 - 순수 함수"""
    try:
        return Ok(Process(
            id=ProcessId(str(uuid.uuid4())),
            binary_path=BinaryPath(binary_path),
            config_path=config_path
        ))
    except ValueError as e:
        return Err(str(e))

def start_process(
    process: Process,
    pid: int
) -> Tuple[Process, ProcessStarted]:
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

def stop_process(
    process: Process,
    exit_code: Optional[int] = None
) -> Tuple[Process, ProcessStopped]:
    """프로세스 종료 - 새 상태와 이벤트 반환"""
    if process.status != "running":
        raise InvalidStateError(f"Cannot stop process in {process.status} state")
    
    new_process = process.with_status(
        "stopped",
        pid=None,
        started_at=None
    )
    
    event = ProcessStopped(
        process_id=process.id,
        exit_code=exit_code,
        occurred_at=datetime.now()
    )
    
    return new_process, event
```

### 3. 이펙트 인터페이스
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
    
    def write_temp(self, content: str, suffix: str = ".ini") -> Result[str, str]:
        """임시 파일 작성하고 경로 반환"""
        ...
    
    def delete(self, path: str) -> Result[None, str]:
        """파일 삭제"""
        ...
```

### 4. 설정 생성 (순수 함수)
```python
# src/core/config_builder.py
from src.domain.config import FRPConfig, ServerConfig, TunnelConfig
from src.domain.types import Result, Ok, Err

def create_config(
    server_addr: str,
    port: int = 7000,
    auth_token: Optional[str] = None
) -> FRPConfig:
    """설정 생성 - 순수 함수"""
    return FRPConfig(
        server=ServerConfig(
            address=server_addr,
            port=port,
            auth_token=auth_token
        ),
        tunnels=[]
    )

def add_tunnel_to_config(
    config: FRPConfig,
    tunnel: TunnelConfig
) -> FRPConfig:
    """터널 추가 - 새 설정 객체 반환"""
    return config.add_tunnel(tunnel)

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
```

## 테스트 시나리오

### 순수 함수 테스트

1. **프로세스 생성 테스트**
   ```python
   def test_create_process():
       result = create_process("/usr/local/bin/frpc", "/tmp/config.ini")
       
       assert result.is_ok()
       process = result.unwrap()
       assert process.status == "stopped"
       assert process.binary_path.value == "/usr/local/bin/frpc"
   ```

2. **프로세스 상태 전환 테스트**
   ```python
   def test_process_state_transitions():
       # 프로세스 생성
       process = create_process("/usr/local/bin/frpc", "/tmp/config.ini").unwrap()
       
       # 시작 테스트
       new_process, event = start_process(process, 12345)
       assert new_process.status == "running"
       assert new_process.pid == 12345
       assert isinstance(event, ProcessStarted)
       
       # 종료 테스트
       final_process, stop_event = stop_process(new_process)
       assert final_process.status == "stopped"
       assert final_process.pid is None
       assert isinstance(stop_event, ProcessStopped)
   ```

3. **설정 생성 테스트**
   ```python
   def test_config_building():
       # 기본 설정 생성
       config = create_config("example.com", 7000, "secret123")
       
       # 터널 추가
       tunnel = TunnelConfig(
           name="web",
           tunnel_type="tcp",
           local_port=3000,
           remote_config={"remote_port": 8080}
       )
       new_config = add_tunnel_to_config(config, tunnel)
       
       # INI 변환 테스트
       ini_content = build_ini_content(new_config)
       assert "[common]" in ini_content
       assert "server_addr = example.com" in ini_content
       assert "token = secret123" in ini_content
       assert "[web]" in ini_content
   ```

### 이펙트 모킹 테스트

```python
from unittest.mock import Mock
from src.domain.types import Ok, Err

def test_process_executor_mock():
    # Mock 생성
    executor = Mock(spec=ProcessExecutor)
    executor.spawn.return_value = Ok(12345)
    executor.terminate.return_value = Ok(None)
    executor.is_alive.return_value = True
    
    # 테스트
    spawn_result = executor.spawn(["/usr/local/bin/frpc", "-c", "/tmp/config.ini"])
    assert spawn_result.is_ok()
    assert spawn_result.unwrap() == 12345
    
    terminate_result = executor.terminate(12345)
    assert terminate_result.is_ok()
```

### 속성 기반 테스트

```python
from hypothesis import given, strategies as st

@given(
    binary_path=st.text(min_size=1),
    config_path=st.text(min_size=1)
)
def test_process_creation_properties(binary_path, config_path):
    # 유효한 경로를 가정
    with patch('os.path.exists', return_value=True):
        result = create_process(binary_path, config_path)
        
        if result.is_ok():
            process = result.unwrap()
            # 불변성 테스트
            assert process.binary_path.value == binary_path
            assert process.config_path == config_path
            # 두 번 호출해도 같은 결과
            result2 = create_process(binary_path, config_path)
            assert result2.is_ok()
```

### 통합 테스트

1. **실제 FRP 바이너리 테스트**
   - Docker 컨테이너에서 FRP 서버 실행
   - 실제 frpc 바이너리로 연결 테스트
   - 프로세스 재시작 시 연결 복구 확인

2. **설정 파일 업데이트**
   - 실행 중 설정 변경
   - 프로세스 재시작
   - 새 설정 적용 확인

## 파일 구조
```
src/
├── domain/
│   ├── __init__.py
│   ├── process.py          # Process, ProcessId, BinaryPath
│   ├── config.py           # FRPConfig, ServerConfig
│   ├── events.py           # ProcessStarted, ProcessStopped
│   └── types.py            # Result, Ok, Err
├── core/
│   ├── __init__.py
│   ├── process_operations.py  # 프로세스 관련 순수 함수
│   └── config_builder.py      # 설정 생성 순수 함수
├── effects/
│   ├── __init__.py
│   ├── protocols.py        # ProcessExecutor, FileWriter 인터페이스
│   ├── process_effects.py  # SubprocessExecutor 구현
│   └── file_effects.py     # TempFileWriter 구현
└── application/
    ├── __init__.py
    └── process_service.py  # ProcessService (조합)

tests/
├── __init__.py
├── test_domain/
│   └── test_process.py     # 도메인 모델 테스트
├── test_core/
│   ├── test_process_operations.py  # 순수 함수 테스트
│   └── test_config_builder.py      # 설정 생성 테스트
└── test_effects/
    └── test_mocks.py       # 이펙트 모킹 테스트
```

## 완료 기준

### 필수 기능
- [x] 프로세스 도메인 모델 정의
- [x] 프로세스 상태 변환 순수 함수
- [x] 설정 생성 순수 함수
- [x] 이펙트 인터페이스 정의
- [x] Result 타입 기반 오류 처리

### 테스트
- [x] 순수 함수 단위 테스트
- [x] 속성 기반 테스트
- [x] 이펙트 모킹 테스트
- [x] 이벤트 생성 검증

### 문서
- [x] 모든 함수에 타입 힌트와 docstring
- [x] 함수형 사용 예제
- [x] 도메인 모델 설명

## 예상 작업 시간
- 도메인 모델 설계: 3시간
- 순수 함수 구현: 4시간
- 이펙트 인터페이스 및 구현: 3시간
- 테스트 작성: 4시간
- 문서화: 2시간
- 리뷰 및 수정: 2시간

**총 예상 시간**: 18시간 (3.5일)

## 다음 단계 준비
- FRPClient 클래스 설계
- 터널 추상화 계획
- API 인터페이스 정의

## 참고 사항
- 불변성을 통한 안전한 상태 관리
- 이펙트 격리로 테스트 용이성 확보
- Result 타입을 통한 명시적 오류 처리
- 이벤트 소싱으로 상태 변경 추적
- 크로스 플랫폼 호환성 고려