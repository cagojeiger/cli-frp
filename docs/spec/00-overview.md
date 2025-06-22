# FRP Python Wrapper - 프로젝트 개요

## 소개

FRP Python Wrapper는 [FRP(Fast Reverse Proxy)](https://github.com/fatedier/frp)를 Python에서 쉽게 사용할 수 있도록 만든 고수준 API 라이브러리입니다. 복잡한 설정 파일 작성 없이 Python 코드로 터널을 생성하고 관리할 수 있습니다.

## 핵심 개념

### 터널링(Tunneling)
터널링은 NAT나 방화벽 뒤에 있는 로컬 서비스를 공개 인터넷에서 접근 가능하게 만드는 기술입니다.

```
[로컬 서비스] → [FRP Client] → [인터넷] → [FRP Server] → [외부 사용자]
```

### 서브패스 라우팅
기존 FRP는 서브도메인 방식(`app.example.com`)을 주로 지원하지만, 이 프로젝트는 서브패스 방식(`example.com/app`)을 중점적으로 지원합니다.

```
https://tunnel.example.com/frontend/ → localhost:3000
https://tunnel.example.com/api/     → localhost:8000
https://tunnel.example.com/admin/   → localhost:3001
```

## 주요 특징

### 1. Pythonic API
```python
# 기존 FRP (설정 파일 필요)
# frpc.ini 파일 작성, 수정, 재시작...

# FRP Python Wrapper
with FRPClient("tunnel.example.com") as client:
    with client.tunnel(3000, "myapp") as tunnel:
        print(f"URL: {tunnel.url}")
```

### 2. 동적 터널 관리
- 실행 중 터널 추가/제거
- 설정 파일 자동 생성
- 프로세스 생명주기 관리

### 3. 서브패스 기반 라우팅
- 하나의 도메인으로 여러 서비스 노출
- Nginx와의 통합
- 경로 기반 라우팅 규칙

### 4. 자동 리소스 관리
- Context Manager 지원
- 예외 발생 시 자동 정리
- 메모리 누수 방지

### 5. 모니터링 및 로깅
- 구조화된 로깅
- 실시간 터널 상태 추적
- 메트릭 수집 및 알림

## 사용 사례

### 개발 환경 공유
로컬에서 개발 중인 웹 애플리케이션을 팀원이나 클라이언트와 실시간으로 공유할 수 있습니다.

### Webhook 테스트
GitHub, Stripe 등 외부 서비스의 webhook을 로컬 환경에서 직접 받아 테스트할 수 있습니다.

### 마이크로서비스 통합
여러 마이크로서비스를 하나의 도메인 아래 다른 경로로 노출하여 API Gateway처럼 사용할 수 있습니다.

### IoT 디바이스 접근
NAT 뒤에 있는 라즈베리파이 등 IoT 디바이스에 안전하게 원격 접근할 수 있습니다.

## 아키텍처

### 컴포넌트 구조
```
┌─────────────────────────────────────────────┐
│            FRP Python Wrapper               │
├─────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────────────┐ │
│  │  FRPClient  │  │   ProcessManager     │ │
│  │             │  │                      │ │
│  │ - connect() │  │ - start()           │ │
│  │ - expose_*  │  │ - stop()            │ │
│  │ - tunnels   │  │ - monitor()         │ │
│  └──────┬──────┘  └──────────┬───────────┘ │
│         │                     │             │
│  ┌──────┴──────┐  ┌──────────┴───────────┐ │
│  │   Tunnel    │  │   ConfigBuilder      │ │
│  │             │  │                      │ │
│  │ - status    │  │ - add_tunnel()      │ │
│  │ - url       │  │ - build()           │ │
│  │ - close()   │  │ - write_config()    │ │
│  └─────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────┘
                        │
                        ↓
              ┌─────────────────┐
              │   FRP Binary    │
              │   (frpc/frps)   │
              └─────────────────┘
```

### 데이터 흐름
1. **터널 생성 요청**: Python API 호출
2. **설정 생성**: ConfigBuilder가 INI 파일 생성
3. **프로세스 관리**: ProcessManager가 FRP 실행
4. **상태 추적**: Tunnel 객체가 상태 관리
5. **이벤트 처리**: 연결, 해제, 오류 등 이벤트 발생

## 기존 솔루션과의 차이점

### vs 순수 FRP
- **설정 관리**: 코드로 동적 관리 vs 정적 설정 파일
- **사용성**: Python API vs CLI/설정 파일
- **통합성**: Python 애플리케이션과 직접 통합

### vs ngrok
- **자체 호스팅**: 자체 서버 운영 가능
- **비용**: 무료로 무제한 사용
- **커스터마이징**: 완전한 제어 가능

### vs localtunnel
- **안정성**: FRP 기반으로 더 안정적
- **기능**: TCP, UDP 등 다양한 프로토콜 지원
- **성능**: 더 나은 성능과 낮은 지연시간

## 프로젝트 목표

### 단기 목표 (v1.0)
- ✅ 기본 터널링 기능
- ✅ 서브패스 라우팅
- ✅ Context Manager 지원
- ✅ 기본 모니터링

### 중기 목표 (v2.0)
- 🔄 비동기 API 지원
- 🔄 웹 기반 관리 UI
- 🔄 플러그인 시스템
- 🔄 고급 보안 기능

### 장기 목표
- 🔮 Kubernetes 통합
- 🔮 분산 터널링
- 🔮 자동 스케일링
- 🔮 엔터프라이즈 기능

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자유롭게 사용, 수정, 배포할 수 있습니다.

## 기여

프로젝트에 기여하고 싶으신 분들은 [기여 가이드](../contributing.md)를 참조해 주세요.
