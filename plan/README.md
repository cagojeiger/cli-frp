# FRP Python Wrapper 프로젝트 계획

## 프로젝트 진화
초기: Python FRP 래퍼 → 현재: **K8s 네이티브 분산 서비스 프록시 시스템**

## 현재 상태 (2024년 12월)

### Checkpoint 진행 상황
- **✅ Completed (1-6)**: 기본 FRP Python 래퍼 구현 완료
  - ProcessManager, FRPClient, TunnelManager
  - Context Manager, Pydantic 모델
  - 95%+ 테스트 커버리지 달성

- **🚧 In Progress (12)**: K8s 분산 시스템
  - FRP + K8s + Python 통합 아키텍처
  - 범용 분산 서비스 프록시 (Ollama LLM은 하나의 사용 사례)
  - 기술 연구 문서 작성 중 (docs/research/, docs/k8s/)

- **📋 Planned (7-11)**: 우선순위 재검토 필요
  - 모니터링, CLI/TUI, 문서화 등
  - K8s 통합 완료 후 필요성 재평가

## 핵심 설계 결정

1. **FRP의 역할**: 순수 터널링 인프라로만 활용 (TCP 그룹 로드 밸런싱)
2. **K8s의 역할**: 오케스트레이션, 서비스 디스커버리, 라이프사이클 관리
3. **Python Wrapper**: 두 시스템을 연결하는 브릿지, 설정 자동화

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

## K8s 통합 로드맵 (Checkpoint 12)

### Phase 1: 기본 K8s 배포 (1-2주)
- Docker 이미지 생성
- K8s 매니페스트 (Deployment, Service, ConfigMap)
- 기본 frps/frpc 배포

### Phase 2: CRD & Operator (2-4주)
- DistributedService CRD 구현
- Python Kopf 기반 Operator
- 선언적 서비스 관리

### Phase 3: 자동화 (1-2개월)
- 서비스 디스커버리
- mTLS 인증서 관리
- 동적 설정 업데이트

### Phase 4: 프로덕션 (지속적)
- 모니터링 & 메트릭
- HA 구성
- 성능 최적화

## 참고 문서

- [아키텍처 설계](01-architecture.md)
- [구현 계획](02-implementation.md)
- [마일스톤](03-milestones.md)
