# 빠른 시작 가이드

3분 안에 첫 터널을 만들어보세요! 🚀

## 설치

```bash
pip install frp-wrapper
```

## 첫 번째 터널 만들기

### 1분만에 웹앱 공유하기

로컬에서 개발 중인 웹앱을 즉시 공유할 수 있습니다:

```python
from frp_wrapper import create_tunnel

# 로컬 서비스(포트 3000)를 인터넷에 공개
url = create_tunnel("your-server.com", 3000, "/myapp")
print(f"🌐 공개 URL: {url}")
# 출력: https://your-server.com/myapp/

input("종료하려면 Enter...")
```

### 고급 사용법: FRPClient 직접 사용

더 많은 제어가 필요한 경우 FRPClient를 직접 사용할 수 있습니다:

```python
from frp_wrapper import FRPClient, TunnelManager, TunnelConfig

# 설정 생성
config = TunnelConfig(
    server_host="your-server.com",
    auth_token="your-token",
    default_domain="your-server.com"
)

# 터널 매니저로 관리
with TunnelManager(config) as manager:
    tunnel = manager.create_http_tunnel(
        tunnel_id="myapp",
        local_port=3000,
        path="/myapp"
    )
    manager.start_tunnel(tunnel.id)
    print(f"🔗 URL: https://your-server.com/myapp/")
    input("종료하려면 Enter...")
# 자동으로 모든 리소스 정리됨
```

### 여러 서비스 동시 노출

개발, 스테이징, API 서버를 한번에 공개:

```python
from frp_wrapper import TunnelManager, TunnelConfig

config = TunnelConfig(
    server_host="your-server.com",
    auth_token="your-token",
    default_domain="your-server.com"
)

with TunnelManager(config) as manager:
    # 프론트엔드 (React/Vue 등)
    frontend = manager.create_http_tunnel("frontend", 3000, "/app")
    manager.start_tunnel(frontend.id)

    # API 서버
    api = manager.create_http_tunnel("api", 8000, "/api")
    manager.start_tunnel(api.id)

    # 관리자 패널
    admin = manager.create_http_tunnel("admin", 8080, "/admin")
    manager.start_tunnel(admin.id)

    print("🚀 서비스가 공개되었습니다:")
    print(f"   Frontend: https://your-server.com/app/")
    print(f"   API:      https://your-server.com/api/")
    print(f"   Admin:    https://your-server.com/admin/")

    input("모든 서비스를 종료하려면 Enter...")
```

## 실제 사용 사례

### 웹 개발자 시나리오

React 앱을 동료나 클라이언트와 즉시 공유:

```python
# dev_share.py
from frp_wrapper import create_tunnel

# React 개발 서버
app_url = create_tunnel("demo.yourcompany.com", 3000, "/demo")
print(f"🎨 데모 사이트: {app_url}")

# Storybook 컴포넌트 라이브러리
storybook_url = create_tunnel("demo.yourcompany.com", 6006, "/storybook")
print(f"📚 컴포넌트: {storybook_url}")

print("\n✨ 팀과 링크를 공유하세요!")
input("개발이 끝나면 Enter...")
```

### API 개발자 시나리오

FastAPI 개발 서버를 팀과 공유:

```python
# api_share.py
from frp_wrapper import create_tunnel, create_tcp_tunnel

# FastAPI 개발 서버
api_url = create_tunnel("api.yourcompany.com", 8000, "/v1")
print(f"🔌 API 엔드포인트: {api_url}")
print(f"📖 API 문서: {api_url}docs")

# PostgreSQL 개발 DB (TCP)
db_endpoint = create_tcp_tunnel("api.yourcompany.com", 5432)
print(f"🗄️  DB 연결: {db_endpoint}")

input("개발 완료 후 Enter...")
```

### TCP 서비스 공유

데이터베이스나 SSH 서버 공유:

```python
from frp_wrapper import create_tcp_tunnel

# PostgreSQL
postgres = create_tcp_tunnel("your-server.com", 5432)
print(f"🐘 PostgreSQL: {postgres}")

# Redis
redis = create_tcp_tunnel("your-server.com", 6379)
print(f"🔴 Redis: {redis}")

# SSH 서버
ssh = create_tcp_tunnel("your-server.com", 22, remote_port=2222)
print(f"🔐 SSH: {ssh}")

input("서비스 종료하려면 Enter...")
```

## CLI로 더 빠르게

명령줄에서 즉시 터널 생성:

```bash
# HTTP 터널
frp-tunnel --server your-server.com --port 3000 --path myapp

# TCP 터널
frp-tunnel --server your-server.com --tcp 5432

# 설정 파일 사용
frp-tunnel --config tunnels.yaml
```

## 설정 파일 예제

재사용 가능한 터널 설정:

```yaml
# tunnels.yaml
server:
  host: your-server.com
  port: 7000
  auth_token: your-secret-token

tunnels:
  - name: frontend
    local_port: 3000
    path: app

  - name: api
    local_port: 8000
    path: api

  - name: database
    local_port: 5432
    type: tcp
```

```python
# 설정 파일 기반 터널 관리는 향후 지원 예정
# 현재는 Python 코드로 직접 관리
from frp_wrapper import TunnelManager, TunnelConfig

config = TunnelConfig(
    server_host="your-server.com",
    auth_token="your-secret-token"
)
manager = TunnelManager(config)
# 터널 생성 및 관리...
```

## 다음 단계

- 📖 [전체 API 문서](01-installation.md) - 설치 및 상세 설정
- 🔧 [고급 사용법](architecture/domain-model.md) - 프로덕션 배포
- 🐳 [Docker 가이드](../deploy/docker/) - 컨테이너 환경
- 🔒 [보안 설정](../docs/security.md) - 안전한 터널 설정

## 자주 묻는 질문

**Q: 무료로 사용할 수 있나요?**
A: 네! 오픈소스 라이브러리입니다. FRP 서버만 준비하면 됩니다.

**Q: 어떤 서비스와 호환되나요?**
A: HTTP/HTTPS, TCP, UDP 프로토콜을 지원하는 모든 서비스와 호환됩니다.

**Q: 성능은 어떤가요?**
A: FRP 네이티브 성능과 동일합니다. 추가 오버헤드는 거의 없습니다.
