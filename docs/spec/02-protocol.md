# 프로토콜 및 통신 방식

## 개요

FRP Python Wrapper가 FRP와 통신하는 방식과 서브패스 라우팅을 구현하는 메커니즘을 설명합니다.

## FRP 프로토콜 기본

### FRP 아키텍처
```
┌──────────────┐     Control Connection    ┌──────────────┐
│  FRP Client  │ ←————————————————————————→ │  FRP Server  │
│    (frpc)    │         Port 7000         │    (frps)    │
└──────────────┘                           └──────────────┘
       ↑                                           ↓
       │                                           │
  Local Service                              Public Access
   (localhost)                                (Internet)
```

### 연결 유형

1. **제어 연결 (Control Connection)**
   - 용도: 클라이언트-서버 간 제어 명령 전송
   - 프로토콜: TCP
   - 기본 포트: 7000
   - 지속성: 항상 유지

2. **데이터 연결 (Data Connection)**
   - 용도: 실제 트래픽 전송
   - 프로토콜: TCP/UDP/HTTP(S)
   - 포트: 동적 할당
   - 지속성: 요청별 생성/종료

## 서브패스 라우팅 구현

### 문제점
FRP는 기본적으로 서브도메인 방식만 지원합니다:
- ✅ 지원: `app.example.com`
- ❌ 미지원: `example.com/app`

### 해결 방안

#### 1. 가상 호스트 매핑
```
URL 경로 → 가상 호스트 → FRP vhost → 로컬 서비스
/myapp/* → myapp.local → frpc → localhost:3000
```

#### 2. Nginx 통합
```nginx
# Nginx가 경로를 가상 호스트로 변환
location ~ ^/myapp/(.*) {
    proxy_set_header Host myapp.local;
    proxy_pass http://localhost:8080;
}
```

#### 3. FRP 설정
```ini
[myapp]
type = http
local_port = 3000
custom_domains = myapp.local
```

### 전체 흐름
```
1. 사용자 요청: https://example.com/myapp/index.html
                          ↓
2. Nginx 처리: Host 헤더를 myapp.local로 변경
                          ↓
3. FRP Server: Host 헤더 기반 라우팅 (포트 8080)
                          ↓
4. FRP Client: myapp.local → localhost:3000
                          ↓
5. 로컬 서비스: 요청 처리 및 응답
```

## 설정 파일 프로토콜

### INI 파일 형식
FRP는 INI 형식의 설정 파일을 사용합니다.

#### 클라이언트 설정 (frpc.ini)
```ini
# 공통 설정
[common]
server_addr = tunnel.example.com
server_port = 7000
token = authentication_token

# TCP 터널
[ssh]
type = tcp
local_ip = 127.0.0.1
local_port = 22
remote_port = 2222

# HTTP 터널 (서브도메인)
[web]
type = http
local_port = 3000
subdomain = myapp

# HTTP 터널 (커스텀 도메인)
[api]
type = http
local_port = 8000
custom_domains = api.mycompany.com

# HTTP 터널 (가상 호스트 - 서브패스용)
[webapp]
type = http
local_port = 3000
custom_domains = webapp.local
```

#### 서버 설정 (frps.ini)
```ini
[common]
bind_port = 7000
vhost_http_port = 8080
vhost_https_port = 8443
dashboard_port = 7500
dashboard_user = admin
dashboard_pwd = admin
token = authentication_token

# 포트 범위 설정
allow_ports = 2000-3000,3001,3003,4000-50000
```

### 동적 설정 업데이트

FRP는 실행 중 설정 변경을 지원하지 않으므로, Python Wrapper는 다음 방식을 사용합니다:

1. **설정 변경 감지**
   ```python
   def _update_config_and_restart(self):
       # 1. 새 설정 파일 생성
       new_config = self._config_builder.build()
       config_path = self._write_temp_config(new_config)
       
       # 2. 프로세스 재시작
       self._process_manager.restart(config_path)
       
       # 3. 터널 상태 복원
       self._restore_tunnel_states()
   ```

2. **무중단 업데이트 시도**
   - 새 프로세스 시작
   - 연결 확인
   - 기존 프로세스 종료
   - 실패 시 롤백

## 프로세스 통신

### 프로세스 출력 파싱

FRP 프로세스는 표준 출력으로 상태 정보를 제공합니다:

```
[2024-01-01 10:00:00] [I] [service] frpc service started
[2024-01-01 10:00:01] [I] [proxy] [web] proxy started
[2024-01-01 10:00:02] [I] [proxy] [web] get a new work connection
[2024-01-01 10:00:03] [E] [proxy] [api] connect to local service error
```

#### 로그 파싱 패턴
```python
LOG_PATTERNS = {
    'started': re.compile(r'\[(.+?)\] \[I\] \[proxy\] \[(.+?)\] proxy started'),
    'error': re.compile(r'\[(.+?)\] \[E\] \[proxy\] \[(.+?)\] (.+)'),
    'connection': re.compile(r'\[(.+?)\] \[I\] \[proxy\] \[(.+?)\] get a new work connection'),
    'traffic': re.compile(r'\[(.+?)\] \[I\] \[traffic\] \[(.+?)\] in:(\d+) out:(\d+)')
}
```

