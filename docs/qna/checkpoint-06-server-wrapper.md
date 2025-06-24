# Checkpoint 6: FRP Server Wrapper 이해하기

## 🎯 목적: 왜 FRP 서버 래퍼가 필요해?

FRP 서버(frps)를 운영하려면 직접 바이너리를 관리해야 합니다. 하지만...

### 문제점들:
1. **서버 프로세스 관리가 복잡함**
   ```bash
   # 시작
   ./frps -c frps.toml &

   # 종료하려면 PID 찾아서...
   ps aux | grep frps
   kill <pid>
   ```

2. **설정 파일 관리가 번거로움**
   - TOML 형식 직접 작성
   - 문법 오류 시 디버깅 어려움
   - 설정 변경 시 재시작 필요

3. **모니터링과 로깅이 어려움**
   - 로그 파일 경로 관리
   - 대시보드 설정 복잡
   - 상태 확인 불편

## 📊 frps 실제 동작 분석

### 1. frps 실행 방법

#### 기본 실행 명령
```bash
# frps는 frpc와 동일한 패턴으로 실행됩니다!
./frps -c ./frps.toml
```

#### 주요 명령줄 옵션
```bash
./frps --help

Usage:
  frps [flags]

Flags:
  -c, --config string   config file path (default "./frps.toml")
  -v, --version        version of frps
  -h, --help           help for frps
```

### 2. frps 설정 파일 형식 (TOML)

#### 최소 설정 예시
```toml
# frps.toml
bindAddr = "0.0.0.0"
bindPort = 7000
```

#### 전체 설정 예시
```toml
# 기본 바인드 설정
bindAddr = "0.0.0.0"
bindPort = 7000

# KCP 프로토콜 지원 (선택)
kcpBindPort = 7000

# 가상 호스트 설정
vhostHTTPPort = 80
vhostHTTPSPort = 443

# 인증 설정
auth.method = "token"
auth.token = "your-secure-token"

# 서브도메인 설정
subDomainHost = "frp.example.com"

# 로깅 설정
log.level = "info"
log.maxDays = 3
log.file = "./frps.log"

# 성능 설정
maxPoolCount = 5
maxPortsPerClient = 0  # 0 = unlimited
heartbeatTimeout = 90

# 웹 대시보드 설정
[webServer]
addr = "0.0.0.0"
port = 7500
user = "admin"
password = "admin123"
```

### 3. 실행 시 동작

#### 성공적인 시작
```bash
$ ./frps -c frps.toml
2024/01/01 10:00:00 [I] [root.go:101] frps uses config file: frps.toml
2024/01/01 10:00:00 [I] [service.go:200] frps tcp listen on 0.0.0.0:7000
2024/01/01 10:00:00 [I] [service.go:250] http service listen on 0.0.0.0:80
2024/01/01 10:00:00 [I] [service.go:290] https service listen on 0.0.0.0:443
2024/01/01 10:00:00 [I] [service.go:350] dashboard listen on 0.0.0.0:7500
2024/01/01 10:00:00 [I] [root.go:110] frps started successfully
```

#### 포트 충돌 시
```bash
$ ./frps -c frps.toml
2024/01/01 10:00:00 [E] [service.go:201] listen tcp 0.0.0.0:7000: bind: address already in use
```

## 🔄 Python 래퍼 설계

### 1. ProcessManager 재사용

현재 ProcessManager는 frpc를 위해 설계되었지만, **frps도 동일한 실행 패턴**을 사용합니다:

```python
# 현재 ProcessManager 사용법 (frpc)
pm = ProcessManager("/usr/local/bin/frpc", "config.toml")
pm.start()

# frps도 완전히 동일!
pm = ProcessManager("/usr/local/bin/frps", "config.toml")
pm.start()
```

따라서 ServerProcessManager는 단순히 기본 경로만 변경하면 됩니다:

```python
class ServerProcessManager(ProcessManager):
    def __init__(self, binary_path: str = "/usr/local/bin/frps", config_path: str = ""):
        super().__init__(binary_path, config_path)
```

### 2. 서버 전용 설정 모델

Pydantic을 사용하여 강력한 타입 검증을 제공합니다:

```python
class ServerConfig(BaseModel):
    # 기본 서버 설정
    bind_addr: str = Field(default="0.0.0.0")
    bind_port: int = Field(default=7000, ge=1, le=65535)

    # 가상 호스트 설정
    vhost_http_port: int = Field(default=80, ge=1, le=65535)
    vhost_https_port: int = Field(default=443, ge=1, le=65535)

    # 인증
    auth_token: Optional[str] = Field(None, min_length=8)

    # 서브도메인
    subdomain_host: Optional[str] = Field(None)

    @field_validator('auth_token')
    def validate_auth_token(cls, v):
        if v and len(set(v)) < 4:
            raise ValueError("Token should be more complex")
        return v

class DashboardConfig(BaseModel):
    enabled: bool = Field(default=False)
    port: int = Field(default=7500, ge=1, le=65535)
    user: str = Field(default="admin", min_length=3)
    password: str = Field(..., min_length=6)

    @field_validator('password')
    def validate_password_strength(cls, v):
        # 대문자, 소문자, 숫자 포함 검증
        if not (any(c.isupper() for c in v) and
                any(c.islower() for c in v) and
                any(c.isdigit() for c in v)):
            raise ValueError("Password must contain uppercase, lowercase, and numbers")
        return v
```

