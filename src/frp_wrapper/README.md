# FRP Python Wrapper

FRP (Fast Reverse Proxy)를 Python으로 감싸서 사용하기 쉽게 만든 라이브러리입니다.

## 모듈 구조

```
frp_wrapper/
├── api.py      # 고수준 사용자 API (create_tunnel, managed_tunnel 등)
├── client/     # FRP 클라이언트(frpc) 래퍼
├── server/     # FRP 서버(frps) 래퍼
└── common/     # 공통 유틸리티 및 헬퍼
```

## 의존성 방향

```
api ──┬──> client ──> common
      │                ↑
      └──> common      │
                       │
server ────────────────┘
```

- `common`: 독립적 모듈 (다른 frp_wrapper 모듈에 의존하지 않음)
- `client`: common 모듈에만 의존
- `server`: common 모듈에만 의존
- `api`: client와 common 모듈에 의존

## 주요 기능

### API 모듈
- `create_tunnel()`: HTTP 터널을 간단히 생성
- `create_tcp_tunnel()`: TCP 터널을 간단히 생성
- `managed_tunnel()`: Context manager로 터널 관리
- `tunnel_group_context()`: 여러 터널을 그룹으로 관리

### Client 모듈
- FRP 클라이언트(frpc) 프로세스 관리
- 터널 생성, 시작, 중지, 삭제
- TOML 설정 파일 자동 생성
- 연결 상태 모니터링

### Server 모듈
- FRP 서버(frps) 프로세스 관리
- 서버 설정 관리 (포트, 인증, 대시보드)
- TOML 설정 파일 자동 생성

### Common 모듈
- Context Manager 패턴 지원
- 구조화된 로깅 (structlog)
- 커스텀 예외 클래스
- 유틸리티 함수

## 사용 예시

```python
# 고수준 API 사용
from frp_wrapper import create_tunnel

url = create_tunnel("example.com", 3000, "/api")
print(f"터널 생성됨: {url}")

# 저수준 API 사용
from frp_wrapper.client import FRPClient

with FRPClient("example.com") as client:
    tunnel = client.expose_path(3000, "/api")
    # 터널이 자동으로 정리됨
```

## FRP 바이너리

이 라이브러리는 FRP 바이너리(frpc, frps)가 시스템에 설치되어 있어야 합니다.
- frpc: 클라이언트 바이너리
- frps: 서버 바이너리

바이너리는 자동으로 검색되며, 없을 경우 자동 다운로드를 시도합니다.
