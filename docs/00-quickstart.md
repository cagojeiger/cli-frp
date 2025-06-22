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
from frp_wrapper import FRPClient

# 로컬 서비스(포트 3000)를 인터넷에 공개
client = FRPClient("your-server.com", auth_token="your-token")
client.connect()

tunnel = client.expose_path(3000, "myapp")
print(f"🌐 공개 URL: {tunnel.url}")
# 출력: https://your-server.com/myapp/

input("종료하려면 Enter...")
tunnel.close()
client.disconnect()
```

### Context Manager로 더 간단하게

```python
from frp_wrapper import FRPClient

with FRPClient("your-server.com", auth_token="your-token") as client:
    tunnel = client.expose_path(3000, "myapp")
    print(f"🔗 URL: {tunnel.url}")
    input("종료하려면 Enter...")
# 자동으로 모든 리소스 정리됨
```

### 여러 서비스 동시 노출

개발, 스테이징, API 서버를 한번에 공개:

```python
from frp_wrapper import FRPClient

with FRPClient("your-server.com") as client:
    # 프론트엔드 (React/Vue 등)
    frontend = client.expose_path(3000, "app")

    # API 서버
    api = client.expose_path(8000, "api")

    # 관리자 패널
    admin = client.expose_path(8080, "admin")

    print("🚀 서비스가 공개되었습니다:")
    print(f"   Frontend: {frontend.url}")
    print(f"   API:      {api.url}")
    print(f"   Admin:    {admin.url}")

    input("모든 서비스를 종료하려면 Enter...")
```

## 실제 사용 사례

### 웹 개발자 시나리오

React 앱을 동료나 클라이언트와 즉시 공유:

```python
# dev_share.py
from frp_wrapper import FRPClient

with FRPClient("demo.yourcompany.com") as client:
    # React 개발 서버
    app = client.expose_path(3000, "demo")
    print(f"🎨 데모 사이트: {app.url}")

    # Storybook 컴포넌트 라이브러리
    storybook = client.expose_path(6006, "storybook")
    print(f"📚 컴포넌트: {storybook.url}")

    print("\n✨ 팀과 링크를 공유하세요!")
    input("개발이 끝나면 Enter...")
```

### API 개발자 시나리오

FastAPI 개발 서버를 팀과 공유:

```python
# api_share.py
from frp_wrapper import FRPClient

with FRPClient("api.yourcompany.com") as client:
    # FastAPI 개발 서버
    api = client.expose_path(8000, "v1")
    print(f"🔌 API 엔드포인트: {api.url}")
    print(f"📖 API 문서: {api.url}docs")

    # PostgreSQL 개발 DB (TCP)
    db = client.expose_tcp(5432)
    print(f"🗄️  DB 연결: {db.endpoint}")

    input("개발 완료 후 Enter...")
```

### TCP 서비스 공유

데이터베이스나 SSH 서버 공유:

```python
from frp_wrapper import FRPClient

with FRPClient("your-server.com") as client:
    # PostgreSQL
    postgres = client.expose_tcp(5432)
    print(f"🐘 PostgreSQL: {postgres.endpoint}")

    # Redis
    redis = client.expose_tcp(6379)
    print(f"🔴 Redis: {redis.endpoint}")

    # SSH 서버
    ssh = client.expose_tcp(22)
    print(f"🔐 SSH: {ssh.endpoint}")

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
from frp_wrapper import load_config

config = load_config("tunnels.yaml")
config.start_all()  # 모든 터널 시작
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
