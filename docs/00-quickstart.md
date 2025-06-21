# 빠른 시작 가이드

5분 안에 첫 터널을 만들어보세요!

## 설치

```bash
pip install frp-wrapper
```

## 첫 번째 터널 만들기

### 가장 간단한 방법

```python
from frp_wrapper import create_tunnel

# 로컬 서비스(포트 3000)를 외부에 노출
try:
    url = create_tunnel("example.com", 3000, "/myapp")
    print(f"🔗 접속 URL: {url}")  # https://example.com/myapp/
    input("Enter 키를 누르면 터널이 종료됩니다...")
except Exception as e:
    print(f"❌ 오류: {e}")
```

### 여러 서비스 동시 노출

```python
from frp_wrapper import FRPClient

with FRPClient("example.com") as client:
    # 여러 경로로 서비스 노출
    frontend = client.create_tunnel(3000, "/app")
    api = client.create_tunnel(8000, "/api")
    
    print(f"Frontend: {frontend}")  # https://example.com/app/
    print(f"API: {api}")           # https://example.com/api/
    
    input("Enter 키를 누르면 모든 터널이 종료됩니다...")
# 자동으로 모든 터널 정리
```

## Docker로 빠르게 시작

```yaml
# docker-compose.yml
version: '3'
services:
  app:
    build: .
    environment:
      - FRP_SERVER=tunnel.example.com
      - FRP_PATH=myapp
    ports:
      - "3000:3000"
```

```bash
docker-compose up
```

## 다음 단계

- 📖 [Simple API 가이드](02-simple-api.md) - Python 개발자를 위한 상세 가이드
- 🚀 [Advanced API](03-advanced-api.md) - 함수형 프로그래밍 패턴
- 🔧 [설정 옵션](01-installation.md) - 상세 설치 및 설정 방법