# 프로젝트 구조 가이드

이 문서는 FRP Python Wrapper의 프로젝트 구조를 설명합니다. 초보자도 각 파일과 디렉토리의 역할을 쉽게 이해할 수 있도록 작성되었습니다.

## 📁 전체 구조 개요

```
src/frp_wrapper/
├── __init__.py                 # 🎯 패키지 진입점 및 공개 API
├── api.py                      # 🚀 사용자 친화적인 고수준 함수
│
├── core/                       # 💡 FRP와 직접 통신하는 핵심 기능
│   ├── __init__.py
│   ├── client.py              # FRP 서버 연결 관리
│   ├── process.py             # FRP 바이너리 실행 관리
│   └── config.py              # 설정 파일 생성
│
├── tunnels/                    # 🚇 터널 생성 및 관리
│   ├── __init__.py
│   ├── models.py              # 터널 데이터 모델 정의
│   ├── manager.py             # 터널 생명주기 관리
│   ├── process.py             # 개별 터널 프로세스 제어
│   └── routing.py             # URL 경로 검증 및 라우팅
│
└── common/                     # 🔧 공통 유틸리티
    ├── __init__.py
    ├── exceptions.py          # 커스텀 예외 클래스
    ├── logging.py             # 로깅 설정
    └── utils.py               # 재사용 가능한 함수들
```

## 🎯 메인 파일들

### `__init__.py` (패키지 진입점)
**역할**: 패키지의 공개 API를 정의합니다.

```python
# 사용자가 import할 수 있는 모든 것들을 정의
from .api import create_tunnel, create_tcp_tunnel
from .core import FRPClient, ConfigBuilder
from .tunnels import TunnelManager, HTTPTunnel, TCPTunnel
```

**초보자 팁**: 사용자가 `from frp_wrapper import ...`로 가져올 수 있는 모든 것이 여기에 정의됩니다.

### `api.py` (고수준 API)
**역할**: 복잡한 내부 구조를 숨기고 간단한 함수를 제공합니다.

```python
# 한 줄로 터널 생성!
url = create_tunnel("example.com", 3000, "/myapp")
```

**주요 함수**:
- `create_tunnel()`: HTTP 터널을 쉽게 생성
- `create_tcp_tunnel()`: TCP 터널을 쉽게 생성

**초보자 팁**: 처음 시작할 때는 이 파일의 함수들만 사용해도 충분합니다!

## 💡 core/ 디렉토리 (핵심 기능)

### `core/client.py`
**역할**: FRP 서버와의 연결을 관리하는 메인 클래스입니다.

**주요 클래스**: `FRPClient`
- `connect()`: 서버에 연결
- `disconnect()`: 연결 종료
- `is_connected()`: 연결 상태 확인

**사용 예시**:
```python
client = FRPClient("example.com", auth_token="secret")
if client.connect():
    print("연결 성공!")
```

### `core/process.py`
**역할**: FRP 바이너리(frpc) 프로세스를 실행하고 관리합니다.

**주요 클래스**: `ProcessManager`
- `start()`: 프로세스 시작
- `stop()`: 프로세스 종료
- `is_running()`: 실행 상태 확인

**초보자 팁**: 이 클래스는 실제 FRP 프로그램을 실행하는 역할을 합니다. subprocess를 안전하게 관리합니다.

### `core/config.py`
**역할**: FRP가 이해할 수 있는 TOML 설정 파일을 생성합니다.

**주요 클래스**: `ConfigBuilder`
- `add_server()`: 서버 정보 추가
- `add_http_proxy()`: HTTP 터널 설정 추가
- `build()`: 설정 파일 생성

**생성되는 설정 예시**:
```toml
[common]
server_addr = "example.com"
server_port = 7000
token = "your-secret-token"

[[proxies]]
name = "my-web-app"
type = "http"
local_port = 3000
custom_domains = ["example.com"]
locations = ["/myapp"]
```

## 🚇 tunnels/ 디렉토리 (터널 관리)

### `tunnels/models.py`
**역할**: 터널 데이터를 표현하는 Pydantic 모델들입니다.

**주요 클래스**:
- `HTTPTunnel`: HTTP 터널 정보 (경로, 도메인 등)
- `TCPTunnel`: TCP 터널 정보 (포트 매핑)
- `TunnelConfig`: 터널 생성 설정

**특징**: Pydantic을 사용해 자동 검증과 타입 안정성을 제공합니다.

### `tunnels/manager.py`
**역할**: 여러 터널을 관리하는 매니저 클래스입니다.

