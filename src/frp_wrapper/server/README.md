# FRP Server Module

FRP 서버(frps) 바이너리를 제어하고 서버 설정을 관리하는 모듈입니다.

## 역할

- frps 프로세스 생명주기 관리
- 서버 포트 및 인증 설정
- 웹 대시보드 설정
- TOML 설정 파일 생성
- 가상 호스트(vhost) 설정

## 모듈 구조

```
server/
├── server.py    # FRPServer 메인 클래스
├── process.py   # ServerProcessManager - frps 프로세스 관리
└── config.py    # ServerConfig, DashboardConfig, ServerConfigBuilder
```

## 주요 컴포넌트

### FRPServer (server.py)
FRP 서버의 메인 진입점입니다.

```python
from frp_wrapper.server import FRPServer

# 기본 서버 시작
with FRPServer() as server:
    print(f"서버가 포트 {server.bind_port}에서 실행 중")
    # 서버는 context 종료 시 자동으로 중지됨

# 커스텀 설정
server = FRPServer(
    bind_port=7000,
    auth_token="my-secret-token",
    dashboard_port=7500,
    dashboard_user="admin",
    dashboard_password="admin123"
)
```

### ServerConfig (config.py)
frps 서버의 전체 설정을 정의합니다.

```python
# 주요 설정 옵션
- bind_port: 클라이언트 연결 포트 (기본: 7000)
- auth_method: 인증 방식 (token, oidc)
- auth_token: 인증 토큰
- vhost_http_port: HTTP 가상 호스트 포트 (기본: 80)
- vhost_https_port: HTTPS 가상 호스트 포트 (기본: 443)
- subdomain_host: 서브도메인 호스트
- log_level: 로그 레벨 (trace, debug, info, warn, error)
```

### DashboardConfig (config.py)
웹 대시보드 설정을 관리합니다.

```python
# 대시보드 설정
- enable: 대시보드 활성화 여부
- addr: 대시보드 주소 (기본: "0.0.0.0")
- port: 대시보드 포트 (기본: 7500)
- user: 대시보드 사용자명
- password: 대시보드 비밀번호 (최소 8자)
- tls_mode: TLS 모드 활성화
- assets_dir: 정적 자원 디렉토리
```

### ServerConfigBuilder (config.py)
Fluent API로 서버 설정을 구성합니다.

```python
from frp_wrapper.server import ServerConfigBuilder

config_path = (ServerConfigBuilder()
    .configure(bind_port=7000, auth_token="secret")
    .configure_vhost(http_port=80, https_port=443)
    .enable_dashboard(port=7500, user="admin", password="admin123")
    .configure_logging(level="info", max_days=7)
    .build())
```

## FRP 제어 부분

### 프로세스 실행
```bash
# ServerProcessManager가 실행하는 명령
frps -c /tmp/frps_xxxx.toml
```

### 생성되는 설정 파일 예시
```toml
# frps.toml
bindPort = 7000

[auth]
method = "token"
token = "your-secret-token"

# 가상 호스트 설정
vhostHTTPPort = 80
vhostHTTPSPort = 443
subdomainHost = "example.com"

# 로그 설정
[log]
level = "info"
maxDays = 30

# 웹 대시보드 설정
[webServer]
addr = "0.0.0.0"
port = 7500
user = "admin"
password = "admin123"
```

## 의존성

- `../common/logging.py` - 구조화된 로깅
- `../common/context.py` - Context Manager 지원
- `process.py` - 기본 ProcessManager 클래스 확장

## 사용 예시

### 기본 서버 시작
```python
from frp_wrapper.server import FRPServer

server = FRPServer()
server.start()
print(f"FRP 서버가 포트 {server.bind_port}에서 실행 중")
```

### 인증 및 대시보드 설정
```python
server = FRPServer(
    bind_port=7000,
    auth_token="secure-token",
    dashboard_port=7500,
    dashboard_user="admin",
    dashboard_password="strongpass123"
)

with server:
    print(f"대시보드: http://localhost:{server.dashboard_port}")
    # 서버 실행 중...
```

### 가상 호스트 설정
```python
from frp_wrapper.server import ServerConfigBuilder

builder = ServerConfigBuilder()
builder.configure_vhost(
    http_port=80,
    https_port=443,
    subdomain_host="*.myapp.com"
)
config_path = builder.build()
```

## 보안 고려사항

1. **인증 토큰**: 항상 강력한 토큰 사용 (최소 16자 이상)
2. **대시보드 비밀번호**: 최소 8자, 복잡도 요구사항 충족
3. **방화벽 설정**: 필요한 포트만 열기
   - 7000: 클라이언트 연결
   - 7500: 웹 대시보드 (필요시)
   - 80/443: HTTP/HTTPS 트래픽
