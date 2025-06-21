# 설정 파일 명세

## 개요

FRP Python Wrapper의 설정 파일 형식과 옵션을 정의합니다. 사용자는 YAML, JSON, Python 코드 등 다양한 방식으로 설정할 수 있습니다.

## 설정 방식

### 1. 코드 기반 설정 (권장)
```python
from frp_wrapper import FRPClient

client = FRPClient(
    server="tunnel.example.com",
    port=7000,
    auth_token="your_secure_token",
    base_url="https://tunnel.example.com",
    auto_reconnect=True,
    reconnect_interval=30
)
```

### 2. YAML 설정 파일
```yaml
# config.yaml
client:
  server: tunnel.example.com
  port: 7000
  auth_token: ${FRP_AUTH_TOKEN}  # 환경 변수 지원
  base_url: https://tunnel.example.com
  options:
    auto_reconnect: true
    reconnect_interval: 30
    log_level: info

tunnels:
  - name: frontend
    type: http
    local_port: 3000
    path: app
    options:
      strip_path: true
      websocket: true
      
  - name: api
    type: http
    local_port: 8000
    path: api/v1
    options:
      strip_path: false
      custom_headers:
        X-API-Version: "1.0"
        
  - name: ssh
    type: tcp
    local_port: 22
    remote_port: 2222
```

### 3. JSON 설정 파일
```json
{
  "client": {
    "server": "tunnel.example.com",
    "port": 7000,
    "auth_token": "${FRP_AUTH_TOKEN}",
    "base_url": "https://tunnel.example.com",
    "options": {
      "auto_reconnect": true,
      "reconnect_interval": 30,
      "log_level": "info"
    }
  },
  "tunnels": [
    {
      "name": "frontend",
      "type": "http",
      "local_port": 3000,
      "path": "app",
      "options": {
        "strip_path": true,
        "websocket": true
      }
    }
  ]
}
```

### 4. 환경 변수
```bash
export FRP_SERVER=tunnel.example.com
export FRP_PORT=7000
export FRP_AUTH_TOKEN=your_secure_token
export FRP_LOG_LEVEL=debug
```

## 설정 옵션 상세

### 클라이언트 설정

#### 필수 옵션
| 옵션 | 타입 | 설명 | 기본값 |
|------|------|------|--------|
| `server` | string | FRP 서버 주소 (도메인 또는 IP) | 필수 |

#### 선택 옵션
| 옵션 | 타입 | 설명 | 기본값 |
|------|------|------|--------|
| `port` | int | FRP 서버 포트 | 7000 |
| `auth_token` | string | 인증 토큰 | None |
| `base_url` | string | 터널 URL 베이스 | `https://{server}` |
| `binary_path` | string | frpc 바이너리 경로 | 자동 탐색 |
| `auto_reconnect` | bool | 자동 재연결 활성화 | true |
| `reconnect_interval` | int | 재연결 간격 (초) | 30 |
| `log_level` | string | 로그 레벨 (debug/info/warning/error) | info |
| `config_dir` | string | 설정 파일 디렉토리 | `~/.frp_wrapper` |
| `timeout` | int | 연결 타임아웃 (초) | 10 |
| `max_retries` | int | 최대 재시도 횟수 | 3 |
| `pool_count` | int | 연결 풀 크기 | 10 |
| `tls_enable` | bool | TLS 암호화 사용 | false |
| `tls_cert_file` | string | TLS 인증서 파일 | None |
| `tls_key_file` | string | TLS 키 파일 | None |

### 터널 설정

#### 공통 옵션
| 옵션 | 타입 | 설명 | 기본값 |
|------|------|------|--------|
| `name` | string | 터널 이름 (자동 생성 가능) | `tunnel_{uuid}` |
| `type` | string | 터널 타입 (tcp/udp/http/https) | 필수 |
| `local_port` | int | 로컬 포트 | 필수 |
| `local_ip` | string | 로컬 IP 주소 | 127.0.0.1 |