**주요 클래스**: `TunnelManager`
- `create_http_tunnel()`: HTTP 터널 생성
- `start_tunnel()`: 터널 시작
- `stop_tunnel()`: 터널 중지
- `list_active_tunnels()`: 활성 터널 목록

**초보자 팁**: 여러 터널을 동시에 관리해야 할 때 사용합니다.

### `tunnels/process.py`
**역할**: 개별 터널의 FRP 프로세스를 관리합니다.

**주요 클래스**: `TunnelProcessManager`
- 각 터널마다 별도의 FRP 프로세스 실행
- 프로세스 상태 모니터링

### `tunnels/routing.py`
**역할**: URL 경로의 유효성을 검사하고 충돌을 방지합니다.

**주요 클래스**:
- `PathValidator`: 경로 유효성 검증
- `PathConflictDetector`: 경로 충돌 감지

**검증 예시**:
```python
# ✅ 올바른 경로
"/myapp", "/api/v1", "/blog/*"

# ❌ 잘못된 경로
"../../../etc/passwd", "/<script>", "/path/../.."
```

## 🔧 common/ 디렉토리 (공통 유틸리티)

### `common/exceptions.py`
**역할**: 프로젝트 전체에서 사용하는 커스텀 예외들입니다.

**주요 예외**:
- `FRPWrapperError`: 기본 예외 클래스
- `ConnectionError`: 연결 실패
- `AuthenticationError`: 인증 실패
- `BinaryNotFoundError`: FRP 바이너리 없음

### `common/logging.py`
**역할**: 구조화된 로깅을 설정합니다.

**특징**:
- JSON 형식의 구조화된 로그
- 파일과 콘솔에 동시 출력
- 디버그 정보 자동 포함

### `common/utils.py`
**역할**: 여러 모듈에서 공통으로 사용하는 유틸리티 함수들입니다.

**주요 함수**:
- `validate_port()`: 포트 번호 검증
- `mask_sensitive_data()`: 민감정보 마스킹
- `sanitize_log_data()`: 로그 데이터 정제

## 🔄 의존성 관계

```
api.py
  ↓
tunnels/manager.py ←→ tunnels/models.py
  ↓                      ↓
core/client.py      tunnels/routing.py
  ↓
core/process.py ←→ core/config.py
  ↓
common/* (모든 모듈에서 사용)
```

## 🚀 초보자를 위한 시작 가이드

### 1. 간단히 시작하기
```python
from frp_wrapper import create_tunnel

# 한 줄로 터널 생성!
url = create_tunnel("example.com", 3000, "/myapp")
print(f"앱 주소: {url}")
```

### 2. 더 많은 제어가 필요할 때
```python
from frp_wrapper import FRPClient

client = FRPClient("example.com", auth_token="secret")
with client:  # 자동으로 연결/해제
    # 여러 작업 수행
    pass
```

### 3. 고급 사용법
```python
from frp_wrapper import TunnelManager, TunnelConfig, HTTPTunnel

config = TunnelConfig(server_host="example.com")
manager = TunnelManager(config)

# 여러 터널 동시 관리
tunnel1 = manager.create_http_tunnel("app1", 3000, "/app1")
tunnel2 = manager.create_http_tunnel("app2", 4000, "/app2")
```

## 📝 새 기능 추가 시 가이드

### 새로운 터널 타입 추가하기
1. `tunnels/models.py`에 새 모델 클래스 추가
2. `tunnels/manager.py`에 생성 메서드 추가
3. `api.py`에 간편 함수 추가 (선택사항)

### 새로운 검증 로직 추가하기
1. `common/utils.py`에 검증 함수 추가
2. 필요한 곳에서 import하여 사용

### 새로운 예외 타입 추가하기
1. `common/exceptions.py`에 예외 클래스 정의
2. 적절한 모듈에서 raise

## 💡 디버깅 팁

### 로그 확인하기
```python
# 로그 레벨 설정
from frp_wrapper import setup_logging
setup_logging(level="DEBUG")
```

### 프로세스 상태 확인
```python
# FRP 프로세스가 실행 중인지 확인
if client.process_manager.is_running():
    print("FRP가 실행 중입니다")
```

## 🎯 핵심 요약

- **시작은 `api.py`에서**: 가장 간단한 인터페이스
- **core/**: FRP와 직접 통신하는 저수준 기능
- **tunnels/**: 터널 관리의 모든 것
- **common/**: 어디서나 쓰이는 공통 기능

이 구조를 이해하면 코드를 쉽게 탐색하고 수정할 수 있습니다!
