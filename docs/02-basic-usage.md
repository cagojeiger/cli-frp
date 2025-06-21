# 기본 사용법

## FRP Client 생성

### 기본 연결
```python
from frp_wrapper import FRPClient

# 가장 간단한 방법
client = FRPClient("tunnel.example.com")
client.connect()

# 연결 확인
if client.is_connected():
    print("서버에 연결되었습니다!")
```

### 인증과 함께 연결
```python
client = FRPClient(
    server="tunnel.example.com",
    port=7000,
    auth_token="your_secure_token"
)
client.connect()
```

### Context Manager 사용
```python
# 자동 연결 및 해제
with FRPClient("tunnel.example.com") as client:
    # 여기서 터널 작업 수행
    pass
# 자동으로 연결 해제
```

## HTTP 터널 생성

### 서브패스 방식 (권장)
```python
# 로컬 서비스를 https://example.com/myapp/ 으로 노출
tunnel = client.expose_path(
    local_port=3000,
    path="myapp"
)

print(f"접속 URL: {tunnel.url}")
# 출력: https://example.com/myapp/
```

### 서브도메인 방식
```python
# 로컬 서비스를 https://myapp.example.com 으로 노출
tunnel = client.expose_http(
    local_port=3000,
    subdomain="myapp"
)
```

### 커스텀 도메인
```python
# 자체 도메인 사용
tunnel = client.expose_http(
    local_port=3000,
    custom_domains=["app.mycompany.com"]
)
```

## TCP 터널 생성

### 기본 TCP 터널
```python
# SSH 서버 노출
ssh_tunnel = client.expose_tcp(
    local_port=22,
    remote_port=2222
)

print(f"SSH 접속: ssh -p 2222 user@{client.server}")
```

### 자동 포트 할당
```python
# 원격 포트를 자동으로 할당
tunnel = client.expose_tcp(local_port=5432)
print(f"PostgreSQL 접속: {client.server}:{tunnel.config.remote_port}")
```

## 터널 옵션

### strip_path 옵션
```python
# strip_path=True (기본값)
# 요청: https://example.com/api/users
# 로컬: http://localhost:8000/users (경로에서 /api 제거)
tunnel1 = client.expose_path(8000, "api", strip_path=True)

# strip_path=False
# 요청: https://example.com/api/users  
# 로컬: http://localhost:8000/api/users (경로 유지)
tunnel2 = client.expose_path(8000, "api", strip_path=False)
```

### WebSocket 지원
```python
# WebSocket 연결 지원 (기본값: True)
tunnel = client.expose_path(
    local_port=3000,
    path="chat",
    websocket=True
)
```

### 커스텀 헤더
```python
tunnel = client.expose_path(
    local_port=8000,
    path="api",
    custom_headers={
        "X-API-Version": "2.0",
        "X-Service-Name": "user-service",
        "Cache-Control": "no-cache"
    }
)
```

### 접근 제어
```python
# IP 화이트리스트
tunnel = client.expose_path(
    local_port=3000,
    path="admin",
    allowed_ips=[
        "192.168.1.0/24",  # 로컬 네트워크
        "203.0.113.5/32"   # 특정 IP
    ]
)

# 기본 인증
tunnel = client.expose_path(
    local_port=3000,
    path="private",
    basic_auth="admin:password"
)
```

### Rate Limiting
```python
tunnel = client.expose_path(
    local_port=8000,
    path="api",
    rate_limit="10r/s"  # 초당 10개 요청
)
```

## 터널 관리

### 터널 목록 조회
```python
# 모든 활성 터널 조회
tunnels = client.list_tunnels()
for tunnel in tunnels:
    print(f"터널 {tunnel.id}: {tunnel.status}")
    if hasattr(tunnel, 'url'):
        print(f"  URL: {tunnel.url}")
```

### 특정 터널 조회
```python
tunnel = client.get_tunnel(tunnel_id)
if tunnel:
    info = tunnel.get_info()
    print(f"터널 정보: {info}")
```

