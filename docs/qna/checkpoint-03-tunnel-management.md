# Checkpoint 3: Tunnel Management - HTTP/TCP 터널 만들기

## 🎯 목적: 왜 Tunnel 모델이 필요해?

FRPClient로 서버에 연결했지만, 실제 터널을 만들려면:

### 문제점들:
1. **복잡한 프록시 설정**
   ```toml
   [[proxies]]
   name = "web"
   type = "http"
   localPort = 3000
   customDomains = ["example.com"]
   locations = ["/myapp"]
   # 더 많은 옵션들...
   ```

2. **터널 타입별 다른 설정**
   - HTTP: domains, paths, headers
   - TCP: remote port, bind addr
   - 각각 다른 옵션과 검증 규칙

3. **터널 생명주기 관리**
   - 생성, 시작, 중지, 삭제
   - 상태 추적
   - 여러 터널 동시 관리

## 📦 구현 내용: Pydantic 기반 터널 모델

### 왜 Pydantic을 사용했나?
```python
# 일반 클래스
class HTTPTunnel:
    def __init__(self, local_port, path, domain):
        if not (1 <= local_port <= 65535):
            raise ValueError("Invalid port")
        if not path.startswith("/"):
            raise ValueError("Path must start with /")
        # 더 많은 검증...

# Pydantic 클래스
class HTTPTunnel(BaseModel):
    local_port: int = Field(ge=1, le=65535)
    path: str = Field(regex="^/[a-zA-Z0-9/_-]*$")
    domain: str = Field(min_length=1)
    # 자동 검증!
```

## 🔧 실제 FRP 프록시 설정과 비교

### 기존 FRP 설정 (frpc.toml):
```toml
# HTTP 프록시
[[proxies]]
name = "web"
type = "http"
localPort = 3000
customDomains = ["example.com"]
locations = ["/myapp"]
hostHeaderRewrite = "localhost"
headers.X-From = "frp"

# TCP 프록시
[[proxies]]
name = "database"
type = "tcp"
localPort = 5432
remotePort = 15432
```

### FRP Wrapper 모델:
```python
# HTTP 터널
tunnel = HTTPTunnel(
    id="web",
    local_port=3000,
    path="/myapp",
    custom_domains=["example.com"],
    host_header_rewrite="localhost",
    headers={"X-From": "frp"}
)

# TCP 터널
tunnel = TCPTunnel(
    id="database",
    local_port=5432,
    remote_port=15432
)
```

## 💡 핵심 모델 구조

### 1. 기본 터널 모델 (Base)
```python
class TunnelStatus(str, Enum):
    """터널 상태"""
    PENDING = "pending"          # 생성됨, 시작 전
    CONNECTING = "connecting"    # 연결 중
    CONNECTED = "connected"      # 활성 상태
    DISCONNECTED = "disconnected"  # 연결 끊김
    ERROR = "error"             # 오류 발생
    CLOSED = "closed"           # 종료됨

class BaseTunnel(BaseModel):
    """모든 터널의 기본 클래스"""

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(..., min_length=1, max_length=50)
    tunnel_type: TunnelType
    local_port: int = Field(..., ge=1, le=65535)
    status: TunnelStatus = Field(default=TunnelStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator('id')
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """ID 형식 검증"""
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError("ID must be alphanumeric with - or _")
        return v
```

### 2. HTTP 터널 모델
```python
class HTTPTunnel(BaseTunnel):
    """HTTP/HTTPS 터널"""

    tunnel_type: Literal[TunnelType.HTTP] = TunnelType.HTTP

    # 경로 기반 라우팅 (핵심!)
    path: str = Field(..., description="URL path like /myapp")
    custom_domains: list[str] = Field(..., min_items=1)

    # HTTP 전용 옵션
    subdomain: str | None = None
    host_header_rewrite: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    basic_auth: tuple[str, str] | None = None

    # 고급 옵션
    enable_websocket: bool = True
    enable_compression: bool = False

    @field_validator('path')
    @classmethod
    def validate_path_format(cls, v: str) -> str:
        """경로 형식 검증"""
        if not v:
            return ""

        # 위험한 패턴 차단
        if ".." in v or "./" in v:
            raise ValueError("Path cannot contain '..' or './'")

        # 정규식 검증
        if not re.match(r'^/[a-zA-Z0-9/_*-]*$', v):
            raise ValueError("Invalid path format")

        return v.strip('/')  # 앞뒤 / 제거
```

### 3. TCP 터널 모델
```python
class TCPTunnel(BaseTunnel):
    """TCP/UDP 터널"""

    tunnel_type: Literal[TunnelType.TCP] = TunnelType.TCP

    # TCP 전용 옵션
    remote_port: int = Field(..., ge=1, le=65535)
    bind_addr: str = Field(default="0.0.0.0")

    # 프록시 프로토콜
    proxy_protocol_version: str | None = None

    @property
    def endpoint(self) -> str:
        """접속 주소 반환"""
        return f"{self.bind_addr}:{self.remote_port}"
```