### 상태 모니터링

1. **프로세스 상태**
   ```python
   def is_running(self) -> bool:
       return self.process is not None and self.process.poll() is None
   ```

2. **터널 상태**
   - 로그 출력에서 "proxy started" 확인
   - 주기적 헬스체크
   - 연결 테스트

## HTTP 헤더 처리

### 요청 헤더

서브패스 라우팅 시 추가되는 헤더:

```http
Host: myapp.local                    # FRP 라우팅용
X-Real-IP: 192.168.1.100            # 실제 클라이언트 IP
X-Forwarded-For: 192.168.1.100      # 프록시 체인
X-Forwarded-Proto: https            # 원본 프로토콜
X-Original-URI: /myapp/api/users    # 원본 요청 경로
X-Forwarded-Path: /myapp            # 서브패스
```

### 응답 헤더 처리

경로 재작성이 필요한 경우:

```python
def rewrite_response_headers(headers: Dict[str, str], base_path: str) -> Dict[str, str]:
    """응답 헤더의 경로 재작성"""
    
    # Location 헤더 재작성 (리다이렉트)
    if 'Location' in headers:
        location = headers['Location']
        if location.startswith('/'):
            headers['Location'] = f"{base_path}{location}"
    
    # Set-Cookie 경로 재작성
    if 'Set-Cookie' in headers:
        headers['Set-Cookie'] = rewrite_cookie_path(
            headers['Set-Cookie'], 
            base_path
        )
    
    return headers
```

## WebSocket 지원

### WebSocket 프로토콜 업그레이드

```http
GET /myapp/ws HTTP/1.1
Host: myapp.local
Upgrade: websocket
Connection: upgrade
Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==
Sec-WebSocket-Version: 13
```

### FRP WebSocket 설정

```ini
[websocket_app]
type = http
local_port = 3000
custom_domains = ws.local
# WebSocket은 자동으로 지원됨
```

### Nginx WebSocket 프록시

```nginx
location ~ ^/myapp/(.*) {
    proxy_pass http://localhost:8080;
    proxy_http_version 1.1;
    
    # WebSocket 헤더
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
}

# Connection 헤더 맵
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}
```

## 보안 프로토콜

### 인증 방식

1. **토큰 기반 인증**
   ```ini
   [common]
   token = secure_random_token
   ```

2. **TLS 암호화**
   ```ini
   [common]
   tls_enable = true
   tls_cert_file = /path/to/cert.pem
   tls_key_file = /path/to/key.pem
   ```

### 접근 제어

1. **IP 화이트리스트**
   ```python
   options = {
       'allowed_ips': ['192.168.1.0/24', '10.0.0.0/8']
   }
   ```

2. **포트 제한**
   ```ini
   [common]
   allow_ports = 2000-3000,8080,8443
   ```

## 성능 최적화

### 연결 풀링
FRP는 내부적으로 연결 풀을 관리합니다:

```ini
[common]
pool_count = 10  # 연결 풀 크기
```

### 압축
```ini
[tunnel_name]
use_compression = true
compression_level = 6  # 1-9
```

### 암호화
```ini
[tunnel_name]
use_encryption = true
```

## 에러 처리 프로토콜

### 재연결 메커니즘

```python
class ReconnectionStrategy:
    def __init__(self):
        self.attempts = 0
        self.base_delay = 1.0
        self.max_delay = 60.0
    
    def next_delay(self) -> float:
        """지수 백오프"""
        delay = min(
            self.base_delay * (2 ** self.attempts),
            self.max_delay
        )
        self.attempts += 1
        return delay
    
    def reset(self):
        self.attempts = 0
```

### 에러 복구

1. **프로세스 충돌**
   - 자동 재시작
   - 터널 상태 복원
   - 이벤트 알림

2. **네트워크 단절**
   - 재연결 시도
   - 큐잉된 요청 처리
   - 타임아웃 관리

## 메트릭 수집 프로토콜

### 트래픽 통계
FRP는 주기적으로 트래픽 통계를 출력합니다:

```
[2024-01-01 10:00:00] [I] [traffic] [web] in:1048576 out:2097152
```

### 메트릭 파싱 및 집계

```python
@dataclass
class TrafficMetric:
    timestamp: datetime
    tunnel_id: str
    bytes_in: int
    bytes_out: int
    
def parse_traffic_log(line: str) -> Optional[TrafficMetric]:
    match = TRAFFIC_PATTERN.match(line)
    if match:
        return TrafficMetric(
            timestamp=parse_timestamp(match.group(1)),
            tunnel_id=match.group(2),
            bytes_in=int(match.group(3)),
            bytes_out=int(match.group(4))
        )
    return None
```

## 확장 프로토콜

### 플러그인 시스템 (향후)
```python
class ProtocolPlugin:
    """커스텀 프로토콜 플러그인 인터페이스"""
    
    def on_tunnel_create(self, tunnel: Tunnel) -> None:
        """터널 생성 시 호출"""
    
    def on_data_received(self, data: bytes) -> bytes:
        """데이터 수신 시 호출 (변환 가능)"""
    
    def on_data_send(self, data: bytes) -> bytes:
        """데이터 전송 시 호출 (변환 가능)"""
```