### 터널 종료
```python
# 개별 터널 종료
tunnel.close()

# 또는 ID로 종료
client.close_tunnel(tunnel_id)

# 모든 터널 종료
client.close_all_tunnels()
```

## 터널 그룹 관리

### TunnelGroup 사용
```python
from frp_wrapper import TunnelGroup

with FRPClient("tunnel.example.com") as client:
    with TunnelGroup(client) as group:
        # 여러 터널을 한 번에 관리
        group.add(3000, "frontend")
        group.add(8000, "backend") 
        group.add(5432)  # TCP 터널
        
        # 모든 터널 정보
        for tunnel in group.tunnels:
            print(f"터널: {tunnel.id}")
```

### 체이닝 방식
```python
with TunnelGroup(client) as group:
    group.add(3000, "app") \
         .add(8000, "api") \
         .add(3001, "admin")
    
    # 작업 수행
    input("Press Enter to close all tunnels...")
```

## 임시 터널

### temporary_tunnel 함수
```python
from frp_wrapper import temporary_tunnel

# 클라이언트 생성부터 터널 종료까지 자동 관리
with temporary_tunnel("tunnel.example.com", 3000, "demo") as tunnel:
    print(f"임시 터널: {tunnel.url}")
    # 사용
# 자동 정리
```

### 클라이언트의 tunnel 메서드
```python
with FRPClient("tunnel.example.com") as client:
    # 임시 HTTP 터널
    with client.tunnel(3000, "temp") as tunnel:
        print(f"URL: {tunnel.url}")
    
    # 임시 TCP 터널
    with client.tunnel(22) as ssh_tunnel:
        print(f"SSH: {ssh_tunnel.endpoint}")
```

## 이벤트 처리

### 이벤트 핸들러 등록
```python
from frp_wrapper import EventType

# 데코레이터 방식
@client.on(EventType.TUNNEL_CONNECTED)
def on_connected(data):
    print(f"터널 연결됨: {data['tunnel_id']}")

@client.on(EventType.TUNNEL_ERROR)
def on_error(data):
    print(f"터널 오류: {data['error']}")

# 함수 방식
def handle_disconnect(data):
    print(f"터널 연결 끊김: {data['tunnel_id']}")

client.on(EventType.TUNNEL_DISCONNECTED, handle_disconnect)
```

### 사용 가능한 이벤트
- `TUNNEL_CREATED`: 터널 생성됨
- `TUNNEL_CONNECTED`: 터널 연결됨
- `TUNNEL_DISCONNECTED`: 터널 연결 끊김
- `TUNNEL_ERROR`: 터널 오류 발생
- `TUNNEL_CLOSED`: 터널 종료됨
- `CLIENT_CONNECTED`: 클라이언트 연결됨
- `CLIENT_DISCONNECTED`: 클라이언트 연결 끊김

## 모니터링

### 터널 메트릭 조회
```python
metrics = client.get_tunnel_metrics(tunnel.id)
if metrics:
    print(f"전송된 바이트: {metrics.bytes_sent}")
    print(f"수신된 바이트: {metrics.bytes_received}")
    print(f"연결 수: {metrics.connection_count}")
    print(f"오류 수: {metrics.error_count}")
```

### 대시보드 시작
```python
# 웹 기반 모니터링 대시보드
client.start_dashboard(port=9999)
print("대시보드: http://localhost:9999")
```

## 에러 처리

### 기본 에러 처리
```python
from frp_wrapper import (
    ConnectionError,
    AuthenticationError,
    TunnelCreationError,
    PortInUseError
)

try:
    client.connect()
except AuthenticationError:
    print("인증 실패: 토큰을 확인하세요")
except ConnectionError as e:
    print(f"연결 실패: {e}")

try:
    tunnel = client.expose_tcp(3000)
except PortInUseError:
    print("포트 3000이 이미 사용 중입니다")
except TunnelCreationError as e:
    print(f"터널 생성 실패: {e}")
```