### 3. ConfigBuilder 패턴 재사용

클라이언트와 동일한 빌더 패턴을 사용합니다:

```python
class ServerConfigBuilder:
    def __init__(self):
        self._server_config = ServerConfig()
        self._dashboard_config = DashboardConfig()

    def configure_basic(self, bind_port: int = 7000, auth_token: str = None):
        # 기본 설정
        return self

    def configure_vhost(self, http_port: int = 80, subdomain_host: str = None):
        # 가상 호스트 설정
        return self

    def enable_dashboard(self, port: int = 7500, user: str = "admin", password: str = "admin123"):
        # 대시보드 활성화
        return self

    def build(self) -> str:
        # TOML 파일 생성 및 경로 반환
        return temp_path
```

## 📈 실제 vs 래퍼 비교

### 1. 서버 시작

#### 기존 방식 (수동)
```bash
# 설정 파일 직접 작성
cat > frps.toml << EOF
bindAddr = "0.0.0.0"
bindPort = 7000
auth.method = "token"
auth.token = "my-secure-token"

[webServer]
addr = "0.0.0.0"
port = 7500
user = "admin"
password = "admin123"
EOF

# 서버 시작
./frps -c frps.toml &

# PID 저장
echo $! > frps.pid
```

#### Python 래퍼 방식
```python
from frp_wrapper.server import FRPServer

# Context Manager로 자동 관리
with FRPServer() as server:
    server.configure(
        bind_port=7000,
        auth_token="my-secure-token"
    )
    server.enable_dashboard(
        port=7500,
        user="admin",
        password="SecurePass123"
    )
    server.start()

    # 서버 실행 중...
    print(f"Server running: {server.is_running()}")
    print(f"Dashboard: http://localhost:7500")

# 자동으로 정리됨!
```

### 2. 설정 검증

#### 기존 방식
- TOML 문법 오류는 실행 시점에 발견
- 잘못된 설정값도 실행 시점에 발견
- 디버깅 어려움

#### Python 래퍼 방식
```python
# Pydantic이 즉시 검증
try:
    server.enable_dashboard(password="weak")  # 너무 약한 비밀번호
except ValueError as e:
    print(f"설정 오류: {e}")
    # "Password must contain uppercase, lowercase, and numbers"

# 포트 범위 자동 검증
server.configure(bind_port=99999)  # ValueError: Port must be between 1 and 65535
```

### 3. 상태 관리

#### 기존 방식
```bash
# 실행 중인지 확인
ps aux | grep frps | grep -v grep

# 로그 확인
tail -f frps.log
```

#### Python 래퍼 방식
```python
# 상태 확인
if server.is_running():
    status = server.get_status()
    print(f"PID: {status['pid']}")
    print(f"Uptime: {status['uptime']}")

# 구조화된 로깅
import structlog
logger = structlog.get_logger()
logger.info("server_status", running=True, port=7000)
```

## 💡 사용 시나리오

### 1. 기본 서버 실행
```python
from frp_wrapper.server import FRPServer

server = FRPServer()
server.configure(bind_port=7000)
server.start()

# 사용 후
server.stop()
```

### 2. 보안 설정과 함께 실행
```python
server = FRPServer()
server.configure(
    bind_port=7000,
    auth_token="very-secure-token-12345"
)
server.start()
```

### 3. 서브도메인 지원 서버
```python
with FRPServer() as server:
    server.configure(
        bind_port=7000,
        subdomain_host="tunnel.mycompany.com",
        vhost_http_port=80,
        vhost_https_port=443
    )
    server.enable_dashboard(
        password="AdminPass123!"
    )
    server.start()

    # 클라이언트는 이제 subdomain.tunnel.mycompany.com 사용 가능
```

### 4. 프로덕션 설정
```python
import logging

# 프로덕션 로깅 설정
logging.basicConfig(level=logging.INFO)

# 서버 설정
server = FRPServer(binary_path="/opt/frp/frps")
server.configure(
    bind_port=7000,
    auth_token=os.environ.get("FRP_AUTH_TOKEN"),  # 환경변수에서 읽기
    subdomain_host="frp.production.com"
)
server.configure_logging(
    level="warn",  # 프로덕션은 warn 레벨
    file_path="/var/log/frps.log",
    max_days=30
)

# 모니터링을 위한 상태 체크
if not server.start():
    alert_ops_team("FRP Server failed to start!")
```

## 🔍 핵심 인사이트

1. **frps와 frpc는 동일한 실행 패턴**: ProcessManager를 그대로 재사용 가능
2. **Pydantic 검증으로 안전성 향상**: 설정 오류를 사전에 방지
3. **Context Manager로 자동 정리**: 리소스 누수 방지
4. **일관된 API**: 클라이언트와 서버 모두 동일한 사용 경험

이 설계로 FRP 서버 관리가 훨씬 쉽고 안전해집니다!