### 4. 터널 매니저
```python
class TunnelManager:
    """터널 생명주기 관리"""

    def __init__(self, config: TunnelConfig):
        self.config = config
        self._tunnels: dict[str, BaseTunnel] = {}
        self._process_manager = TunnelProcessManager(config)

    def create_http_tunnel(
        self,
        tunnel_id: str,
        local_port: int,
        path: str,
        **options
    ) -> HTTPTunnel:
        """HTTP 터널 생성"""

        # 1. 경로 충돌 검사
        self._check_path_conflict(path)

        # 2. 터널 모델 생성 (Pydantic 자동 검증)
        tunnel = HTTPTunnel(
            id=tunnel_id,
            local_port=local_port,
            path=path,
            custom_domains=options.get('custom_domains', [self.config.default_domain]),
            **options
        )

        # 3. 등록
        self._tunnels[tunnel_id] = tunnel

        return tunnel

    def start_tunnel(self, tunnel_id: str) -> bool:
        """터널 시작"""
        tunnel = self._tunnels.get(tunnel_id)
        if not tunnel:
            raise ValueError(f"Tunnel {tunnel_id} not found")

        # FRP 설정 생성
        config = self._generate_frp_config(tunnel)

        # 프로세스 시작
        if self._process_manager.start_tunnel_process(tunnel_id, config):
            tunnel.status = TunnelStatus.CONNECTED
            return True

        return False
```

## 🔍 실제 사용 예시

### HTTP 터널 생성:
```python
from frp_wrapper import TunnelManager, TunnelConfig

# 설정
config = TunnelConfig(
    server_host="example.com",
    auth_token="secret",
    default_domain="example.com"
)

# 매니저 생성
manager = TunnelManager(config)

# HTTP 터널 생성
tunnel = manager.create_http_tunnel(
    tunnel_id="my-web-app",
    local_port=3000,
    path="/myapp",
    host_header_rewrite="localhost:3000",
    headers={"X-Source": "frp-wrapper"}
)

# 시작
if manager.start_tunnel(tunnel.id):
    print(f"✅ 터널 시작됨: https://{tunnel.custom_domains[0]}/{tunnel.path}/")
```

### TCP 터널 생성:
```python
# PostgreSQL 터널
db_tunnel = manager.create_tcp_tunnel(
    tunnel_id="postgres",
    local_port=5432,
    remote_port=15432
)

manager.start_tunnel(db_tunnel.id)
print(f"✅ DB 접속: {config.server_host}:{db_tunnel.remote_port}")
```

### 여러 터널 동시 관리:
```python
# 프론트엔드, API, 관리자 패널
tunnels = [
    ("frontend", 3000, "/app"),
    ("api", 8000, "/api"),
    ("admin", 8080, "/admin")
]

for tunnel_id, port, path in tunnels:
    tunnel = manager.create_http_tunnel(tunnel_id, port, path)
    manager.start_tunnel(tunnel.id)
    print(f"✅ {tunnel_id}: https://example.com{path}/")

# 모든 터널 상태 확인
for tunnel in manager.list_tunnels():
    print(f"{tunnel.id}: {tunnel.status}")
```

## 🛡️ Pydantic의 장점

### 1. 자동 검증
```python
# 잘못된 포트
try:
    tunnel = HTTPTunnel(id="test", local_port=99999, path="/test")
except ValidationError as e:
    print(e)
    # local_port: ensure this value is less than or equal to 65535

# 잘못된 경로
try:
    tunnel = HTTPTunnel(id="test", local_port=3000, path="../hack")
except ValidationError as e:
    print(e)
    # path: Path cannot contain '..'
```

### 2. 타입 안전성
```python
# IDE가 타입을 알고 있음
tunnel = manager.create_http_tunnel("test", 3000, "/app")
tunnel.local_port  # IDE: int
tunnel.path        # IDE: str
tunnel.unknown     # IDE: 에러!
```

### 3. 직렬화/역직렬화
```python
# JSON으로 변환
json_data = tunnel.model_dump_json()

# JSON에서 복원
tunnel2 = HTTPTunnel.model_validate_json(json_data)

# 설정 파일로 저장/로드 가능
```

## ❓ 자주 묻는 질문

**Q: 왜 터널마다 별도 프로세스?**
A: FRP는 각 프록시를 독립적으로 관리할 수 있어서:
- 하나가 죽어도 다른 터널은 영향 없음
- 개별 시작/중지 가능
- 리소스 격리

**Q: locations 파라미터는 뭐야?**
A: FRP의 핵심 기능으로, HTTP 라우팅 경로를 지정:
```toml
locations = ["/myapp", "/app"]  # 이 경로로 오는 요청만 처리
```

**Q: 경로 충돌은 어떻게 감지해?**
A: PathConflictDetector가 처리 (다음 checkpoint에서 자세히)

**Q: subdomain vs customDomains?**
A:
- subdomain: `test.example.com` 같은 서브도메인
- customDomains: `mysite.com` 같은 완전한 도메인

## 🎓 핵심 배운 점

1. **모델 기반 설계의 장점**
   - 명확한 데이터 구조
   - 자동 검증
   - 문서화 용이

2. **Pydantic의 강력함**
   - 선언적 검증
   - 타입 안전성
   - 직렬화 지원

3. **터널 생명주기 관리**
   - 상태 기계 패턴
   - 명확한 전환 규칙

## 🚧 현재 한계점

터널은 만들어졌지만, 같은 경로에 여러 터널이 생기면 충돌합니다. 이를 해결하려면 경로 라우팅 시스템이 필요합니다.

## 다음 단계

경로 기반 라우팅으로 한 서버에서 여러 서비스를 깔끔하게 관리해봅시다.

→ [Checkpoint 4: Path-based Routing - 경로 충돌 감지와 라우팅](checkpoint-04-path-routing.md)