### 재시도 로직
```python
import time

def create_tunnel_with_retry(client, port, path, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.expose_path(port, path)
        except TunnelCreationError as e:
            if attempt < max_retries - 1:
                print(f"재시도 {attempt + 1}/{max_retries}")
                time.sleep(2 ** attempt)  # 지수 백오프
            else:
                raise
```

## 설정 파일 사용

### YAML 설정 로드
```python
from frp_wrapper import FRPClient

# config.yaml 파일에서 설정 로드
client = FRPClient.from_config("config.yaml")

# 자동으로 설정된 터널 생성
client.create_tunnels_from_config()
```

### 프로그래밍 방식과 설정 파일 혼합
```python
# 기본 설정은 파일에서
client = FRPClient.from_config()

# 추가 터널은 코드로
extra_tunnel = client.expose_path(9000, "extra")
```

## 실제 사용 예제

### Flask 앱 노출
```python
from flask import Flask
from frp_wrapper import FRPClient
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello from Flask!"

# Flask를 백그라운드에서 실행
server = threading.Thread(target=lambda: app.run(port=5000))
server.daemon = True
server.start()

# 터널 생성
with FRPClient("tunnel.example.com") as client:
    with client.tunnel(5000, "flask-demo") as tunnel:
        print(f"Flask 앱: {tunnel.url}")
        input("Enter to stop...")
```

### FastAPI 앱 노출
```python
from fastapi import FastAPI
import uvicorn
from frp_wrapper import FRPClient
import asyncio

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello from FastAPI"}

async def main():
    # Uvicorn 서버 시작
    config = uvicorn.Config(app, host="127.0.0.1", port=8000)
    server = uvicorn.Server(config)
    
    # 백그라운드에서 서버 실행
    asyncio.create_task(server.serve())
    
    # 터널 생성
    with FRPClient("tunnel.example.com") as client:
        with client.tunnel(8000, "api", strip_path=False) as tunnel:
            print(f"FastAPI 문서: {tunnel.url}docs")
            await asyncio.Event().wait()  # 계속 실행

asyncio.run(main())
```

### Jupyter Notebook 노출
```python
from frp_wrapper import FRPClient
import subprocess

# Jupyter 시작 (토큰 비활성화 - 보안 주의!)
jupyter = subprocess.Popen([
    "jupyter", "notebook",
    "--port=8888",
    "--no-browser",
    "--NotebookApp.token=''"
])

with FRPClient("tunnel.example.com") as client:
    # 기본 인증으로 보호
    with client.expose_path(
        8888, 
        "jupyter",
        basic_auth="user:password"
    ) as tunnel:
        print(f"Jupyter Notebook: {tunnel.url}")
        input("Enter to stop...")

jupyter.terminate()
```

## 디버깅

### 로그 레벨 설정
```python
# 상세 로그 출력
client = FRPClient(
    "tunnel.example.com",
    log_level="debug"
)

# 또는 환경 변수로
# export FRP_LOG_LEVEL=debug
```

### 연결 테스트
```python
# 서버 연결 테스트
if client.test_connection():
    print("서버 연결 가능")
else:
    print("서버 연결 불가")

# 포트 사용 가능 확인
if client.is_port_available(3000):
    print("포트 3000 사용 가능")
```

### 프로세스 상태 확인
```python
# 내부 프로세스 상태
if client._process_manager.is_running():
    output = client._process_manager.get_output()
    errors = client._process_manager.get_errors()
    print(f"출력: {output}")
    print(f"에러: {errors}")
```

## 다음 단계

- 🚀 [고급 사용법](03-advanced-usage.md) - 프로덕션 환경 설정
- 🔐 [보안 가이드](../spec/04-security.md) - 보안 설정 방법
- 🛠️ [문제 해결](04-troubleshooting.md) - 일반적인 문제 해결