#### TCP/UDP 터널 옵션
| 옵션 | 타입 | 설명 | 기본값 |
|------|------|------|--------|
| `remote_port` | int | 원격 포트 | 자동 할당 |
| `allowed_ips` | list | 허용 IP 목록 | [] (모두 허용) |

#### HTTP/HTTPS 터널 옵션
| 옵션 | 타입 | 설명 | 기본값 |
|------|------|------|--------|
| `subdomain` | string | 서브도메인 | None |
| `custom_domains` | list | 커스텀 도메인 목록 | [] |
| `path` | string | URL 경로 (서브패스) | None |
| `strip_path` | bool | 프록시 시 경로 제거 | true |
| `websocket` | bool | WebSocket 지원 | true |
| `locations` | list | URL 경로 목록 | ["/"] |
| `host_header_rewrite` | string | Host 헤더 재작성 | None |
| `custom_headers` | dict | 추가 HTTP 헤더 | {} |
| `basic_auth` | string | 기본 인증 (user:pass) | None |
| `rate_limit` | string | 요청 제한 (예: "10r/s") | None |
| `rewrite_rules` | list | URL 재작성 규칙 | [] |

#### 고급 옵션
| 옵션 | 타입 | 설명 | 기본값 |
|------|------|------|--------|
| `use_encryption` | bool | 데이터 암호화 | false |
| `use_compression` | bool | 데이터 압축 | false |
| `compression_level` | int | 압축 레벨 (1-9) | 6 |
| `bandwidth_limit` | string | 대역폭 제한 (예: "1MB") | None |
| `proxy_protocol_version` | string | 프록시 프로토콜 버전 | None |

## 설정 파일 로드

### 자동 로드 순서
1. 환경 변수
2. 현재 디렉토리의 `.frp_wrapper.yaml`
3. 홈 디렉토리의 `~/.frp_wrapper/config.yaml`
4. `/etc/frp_wrapper/config.yaml` (Linux/Mac)
5. 명시적으로 지정된 파일

### 설정 파일 로드 예제
```python
from frp_wrapper import FRPClient, load_config

# 자동 로드
client = FRPClient.from_config()

# 특정 파일 로드
config = load_config("my_config.yaml")
client = FRPClient(**config['client'])

# 여러 파일 병합
config = load_config(["base.yaml", "override.yaml"])
```

## 서버 측 설정

### Nginx 설정 생성
```python
from frp_wrapper.server import NginxConfigBuilder

builder = NginxConfigBuilder("tunnel.example.com")
builder.set_ssl("/etc/ssl/cert.pem", "/etc/ssl/key.pem")

# 터널 경로 추가
builder.add_path("app", "app.local", {
    "strip_path": True,
    "websocket": True,
    "rate_limit": "10r/s"
})

builder.add_path("api", "api.local", {
    "strip_path": False,
    "custom_headers": {
        "X-API-Gateway": "FRP"
    }
})

# 설정 생성
nginx_config = builder.build()
builder.write_config("/etc/nginx/sites-available/frp-tunnel")
```

### FRP 서버 설정 생성
```python
from frp_wrapper.server import FRPServerConfig

config = FRPServerConfig()
config.set_auth("secure_token")
config.set_dashboard(7500, "admin", "password")
config.add_allowed_ports([2000, 3000])
config.add_allowed_ports(range(8000, 9000))

# frps.ini 생성
ini_content = config.generate_ini()
with open("/etc/frp/frps.ini", "w") as f:
    f.write(ini_content)

# systemd 서비스 생성
service = config.generate_systemd_service()
with open("/etc/systemd/system/frps.service", "w") as f:
    f.write(service)
```

## 설정 검증

