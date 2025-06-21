# 빠른 시작 가이드

5분 안에 첫 터널을 만들어보세요!

## 설치

### pip를 사용한 설치
```bash
pip install frp-wrapper
```

### 소스에서 설치
```bash
git clone https://github.com/yourusername/frp-wrapper.git
cd frp-wrapper
pip install -e .
```

## 첫 번째 터널 만들기

### 1. 가장 간단한 예제

로컬에서 실행 중인 웹 서비스를 외부에 공개해보겠습니다.

```python
from frp_wrapper import create_client, quick_tunnel

# 방법 1: 빠른 터널 생성 (함수형 접근)
result = quick_tunnel("tunnel.example.com", 3000, "myapp")

match result:
    case Ok(url):
        print(f"🎉 터널이 생성되었습니다!")
        print(f"🔗 접속 URL: {url}")
        input("Enter 키를 누르면 터널이 종료됩니다...")
    case Err(error):
        print(f"❌ 터널 생성 실패: {error}")
```

### 2. 클라이언트를 사용한 터널 관리

```python
from frp_wrapper import create_client

# FRP 서버에 연결
client_result = create_client("tunnel.example.com")

match client_result:
    case Ok(client):
        # 로컬 3000번 포트를 공개
        tunnel_result = client.expose_path(3000, "myapp")
        
        match tunnel_result:
            case Ok(tunnel):
                print(f"🎉 터널이 생성되었습니다!")
                print(f"🔗 접속 URL: {tunnel.url}")
                input("Enter 키를 누르면 터널이 종료됩니다...")
                
                # 터널 종료
                client.close_tunnel(tunnel.id)
            case Err(error):
                print(f"❌ 터널 생성 실패: {error}")
                
        # 연결 해제
        disconnect_client(client)
    case Err(error):
        print(f"❌ 연결 실패: {error}")
```

### 3. Context Manager 사용

리소스를 자동으로 정리하는 더 안전한 방법입니다.

```python
from frp_wrapper import temporary_tunnel

# 임시 터널 생성 (자동 정리)
with temporary_tunnel("tunnel.example.com", 3000, "myapp") as tunnel:
    print(f"🔗 접속 URL: {tunnel.url}")
    input("Enter 키를 누르면 터널이 종료됩니다...")
# 자동으로 모든 리소스가 정리됩니다
```

### 4. 여러 서비스 동시 노출

```python
from frp_wrapper import create_client, pipe
from frp_wrapper.types import Ok, Err

client_result = create_client("tunnel.example.com")

match client_result:
    case Ok(client):
        # 여러 터널을 파이프라인으로 생성
        tunnels = []
        
        # 프론트엔드
        frontend_result = client.expose_path(3000, "app")
        if frontend_result.is_ok():
            frontend = frontend_result.unwrap()
            print(f"프론트엔드: {frontend.url}")
            tunnels.append(frontend)
        
        # API 서버
        api_result = client.expose_path(8000, "api", strip_path=False)
        if api_result.is_ok():
            api = api_result.unwrap()
            print(f"API: {api.url}")
            tunnels.append(api)
        
        # 관리자 패널
        admin_result = client.expose_path(3001, "admin")
        if admin_result.is_ok():
            admin = admin_result.unwrap()
            print(f"관리자: {admin.url}")
            tunnels.append(admin)
        
        input("Enter 키를 누르면 모든 터널이 종료됩니다...")
        
        # 모든 터널 종료
        for tunnel in tunnels:
            client.close_tunnel(tunnel.id)
    case Err(error):
        print(f"❌ 연결 실패: {error}")
```

## 함수형 프로그래밍 패턴

### 1. Result 타입을 사용한 에러 처리

```python
from frp_wrapper import create_client
from frp_wrapper.types import Ok, Err

def setup_tunnel(server: str, port: int, path: str) -> Result[str, str]:
    """터널을 설정하고 URL을 반환"""
    return create_client(server).flat_map(
        lambda client: client.expose_path(port, path)
    ).map(
        lambda tunnel: tunnel.url
    )

# 사용
result = setup_tunnel("tunnel.example.com", 3000, "myapp")

match result:
    case Ok(url):
        print(f"터널 URL: {url}")
    case Err(error):
        print(f"에러: {error}")
```

### 2. 파이프라인을 사용한 터널 생성

```python
from frp_wrapper import pipe, create_client
from frp_wrapper.pipelines import flat_map_result, map_result

# 터널 생성 파이프라인
tunnel_pipeline = pipe(
    lambda _: create_client("tunnel.example.com"),
    flat_map_result(lambda c: c.expose_path(3000, "myapp")),
    map_result(lambda t: {
        "id": t.id,
        "url": t.url,
        "status": t.status
    })
)

result = tunnel_pipeline(None)

match result:
    case Ok(info):
        print(f"터널 정보: {info}")
    case Err(error):
        print(f"에러: {error}")
```

