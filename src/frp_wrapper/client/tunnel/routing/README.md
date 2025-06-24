# Routing Module

HTTP 터널의 경로 기반 라우팅을 위한 모듈입니다. FRP의 `locations` 기능을 활용하여 하나의 도메인에서 여러 서비스를 경로별로 분리할 수 있습니다.

## 역할

- URL 경로 패턴 분석 및 매칭
- 경로 간 충돌 감지
- 경로 유효성 검증
- 와일드카드 패턴 지원

## 모듈 구조

```
routing/
├── patterns.py    # PathPattern - 경로 패턴 매칭
├── conflicts.py   # PathConflict, PathConflictType 정의
├── detector.py    # PathConflictDetector - 충돌 감지
└── validator.py   # PathValidator - 경로 유효성 검증
```

## 주요 컴포넌트

### PathPattern (patterns.py)

URL 경로 패턴을 분석하고 매칭하는 클래스입니다.

```python
from frp_wrapper.client.tunnel.routing import PathPattern

# 패턴 생성
pattern = PathPattern("/api/v1/*")

# 매칭 확인
pattern.matches("/api/v1/users")     # True
pattern.matches("/api/v2/users")     # False
pattern.matches("/api/v1")          # True (prefix match)

# 패턴 속성
pattern.path           # "/api/v1/*"
pattern.segments       # ["api", "v1", "*"]
pattern.has_wildcard   # True
pattern.specificity    # 2 (구체적인 세그먼트 수)
```

지원하는 패턴:
- 정확한 경로: `/api/users`
- 와일드카드: `/api/*`
- 중첩 와일드카드: `/api/*/docs`

### PathConflictType (conflicts.py)

경로 충돌의 유형을 정의합니다.

```python
class PathConflictType(Enum):
    EXACT_DUPLICATE = "exact_duplicate"      # 완전히 같은 경로
    WILDCARD_OVERLAP = "wildcard_overlap"    # 와일드카드 중복
    PREFIX_CONFLICT = "prefix_conflict"      # 접두사 충돌
```

### PathConflict (conflicts.py)

두 경로 간의 충돌 정보를 담습니다.

```python
@dataclass
class PathConflict:
    path1: str                    # 첫 번째 경로
    path2: str                    # 두 번째 경로
    conflict_type: PathConflictType
    description: str              # 충돌 설명
```

### PathConflictDetector (detector.py)

여러 경로 간의 충돌을 감지합니다.

```python
from frp_wrapper.client.tunnel.routing import PathConflictDetector

detector = PathConflictDetector()

# 단일 경로 검사
conflicts = detector.detect_conflicts("/api/*", [
    "/api/users",    # 충돌: 와일드카드와 중복
    "/api/admin",    # 충돌: 와일드카드와 중복
    "/app"          # OK: 다른 경로
])

# 여러 경로 검사
all_conflicts = detector.check_conflicts([
    "/api/*",
    "/api/v1",      # 충돌
    "/api/v2",      # 충돌
    "/app/*",
    "/app/admin"    # 충돌
])
```

충돌 감지 규칙:
1. **정확한 중복**: 두 경로가 완전히 같음
2. **와일드카드 중복**: 와일드카드가 다른 경로를 포함
3. **접두사 충돌**: 한 경로가 다른 경로의 접두사

### PathValidator (validator.py)

경로의 유효성을 검증합니다.

```python
from frp_wrapper.client.tunnel.routing import PathValidator

validator = PathValidator()

# 유효성 검사
validator.validate_path("/api/users")    # OK
validator.validate_path("")             # ValueError: 빈 경로
validator.validate_path("/admin/")      # ValueError: 후행 슬래시
validator.validate_path("api")          # ValueError: 선행 슬래시 없음

# 예약된 경로 검사
validator.is_reserved("/health")        # True (시스템 예약)
validator.is_reserved("/api")          # False

# 안전한 경로 생성
safe_path = validator.sanitize_path("//api//users/")  # "/api/users"
```

검증 규칙:
- 빈 경로 불허
- 선행 슬래시 필수
- 후행 슬래시 불허
- 연속된 슬래시 불허
- 특수 문자 제한

예약된 경로:
- `/health` - 상태 확인
- `/metrics` - 메트릭스
- `/.well-known` - 웹 표준

## FRP locations 매핑

이 모듈의 경로는 FRP의 `locations` 설정으로 직접 매핑됩니다:

```toml
[[proxies]]
name = "my-service"
type = "http"
localPort = 3000
customDomains = ["example.com"]
locations = ["/api", "/docs"]  # 이 모듈이 관리하는 경로

# 결과 URL:
# - https://example.com/api → localhost:3000/api
# - https://example.com/docs → localhost:3000/docs
```

## 사용 예시

### 경로 충돌 검사 워크플로우
```python
from frp_wrapper.client.tunnel.routing import (
    PathValidator,
    PathConflictDetector,
    PathPattern
)

# 1. 경로 유효성 검사
validator = PathValidator()
try:
    validator.validate_path("/api/v1")
except ValueError as e:
    print(f"잘못된 경로: {e}")

# 2. 기존 경로와 충돌 검사
detector = PathConflictDetector()
existing_paths = ["/api/*", "/admin"]
conflicts = detector.detect_conflicts("/api/users", existing_paths)

if conflicts:
    for conflict in conflicts:
        print(f"충돌 발견: {conflict.description}")
else:
    print("경로 사용 가능")

# 3. 패턴 매칭 확인
pattern = PathPattern("/api/*")
if pattern.matches("/api/users/123"):
    print("이 요청은 터널로 라우팅됩니다")
```

### 터널 그룹의 경로 관리
```python
paths = ["/api", "/admin", "/docs"]
detector = PathConflictDetector()

# 모든 경로 간 충돌 검사
conflicts = detector.check_conflicts(paths)
if not conflicts:
    print("모든 경로가 충돌 없이 사용 가능합니다")

# 우선순위별 정렬 (구체적인 경로 우선)
sorted_paths = sorted(paths,
    key=lambda p: PathPattern(p).specificity,
    reverse=True
)
```

## 성능 고려사항

- 패턴 컴파일은 캐시됨 (`@lru_cache`)
- 경로 정규화는 캐시됨
- 대량의 경로 검사 시 O(n²) 복잡도 주의

## 제한사항

- 정규식 패턴은 지원하지 않음 (FRP가 지원하지 않음)
- 쿼리 스트링은 라우팅에 사용되지 않음
- 대소문자 구분 (case-sensitive)
