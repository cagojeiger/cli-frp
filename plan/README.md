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

- **언어**: Python 3.8+
- **비동기**: asyncio (선택적)
- **프로세스 관리**: subprocess
- **설정**: YAML/JSON
- **테스트**: pytest
- **문서**: Sphinx

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

## 개발 일정

### Phase 1: 기초 구현 (2주)
- Checkpoint 1: FRP 프로세스 관리
- Checkpoint 2: 기본 클라이언트 API
- Checkpoint 3: 터널 생성/삭제

### Phase 2: 핵심 기능 (2주)
- Checkpoint 4: 서브패스 라우팅
- Checkpoint 5: Context Manager 지원

### Phase 3: 프로덕션 준비 (1주)
- Checkpoint 6: 서버 설정 도구
- Checkpoint 7: 모니터링 및 로깅
- Checkpoint 8: 예제 및 문서

## 성공 기준

1. **기능적 완성도**
   - 모든 핵심 기능 구현
   - 95% 이상 테스트 커버리지
   - 주요 사용 사례 예제 제공

2. **사용성**
   - 5분 안에 첫 터널 생성 가능
   - 직관적인 API
   - 명확한 에러 메시지

3. **안정성**
   - 자동 재연결
   - 리소스 누수 없음
   - 예외 상황 처리

## 참고 문서

- [아키텍처 설계](01-architecture.md)
- [구현 계획](02-implementation.md)
- [마일스톤](03-milestones.md)