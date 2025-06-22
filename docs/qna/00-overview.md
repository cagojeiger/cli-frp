# FRP Wrapper 전체 개요

## 🎯 FRP Wrapper가 뭐야?

**FRP Wrapper**는 [FRP (Fast Reverse Proxy)](https://github.com/fatedier/frp)를 Python으로 쉽게 사용할 수 있게 만든 라이브러리입니다.

### 원래 FRP는 뭐야?

FRP는 NAT나 방화벽 뒤에 있는 로컬 서버를 인터넷에 공개할 수 있게 해주는 프록시 도구입니다.

```
[내 컴퓨터] ---> [FRP 클라이언트] ---> [인터넷] ---> [FRP 서버] ---> [외부 사용자]
   (로컬)          (frpc)                           (frps)          (인터넷)
```

### 그럼 FRP Wrapper는 왜 필요해?

기존 FRP 사용 방법:
```bash
# 1. 복잡한 TOML 설정 파일 작성
vim frpc.toml

# 2. 프로세스 직접 실행
./frpc -c frpc.toml

# 3. 수동으로 관리...
```

FRP Wrapper 사용 방법:
```python
# 한 줄로 끝!
url = create_tunnel("myserver.com", 3000, "/myapp")
print(f"앱 주소: {url}")  # https://myserver.com/myapp/
```

## 📊 기존 FRP vs FRP Wrapper 비교

### 1. 설정 파일 작성

**기존 FRP (frpc.toml):**
```toml
serverAddr = "example.com"
serverPort = 7000
auth.token = "secret123"

[[proxies]]
name = "web"
type = "http"
localPort = 3000
customDomains = ["example.com"]
locations = ["/myapp"]
```

**FRP Wrapper (Python):**
```python
url = create_tunnel("example.com", 3000, "/myapp", auth_token="secret123")
```

### 2. 여러 서비스 관리

**기존 FRP:**
```toml
[[proxies]]
name = "frontend"
type = "http"
localPort = 3000
customDomains = ["example.com"]
locations = ["/app"]

[[proxies]]
name = "api"
type = "http"
localPort = 8000
customDomains = ["example.com"]
locations = ["/api"]

[[proxies]]
name = "admin"
type = "http"
localPort = 8080
customDomains = ["example.com"]
locations = ["/admin"]
```

**FRP Wrapper:**
```python
frontend = create_tunnel("example.com", 3000, "/app")
api = create_tunnel("example.com", 8000, "/api")
admin = create_tunnel("example.com", 8080, "/admin")
```

### 3. 프로세스 관리

**기존 FRP:**
- 수동으로 프로세스 시작/종료
- PID 파일 관리 필요
- 에러 발생 시 수동 재시작

**FRP Wrapper:**
- 자동 프로세스 관리
- Context Manager로 자동 정리
- 에러 처리 내장

## 🏗️ 전체 아키텍처

```
FRP Wrapper
├── API Layer (간단한 함수들)
│   └── create_tunnel(), create_tcp_tunnel()
│
├── Core Layer (핵심 기능)
│   ├── FRPClient (서버 연결)
│   ├── ConfigBuilder (설정 생성)
│   └── ProcessManager (프로세스 관리)
│
├── Tunnel Layer (터널 관리)
│   ├── HTTPTunnel, TCPTunnel (터널 모델)
│   ├── TunnelManager (생명주기 관리)
│   ├── PathRouting (경로 라우팅)
│   └── TunnelProcessManager (개별 프로세스)
│
└── Common Layer (공통 기능)
    ├── Exceptions (에러 처리)
    ├── Logging (로그)
    └── Utils (유틸리티)
```

## 🚀 주요 기능

### 1. 경로 기반 라우팅 (Path-based Routing)
한 서버에서 여러 서비스를 경로로 구분:
- `https://server.com/app` → 포트 3000
- `https://server.com/api` → 포트 8000
- `https://server.com/admin` → 포트 8080

### 2. 자동 충돌 감지
```python
# 첫 번째 터널
create_tunnel("server.com", 3000, "/api")

# 두 번째 터널 (에러!)
create_tunnel("server.com", 8000, "/api")
# Error: Path '/api' already in use
```

### 3. 와일드카드 지원
```python
# /static/* → /static/css, /static/js 등 모두 포함
create_tunnel("server.com", 3000, "/static/*")

# /api/** → /api/v1/users 같은 하위 경로 모두 포함
create_tunnel("server.com", 8000, "/api/**")
```

### 4. 보안 기능
- 민감정보 자동 마스킹 (auth_token → ****3456)
- 위험한 경로 패턴 차단 (.., ./, ***)
- 안전한 임시 파일 관리

## 🔑 핵심 개념

### 1. FRP의 locations 파라미터
FRP는 `locations` 파라미터로 경로 기반 라우팅을 지원합니다:
```toml
[[proxies]]
name = "web"
type = "http"
customDomains = ["example.com"]
locations = ["/myapp", "/app"]  # 이 경로들로 들어오는 요청만 처리
```

### 2. Pydantic 모델 사용
타입 안전성과 자동 검증을 위해 Pydantic 사용:
```python
class HTTPTunnel(BaseTunnel):
    path: str = Field(..., regex="^/[a-zA-Z0-9/_-]*$")
    local_port: int = Field(..., ge=1, le=65535)
```

### 3. Context Manager 패턴
자동 리소스 정리:
```python
with TunnelManager(config) as manager:
    tunnel = manager.create_http_tunnel(...)
    # 사용
# 자동으로 모든 터널 정리
```

## ❓ 자주 묻는 질문

**Q: FRP 서버는 어떻게 준비하나요?**
A: 별도로 FRP 서버(frps)를 설치하고 실행해야 합니다. FRP Wrapper는 클라이언트(frpc) 부분만 담당합니다.

**Q: ngrok과 뭐가 다른가요?**
A: ngrok은 클라우드 서비스지만, FRP는 자체 서버에서 운영합니다. 더 많은 제어권과 프라이버시를 제공합니다.

**Q: 성능은 어떤가요?**
A: FRP 네이티브 성능과 동일합니다. Python 래퍼는 설정과 프로세스 관리만 담당하고, 실제 데이터 전송은 FRP 바이너리가 처리합니다.

## 다음 단계

각 Checkpoint별 상세 설명:
- [Checkpoint 1: Process Manager](checkpoint-01-process-manager.md)
- [Checkpoint 2: Basic Client](checkpoint-02-basic-client.md)
- [Checkpoint 3: Tunnel Management](checkpoint-03-tunnel-management.md)
- [Checkpoint 4: Path-based Routing](checkpoint-04-path-routing.md)
- [Checkpoint 5: Context Manager](checkpoint-05-context-manager.md)
