# Tunnel Management Module

FRP 터널을 정의하고 관리하는 모듈입니다. HTTP와 TCP 터널을 지원하며, 경로 기반 라우팅 및 충돌 감지 기능을 제공합니다.

## 역할

- HTTP/TCP 터널 모델 정의
- 터널 레지스트리 관리
- 경로 기반 라우팅 및 충돌 감지
- 터널별 frpc 프로세스 관리
- 터널 상태 추적 및 전환

## 모듈 구조

```
tunnel/
├── models.py      # 터널 모델 (BaseTunnel, HTTPTunnel, TCPTunnel)
├── config.py      # TunnelConfig - 터널 관리자 설정
├── routing/       # 경로 라우팅 관련 모듈
│   ├── patterns.py   # PathPattern - 경로 패턴 매칭
│   ├── conflicts.py  # PathConflict - 충돌 타입 정의
│   ├── detector.py   # PathConflictDetector - 충돌 감지
│   └── validator.py  # PathValidator - 경로 유효성 검증
├── exceptions.py  # 터널 관련 예외 클래스
├── registry.py    # TunnelRegistry - 터널 저장소
├── process.py     # TunnelProcessManager - 프로세스 관리
└── manager.py     # TunnelManager - 터널 관리자
```

## 주요 컴포넌트

### 터널 모델 (models.py)

#### TunnelType
```python
class TunnelType(Enum):
    HTTP = "http"
    TCP = "tcp"
    UDP = "udp"
    STCP = "stcp"
    SUDP = "sudp"
```

#### TunnelStatus
```python
class TunnelStatus(Enum):
    PENDING = "pending"      # 생성됨, 시작 대기
    CONNECTING = "connecting" # 연결 시도 중
    CONNECTED = "connected"   # 정상 연결됨
    ERROR = "error"          # 오류 발생
    STOPPED = "stopped"      # 중지됨
```

#### BaseTunnel
모든 터널의 기본 클래스:
- `id`: 고유 식별자
- `local_port`: 로컬 포트
- `tunnel_type`: 터널 타입
- `status`: 현재 상태
- `created_at`: 생성 시간
- `connected_at`: 연결 시간

#### HTTPTunnel
HTTP 터널 전용 속성:
- `path`: URL 경로 (예: "/api")
- `custom_domains`: 커스텀 도메인 목록
- `strip_path`: 프록시 시 경로 제거 여부
- `websocket`: WebSocket 지원 여부

#### TCPTunnel
TCP 터널 전용 속성:
- `remote_port`: 원격 포트 (선택사항)

### 경로 라우팅 (routing/)

#### PathPattern (patterns.py)
경로 패턴을 분석하고 매칭합니다.
```python
pattern = PathPattern("/api/*")
pattern.matches("/api/users")  # True
pattern.specificity  # 패턴의 구체성 점수
```

#### PathConflictDetector (detector.py)
여러 경로 간의 충돌을 감지합니다.
```python
detector = PathConflictDetector()
conflicts = detector.check_conflicts([
    "/api/*",
    "/api/users",  # 충돌: 더 구체적인 경로
    "/app"
])
```

충돌 타입:
- `EXACT_DUPLICATE`: 정확히 같은 경로
- `WILDCARD_OVERLAP`: 와일드카드 중복
- `PREFIX_CONFLICT`: 접두사 충돌

#### PathValidator (validator.py)
경로의 유효성을 검증합니다.
- 빈 경로 확인
- 선행 슬래시 확인
- 유효하지 않은 문자 확인
- 예약된 경로 확인

### 터널 레지스트리 (registry.py)

터널을 저장하고 관리하는 저장소입니다.

```python
registry = TunnelRegistry(max_tunnels=10)
registry.add_tunnel(tunnel)
registry.get_tunnel("tunnel-id")
registry.list_tunnels(status=TunnelStatus.CONNECTED)
```

주요 기능:
- 터널 추가/제거
- 상태별 필터링
- 최대 터널 수 제한
- 경로 충돌 검사 (HTTP 터널)

### 터널 프로세스 관리자 (process.py)

각 터널별로 독립적인 frpc 프로세스를 관리합니다.

```python
process_manager = TunnelProcessManager(config, "/usr/bin/frpc")
success = process_manager.start_tunnel_process(tunnel)
process_manager.stop_tunnel_process(tunnel.id)
```

특징:
- 터널별 독립 프로세스
- 설정 파일 자동 생성
- 프로세스 상태 모니터링
- 비정상 종료 시 정리

### 터널 관리자 (manager.py)

모든 터널 관련 작업을 조율하는 최상위 관리자입니다.

```python
manager = TunnelManager(config)

# HTTP 터널 생성
tunnel = manager.create_http_tunnel(
    local_port=3000,
    path="/api",
    custom_domains=["api.example.com"]
)

# 터널 시작
manager.start_tunnel(tunnel.id)

# 터널 정보 조회
info = manager.get_tunnel_info(tunnel.id)

# 모든 터널 중지
manager.shutdown_all()
```

## FRP 설정 매핑

### HTTPTunnel → frpc 설정
```toml
[[proxies]]
name = "http-3000-api-abc123"
type = "http"
localPort = 3000
customDomains = ["example.com", "api.example.com"]
locations = ["/api"]
stripPrefix = ["/api"]  # strip_path=True인 경우
```

### TCPTunnel → frpc 설정
```toml
[[proxies]]
name = "tcp-22-2222-xyz789"
type = "tcp"
localPort = 22
remotePort = 2222  # 지정된 경우
```

## 의존성

- `../config.py` - ConfigBuilder (TOML 설정 생성)
- `../process.py` - ProcessManager (프로세스 관리)
- `../../common/exceptions.py` - 기본 예외 클래스
- `../../common/logging.py` - 구조화된 로깅
- `../../common/utils.py` - 유틸리티 함수

## 사용 예시

### 터널 생성 및 관리
```python
from frp_wrapper.client.tunnel import TunnelManager, TunnelConfig

config = TunnelConfig(
    server_host="example.com",
    auth_token="secret",
    max_tunnels=10
)

manager = TunnelManager(config)

# HTTP 터널 생성
http_tunnel = manager.create_http_tunnel(
    local_port=3000,
    path="/api",
    strip_path=True,
    websocket=True
)

# TCP 터널 생성
tcp_tunnel = manager.create_tcp_tunnel(
    local_port=22,
    remote_port=2222
)

# 터널 시작
manager.start_tunnel(http_tunnel.id)
manager.start_tunnel(tcp_tunnel.id)

# 활성 터널 조회
active_tunnels = manager.list_active_tunnels()
```

### 경로 충돌 검사
```python
from frp_wrapper.client.tunnel.routing import PathConflictDetector

detector = PathConflictDetector()
conflicts = detector.check_conflicts([
    "/api/*",
    "/api/v1",
    "/api/v2"
])

for conflict in conflicts:
    print(f"충돌: {conflict.path1} vs {conflict.path2}")
    print(f"타입: {conflict.conflict_type}")
```
