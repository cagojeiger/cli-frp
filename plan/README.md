# FRP Python Wrapper 프로젝트 계획

## 프로젝트 개요

Python에서 FRP(Fast Reverse Proxy)를 쉽게 사용할 수 있도록 하는 래퍼 라이브러리입니다. 특히 로컬 서비스를 고정 도메인의 서브패스로 노출하는 기능에 중점을 둡니다.

## 프로젝트 목표

1. **쉬운 사용성**: Python 개발자가 터널링을 직관적으로 사용
2. **서브패스 라우팅**: `https://tunnel.example.com/myapp/` 형태로 서비스 노출
3. **프로그래밍 방식 제어**: 설정 파일이 아닌 코드로 터널 관리
4. **자동 리소스 관리**: Context Manager를 통한 안전한 터널 생명주기 관리

## 핵심 기능

- FRP 프로세스 자동 관리
- 동적 터널 생성/삭제
- 서브패스 기반 라우팅
- WebSocket 지원
- 자동 재연결
- 구조화된 로깅

## 기술 스택

- **언어**: Python 3.11+
- **모델링**: Pydantic v2
- **프로세스 관리**: subprocess
- **설정 생성**: TOML
- **테스트**: pytest + hypothesis
- **의존성 관리**: uv
- **타입 체킹**: mypy (strict mode)
- **코드 품질**: ruff + pre-commit

## 프로젝트 구조

```
prototype-frp/
├── frp_wrapper/        # 메인 라이브러리
├── examples/           # 사용 예제
├── tests/              # 테스트 코드
├── server_setup/       # 서버 설정 도구
├── docs/               # 사용자 문서
└── plan/               # 프로젝트 계획
```

## 개발 상황

### ✅ 완료된 Phase (Checkpoint 1-4)
- ✅ Checkpoint 1: FRP 프로세스 관리 (ProcessManager)
- ✅ Checkpoint 2: 기본 클라이언트 API (FRPClient, ConfigBuilder)
- ✅ Checkpoint 3: 터널 생성/삭제 (TunnelManager, Pydantic models)
- ✅ Checkpoint 4: 서브패스 라우팅 (Native FRP locations)

### 🔧 구현된 핵심 기능
- Protocol 패턴으로 순환 의존성 해결
- 95%+ 테스트 커버리지 달성
- Context Manager 지원
- 고수준 API (create_tunnel, create_tcp_tunnel)

### 🚀 향후 확장 가능 기능
- CLI 인터페이스
- TUI 인터페이스
- 서버 설정 도구
- 모니터링 대시보드

## 달성된 성공 기준

1. **기능적 완성도** ✅
   - ✅ 모든 핵심 기능 구현 완료
   - ✅ 95% 이상 테스트 커버리지 달성
   - ✅ 주요 사용 사례 예제 제공

2. **사용성** ✅
   - ✅ 한 줄로 터널 생성 가능: `create_tunnel("domain", port, "/path")`
   - ✅ 직관적인 객체지향 API
   - ✅ 명확한 에러 메시지와 타입 힌트

3. **안정성** ✅
   - ✅ Context Manager로 자동 리소스 정리
   - ✅ Pydantic으로 데이터 검증
   - ✅ 포괄적인 예외 처리

## 참고 문서

- [아키텍처 설계](01-architecture.md)
- [구현 계획](02-implementation.md)
- [마일스톤](03-milestones.md)
