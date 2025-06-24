# FRP Client Module

FRP 클라이언트(frpc) 바이너리를 제어하고 터널을 관리하는 모듈입니다.

## 역할

- frpc 프로세스 생명주기 관리
- HTTP/TCP 터널 생성 및 관리
- TOML 설정 파일 동적 생성
- 연결 상태 모니터링
- 경로 기반 라우팅 및 충돌 감지

## 모듈 구조

```
client/
├── client.py    # FRPClient 메인 클래스
├── process.py   # ProcessManager - frpc 프로세스 관리
├── config.py    # ConfigBuilder - TOML 설정 생성
├── tunnel.py    # 터널 모델 및 관리 (추후 tunnel/ 디렉토리로 분리 예정)
└── group.py     # TunnelGroup - 터널 그룹 관리
```

## 주요 컴포넌트

### FRPClient (client.py)
메인 진입점으로 모든 기능을 조율합니다.

```python
from frp_wrapper.client import FRPClient

# Context manager 사용
with FRPClient("example.com", auth_token="secret") as client:
    # HTTP 터널 생성
    tunnel = client.expose_path(3000, "/api")

    # TCP 터널 생성
    tcp_tunnel = client.expose_tcp(22, remote_port=2222)
```

### ProcessManager (process.py)
frpc 프로세스의 생명주기를 관리합니다.

- 프로세스 시작/중지/재시작
- 프로세스 상태 모니터링
- 로그 캡처 및 분석
- 비정상 종료 감지

### ConfigBuilder (config.py)
frpc용 TOML 설정 파일을 생성합니다.

```toml
# 생성되는 설정 예시
serverAddr = "example.com"
serverPort = 7000
auth.method = "token"
auth.token = "secret"

[[proxies]]
name = "http-3000-api"
type = "http"
localPort = 3000
customDomains = ["example.com"]
locations = ["/api"]
```

### TunnelManager (tunnel.py)
터널의 생명주기와 레지스트리를 관리합니다.

- 터널 생성/시작/중지/삭제
- 터널 상태 추적
- 경로 충돌 감지
- 터널별 프로세스 관리

### TunnelGroup (group.py)
여러 터널을 그룹으로 관리합니다.

```python
from frp_wrapper.client import TunnelGroup

group = TunnelGroup(client)
group.add_http_tunnel(3000, "/api")
group.add_http_tunnel(3001, "/admin")
group.start_all()  # 모든 터널 시작
```

## FRP 제어 부분

### 프로세스 실행
```bash
# ProcessManager가 실행하는 명령
frpc -c /tmp/frpc_xxxx.toml
```

### 설정 파일 관리
- 임시 디렉토리에 TOML 파일 생성
- 프로세스 종료 시 자동 정리
- 동적 설정 업데이트 지원

### 연결 상태 확인
- 로그 파싱을 통한 연결 상태 감지
- "login to server success" 메시지 확인
- 에러 메시지 분석

## 의존성

- `../common/context.py` - Context Manager 믹스인
- `../common/exceptions.py` - 커스텀 예외 클래스
- `../common/logging.py` - 구조화된 로깅
- `../common/utils.py` - 유틸리티 함수

## 사용 예시

### 기본 사용
```python
client = FRPClient("example.com")
client.connect()
tunnel = client.expose_path(3000, "/app")
# ... 사용 ...
client.disconnect()
```

### Context Manager 사용
```python
with FRPClient("example.com") as client:
    tunnel = client.expose_path(3000, "/app")
    # 자동으로 정리됨
```

### 터널 그룹 사용
```python
with client.tunnel_group() as group:
    group.add_http_tunnel(3000, "/api")
    group.add_tcp_tunnel(22)
    group.start_all()
```