### 스키마 검증
```python
from frp_wrapper.config import validate_config

config = {
    "client": {
        "server": "example.com",
        "port": "not_a_number"  # 오류!
    }
}

errors = validate_config(config)
if errors:
    for error in errors:
        print(f"설정 오류: {error}")
```

### 런타임 검증
```python
client = FRPClient("example.com")

# 연결 테스트
if not client.test_connection():
    print("서버에 연결할 수 없습니다")

# 포트 사용 가능 확인
if not client.is_port_available(3000):
    print("포트 3000이 이미 사용 중입니다")
```

## 설정 예제

### 개발 환경
```yaml
# dev.yaml
client:
  server: dev-tunnel.company.local
  port: 7000
  auth_token: dev_token
  options:
    log_level: debug
    auto_reconnect: true

tunnels:
  - name: react-dev
    type: http
    local_port: 3000
    path: frontend
    options:
      websocket: true  # Hot reload 지원
      strip_path: true
      custom_headers:
        Cache-Control: "no-cache"
```

### 프로덕션 환경
```yaml
# prod.yaml
client:
  server: tunnel.company.com
  port: 7000
  auth_token: ${PROD_FRP_TOKEN}
  options:
    log_level: warning
    auto_reconnect: true
    reconnect_interval: 60
    tls_enable: true
    tls_cert_file: /etc/ssl/client.crt
    tls_key_file: /etc/ssl/client.key

tunnels:
  - name: api-gateway
    type: http
    local_port: 8000
    path: api
    options:
      strip_path: false
      rate_limit: "100r/s"
      allowed_ips:
        - 10.0.0.0/8
        - 172.16.0.0/12
      basic_auth: ${API_BASIC_AUTH}
      custom_headers:
        X-API-Version: "2.0"
        Strict-Transport-Security: "max-age=31536000"
```

### 다중 서비스
```yaml
# microservices.yaml
client:
  server: api.example.com
  port: 7000
  auth_token: ${FRP_TOKEN}

tunnels:
  # 인증 서비스
  - name: auth-service
    type: http
    local_port: 3001
    path: api/auth
    options:
      strip_path: false
      custom_headers:
        X-Service: "auth"
  
  # 사용자 서비스
  - name: user-service
    type: http
    local_port: 3002
    path: api/users
    options:
      strip_path: false
      custom_headers:
        X-Service: "users"
  
  # 주문 서비스
  - name: order-service
    type: http
    local_port: 3003
    path: api/orders
    options:
      strip_path: false
      custom_headers:
        X-Service: "orders"
  
  # 관리자 SSH
  - name: admin-ssh
    type: tcp
    local_port: 22
    remote_port: 2222
    options:
      allowed_ips:
        - 192.168.1.0/24
```

## 설정 마이그레이션

### FRP 설정에서 마이그레이션
```python
from frp_wrapper.config import migrate_from_frp

# 기존 frpc.ini 파일을 YAML로 변환
old_config = "/etc/frp/frpc.ini"
new_config = migrate_from_frp(old_config, format="yaml")

with open("config.yaml", "w") as f:
    f.write(new_config)
```

### ngrok 설정에서 마이그레이션
```python
from frp_wrapper.config import migrate_from_ngrok

# ngrok 설정을 FRP Wrapper 설정으로 변환
ngrok_config = """
tunnels:
  app:
    proto: http
    addr: 3000
    subdomain: myapp
"""

frp_config = migrate_from_ngrok(ngrok_config)
```

## 보안 권장사항

1. **토큰 관리**
   - 환경 변수 사용
   - 설정 파일에 직접 저장 금지
   - 정기적 토큰 교체

2. **접근 제어**
   - IP 화이트리스트 설정
   - 기본 인증 사용
   - Rate limiting 적용

3. **암호화**
   - 프로덕션에서 TLS 필수
   - 민감한 데이터는 암호화 옵션 사용

4. **권한 관리**
   - 설정 파일 권한: 600
   - 실행 사용자 제한
   - 로그 파일 접근 제한