# Common Utilities Module

client와 server 모듈에서 공통으로 사용하는 유틸리티 및 헬퍼 모듈입니다.

## 역할

- Context Manager 패턴 구현
- 구조화된 로깅 설정
- 커스텀 예외 클래스 정의
- 공통 유틸리티 함수
- 리소스 추적 및 정리

## 모듈 구조

```
common/
├── context.py         # Context Manager 믹스인 및 헬퍼
├── context_config.py  # Context 설정 클래스
├── exceptions.py      # 커스텀 예외 클래스
├── logging.py         # structlog 설정
└── utils.py          # 유틸리티 함수
```

## 주요 컴포넌트

### ContextManagerMixin (context.py)
Context Manager 패턴을 쉽게 구현할 수 있는 믹스인 클래스입니다.

```python
class MyResource(ContextManagerMixin):
    def __init__(self):
        super().__init__(ContextConfig())

    def _setup(self):
        # 리소스 초기화
        pass

    def _cleanup(self):
        # 리소스 정리
        pass
```

주요 기능:
- 자동 리소스 정리
- 중첩된 context 지원
- 타임아웃 처리
- 예외 시 안전한 정리

### 예외 클래스 (exceptions.py)

```python
# 기본 예외
FRPWrapperError      # 모든 커스텀 예외의 기본 클래스

# 프로세스 관련
ProcessError         # 프로세스 실행 오류
BinaryNotFoundError  # FRP 바이너리를 찾을 수 없음

# 연결 관련
ConnectionError      # FRP 서버 연결 실패
TimeoutError        # 작업 타임아웃

# 터널 관련
TunnelError         # 터널 관련 일반 오류
```

### 로깅 설정 (logging.py)

structlog를 사용한 구조화된 로깅을 제공합니다.

```python
from frp_wrapper.common.logging import get_logger

logger = get_logger(__name__)

# 구조화된 로그
logger.info("서버 시작됨", port=7000, auth_enabled=True)
logger.error("연결 실패", server="example.com", error=str(e))
```

특징:
- JSON 형식 출력 지원
- 컬러 콘솔 출력
- 타임스탬프 자동 추가
- 컨텍스트 정보 보존

### 유틸리티 함수 (utils.py)

#### 포트 검증
```python
MIN_PORT = 1
MAX_PORT = 65535

def validate_port(port: int) -> None:
    """포트 번호가 유효한 범위인지 검증"""
    if not MIN_PORT <= port <= MAX_PORT:
        raise ValueError(f"포트는 {MIN_PORT}-{MAX_PORT} 범위여야 합니다")
```

#### 경로 정리
```python
def sanitize_path(path: str) -> str:
    """경로를 정리하고 정규화
    - 선행/후행 슬래시 제거
    - 중복 슬래시 제거
    - 빈 경로는 "/" 반환
    """
```

#### 민감 정보 마스킹
```python
def sanitize_log_data(data: dict) -> dict:
    """로그 데이터에서 민감한 정보 마스킹
    - password, token, secret 등의 값을 마스킹
    - 원본 데이터는 변경하지 않음
    """
```

#### FRP 바이너리 검색
```python
def find_binary(name: str) -> str | None:
    """시스템에서 FRP 바이너리 찾기
    - PATH 환경변수 검색
    - 일반적인 설치 위치 확인
    """
```

### Context 설정 (context_config.py)

Context Manager의 동작을 설정하는 클래스들입니다.

```python
@dataclass
class ContextConfig:
    """기본 context 설정"""
    timeout: float | None = None
    cleanup_on_error: bool = True
    suppress_cleanup_errors: bool = True

@dataclass
class TunnelGroupConfig(ContextConfig):
    """터널 그룹 context 설정"""
    auto_start: bool = True
    stop_on_exit: bool = True
    parallel_start: bool = False
```

## 의존성

이 모듈은 독립적이며 frp_wrapper의 다른 모듈에 의존하지 않습니다.

외부 의존성:
- `structlog`: 구조화된 로깅
- `pydantic`: 데이터 검증 (일부 모델)

## 사용 예시

### Context Manager 사용
```python
from frp_wrapper.common.context import ContextManagerMixin
from frp_wrapper.common.context_config import ContextConfig

class MyManager(ContextManagerMixin):
    def __init__(self):
        config = ContextConfig(timeout=30.0)
        super().__init__(config)

    def _setup(self):
        self.resource = acquire_resource()

    def _cleanup(self):
        release_resource(self.resource)

# 사용
with MyManager() as manager:
    # 리소스 사용
    pass
# 자동 정리됨
```

### 로깅 사용
```python
from frp_wrapper.common.logging import get_logger

logger = get_logger(__name__)

try:
    # 작업 수행
    logger.info("작업 시작", task_id="123")
except Exception as e:
    logger.error("작업 실패", task_id="123", error=str(e))
```

### 유틸리티 사용
```python
from frp_wrapper.common.utils import validate_port, sanitize_path

# 포트 검증
validate_port(8080)  # OK
validate_port(70000)  # ValueError

# 경로 정리
sanitize_path("/api//test/")  # "api/test"
sanitize_path("")  # "/"
```