## 일반적인 사용 사례

### 1. React 개발 서버 공유

```python
from frp_wrapper import temporary_tunnel
import subprocess

# React 개발 서버 시작
subprocess.Popen(["npm", "start"], cwd="./my-react-app")

# WebSocket 지원으로 Hot Reload 가능
with temporary_tunnel(
    "tunnel.example.com", 
    3000, 
    "react-dev",
    websocket=True
) as tunnel:
    print(f"📱 React 앱: {tunnel.url}")
    print("✨ Hot Reload가 지원됩니다!")
    input("개발이 끝나면 Enter를 누르세요...")
```

### 2. Webhook 테스트

```python
from frp_wrapper import temporary_tunnel
from flask import Flask, request
import threading

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    print(f"Webhook 수신: {request.json}")
    return "OK", 200

# Flask 서버 시작 (별도 스레드)
server = threading.Thread(target=lambda: app.run(port=5000))
server.daemon = True
server.start()

# 터널 생성
with temporary_tunnel("tunnel.example.com", 5000, "webhook-test") as tunnel:
    print(f"🪝 Webhook URL: {tunnel.url}webhook")
    print("이 URL을 GitHub, Stripe 등에 등록하세요!")
    input("테스트가 끝나면 Enter를 누르세요...")
```

### 3. TCP 터널 (SSH 접속)

```python
from frp_wrapper import create_client

client_result = create_client("tunnel.example.com")

match client_result:
    case Ok(client):
        # SSH 포트 노출
        ssh_result = client.expose_tcp(22, remote_port=2222)
        
        match ssh_result:
            case Ok(tunnel):
                print(f"🖥️  SSH 접속 명령어:")
                print(f"ssh -p 2222 user@{client.server.host}")
                input("Enter 키를 누르면 종료됩니다...")
                client.close_tunnel(tunnel.id)
            case Err(error):
                print(f"❌ SSH 터널 생성 실패: {error}")
    case Err(error):
        print(f"❌ 연결 실패: {error}")
```

## 설정 옵션

### 인증 사용

```python
from frp_wrapper import create_client

client_result = create_client(
    server="tunnel.example.com",
    auth_token="your_secure_token"  # 서버와 동일한 토큰
)
```

### 사용자 정의 헤더

```python
tunnel_result = client.expose_path(
    local_port=3000,
    path="api",
    custom_headers={
        "X-API-Version": "2.0",
        "X-Custom-Header": "value"
    }
)
```

### Rate Limiting

```python
tunnel_result = client.expose_path(
    local_port=8000,
    path="api",
    rate_limit="10r/s"  # 초당 10개 요청으로 제한
)
```

## 함수형 에러 처리

### Result 타입을 활용한 안전한 에러 처리

```python
from frp_wrapper import create_client, sequence
from frp_wrapper.types import Ok, Err

def create_multiple_tunnels(server: str, ports: List[int]) -> Result[List[Tunnel], str]:
    """여러 터널을 한 번에 생성"""
    
    def create_tunnel_for_port(client, port):
        return client.expose_path(port, f"app-{port}")
    
    return create_client(server).flat_map(
        lambda client: sequence([
            create_tunnel_for_port(client, port)
            for port in ports
        ])
    )

# 사용
result = create_multiple_tunnels("tunnel.example.com", [3000, 3001, 3002])

match result:
    case Ok(tunnels):
        for tunnel in tunnels:
            print(f"터널 생성됨: {tunnel.url}")
    case Err(error):
        print(f"터널 생성 실패: {error}")
```

### 기본값을 사용한 에러 처리

```python
from frp_wrapper import create_client

# 실패 시 기본값 사용
client_result = create_client("tunnel.example.com")
url = client_result.flat_map(
    lambda c: c.expose_path(3000, "app")
).map(
    lambda t: t.url
).unwrap_or("http://localhost:3000")  # 실패 시 로컬 URL 사용

print(f"앱 URL: {url}")
```

## 다음 단계

- 📖 [상세 설치 가이드](01-installation.md) - 다양한 환경에서의 설치 방법
- 🔧 [기본 사용법](02-basic-usage.md) - 더 많은 예제와 옵션
- 🚀 [고급 사용법](03-advanced-usage.md) - 프로덕션 환경 설정
- 🛠️ [문제 해결](04-troubleshooting.md) - 일반적인 문제와 해결책
- 🎯 [함수형 프로그래밍 가이드](architecture/functional-design.md) - 함수형 패턴 상세 설명

## 도움 받기

문제가 있거나 기능 요청이 있으시면:
- 📝 [GitHub Issues](https://github.com/yourusername/frp-wrapper/issues)
- 💬 [Discussions](https://github.com/yourusername/frp-wrapper/discussions)
- 📧 support@example.com