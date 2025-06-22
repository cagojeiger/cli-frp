# Checkpoint 4: Path-based Routing - 경로 충돌 감지와 라우팅

## 🎯 목적: 왜 Path Routing이 중요해?

한 서버에서 여러 서비스를 운영하려면:

### 문제점들:
1. **경로 충돌**
   ```python
   # 첫 번째 서비스
   create_tunnel("server.com", 3000, "/api")

   # 두 번째 서비스 (충돌!)
   create_tunnel("server.com", 8000, "/api")  # Error!
   ```

2. **와일드카드 복잡성**
   - `/api/*` vs `/api/v1`?
   - `/static/**` vs `/static/css`?
   - 어느 것이 우선?

3. **보안 문제**
   - `/../../../etc/passwd` 같은 경로
   - 악의적인 패턴 차단 필요

## 📦 구현 내용: 고급 경로 라우팅 시스템

### 핵심: FRP의 locations 파라미터 활용
```toml
# FRP는 locations로 경로 기반 라우팅 지원
[[proxies]]
name = "web01"
type = "http"
localPort = 80
customDomains = ["example.com"]
locations = ["/"]  # 루트 경로

[[proxies]]
name = "web02"
type = "http"
localPort = 81
customDomains = ["example.com"]
locations = ["/api", "/v1"]  # 특정 경로들
```

## 🔧 실제 FRP 라우팅과 비교

### FRP의 경로 매칭 규칙:
1. **정확한 매칭 우선**
   - `/api/users` > `/api/*` > `/*`
2. **긴 경로 우선**
   - `/api/v1/users` > `/api/v1` > `/api`
3. **와일드카드는 마지막**
   - `*`는 한 레벨, `**`는 모든 하위

### FRP Wrapper의 구현:
```python
# 같은 규칙을 Python으로 구현
class PathPattern:
    """경로 패턴 with 와일드카드 지원"""

    def __init__(self, pattern: str):
        self.pattern = pattern
        self.is_wildcard = "*" in pattern
        self.is_recursive = "**" in pattern
        self._regex = self._compile_pattern()

    def _compile_pattern(self) -> Pattern[str]:
        """패턴을 정규식으로 변환"""
        escaped = re.escape(self.pattern)
        # ** → .* (모든 경로)
        escaped = escaped.replace(r"\*\*", ".*")
        # * → [^/]* (/ 제외한 모든 문자)
        escaped = escaped.replace(r"\*", "[^/]*")
        return re.compile(f"^{escaped}$")
```

## 💡 핵심 기능들

### 1. 경로 충돌 감지
```python
class PathConflictDetector:
    """경로 충돌을 감지하는 클래스"""

    def check_conflict(self, new_path: str, existing_paths: list[str]) -> str | None:
        """새 경로가 기존 경로와 충돌하는지 검사"""

        new_pattern = PathPattern(new_path)

        for existing_path in existing_paths:
            existing_pattern = PathPattern(existing_path)

            # 1. 정확히 같은 경로
            if new_path == existing_path:
                return f"Exact match: '{new_path}' already exists"

            # 2. 와일드카드 충돌
            if new_pattern.conflicts_with(existing_pattern):
                return f"Wildcard conflict: '{new_path}' overlaps with '{existing_path}'"

        return None  # 충돌 없음
```

### 2. 와일드카드 패턴 매칭
```python
# 사용 예시
patterns = {
    "/api/*": "API v1 endpoints",
    "/api/v2/*": "API v2 endpoints",
    "/static/**": "All static files",
    "/app": "Exact app route"
}

# 테스트
test_paths = [
    "/api/users",      # → /api/*
    "/api/v2/users",   # → /api/v2/*
    "/static/css/main.css",  # → /static/**
    "/app",            # → /app
    "/app/dashboard"   # → 매칭 없음
]
```

### 3. 보안 검증
```python
@staticmethod
def validate_path(path: str) -> bool:
    """경로 보안 검증"""

    # 위험한 패턴 차단
    dangerous_patterns = [
        "..",           # 디렉토리 탐색
        "./",           # 상대 경로
        "//",           # 이중 슬래시
        "\x00",         # Null 바이트
        "%2e%2e",       # URL 인코딩된 ..
    ]

    for pattern in dangerous_patterns:
        if pattern in path.lower():
            return False

    # 허용된 문자만
    if not re.match(r'^/[a-zA-Z0-9/_*-]*$', path):
        return False

    return True
```

### 4. 경로 정규화
```python
@lru_cache(maxsize=512)  # 성능 최적화
def normalize_path(path: str) -> str:
    """경로 정규화"""

    # 앞뒤 슬래시 제거
    path = path.strip("/")

    # 중복 슬래시 제거
    path = re.sub(r"/+", "/", path)

    # 빈 경로는 루트로
    if not path:
        return ""

    return path
```

## 🔍 실제 사용 예시

### 기본 충돌 감지:
```python
detector = PathConflictDetector()

# 첫 번째 터널
detector.register_path("/api", "tunnel-1")

# 두 번째 터널 (충돌!)
conflict = detector.check_conflict("/api", detector.get_active_paths())
if conflict:
    print(f"❌ {conflict}")
    # Output: Path '/api' conflicts with existing path '/api' (tunnel: tunnel-1)
```

### 와일드카드 라우팅:
```python
# 정적 파일 서버
static_tunnel = manager.create_http_tunnel(
    "static-files",
    local_port=3001,
    path="/static/**"  # 모든 정적 파일
)

# API 서버
api_tunnel = manager.create_http_tunnel(
    "api-server",
    local_port=8000,
    path="/api/*"  # API 엔드포인트
)

# 매칭 테스트
router = PathRouter()
router.add_route("/static/**", static_tunnel)
router.add_route("/api/*", api_tunnel)

print(router.match("/static/css/main.css"))  # → static_tunnel
print(router.match("/api/users"))            # → api_tunnel
print(router.match("/unknown"))              # → None
```

### 복잡한 라우팅 시나리오:
```python
# 여러 서비스를 한 도메인에서 운영
services = [
    # 서비스명, 포트, 경로
    ("frontend", 3000, "/"),           # 기본 경로
    ("api-v1", 8001, "/api/v1/*"),    # API v1
    ("api-v2", 8002, "/api/v2/*"),    # API v2
    ("admin", 8080, "/admin/**"),      # 관리자 (하위 모두)
    ("docs", 3030, "/docs"),           # 문서 (정확히)
    ("static", 3001, "/static/**"),    # 정적 파일
]

# 충돌 없이 모두 등록
for name, port, path in services:
    tunnel = manager.create_http_tunnel(name, port, path)
    print(f"✅ {name}: https://example.com{path}")
```

## 🛡️ 고급 기능들

### 1. 우선순위 기반 라우팅
```python
class RouteTable:
    """우선순위 기반 라우팅 테이블"""

    def __init__(self):
        self.routes: list[tuple[int, PathPattern, Any]] = []

    def add_route(self, path: str, handler: Any):
        pattern = PathPattern(path)

        # 우선순위 계산
        priority = self._calculate_priority(path)

        # 정렬된 위치에 삽입
        bisect.insort(self.routes, (priority, pattern, handler))

    def _calculate_priority(self, path: str) -> int:
        """우선순위 계산 (낮을수록 높은 우선순위)"""
        priority = 0

        if "**" in path:
            priority += 1000  # 재귀 와일드카드는 낮은 우선순위
        elif "*" in path:
            priority += 100   # 일반 와일드카드

        # 경로 깊이 (깊을수록 우선)
        priority -= path.count("/") * 10

        return priority
```

### 2. 캐싱으로 성능 최적화
```python
# LRU 캐시로 컴파일된 패턴 재사용
@lru_cache(maxsize=64)
def _compile_pattern_cached(pattern: str) -> Pattern[str]:
    """패턴 컴파일 결과 캐싱"""
    return _compile_pattern(pattern)

# 경로 정규화 결과 캐싱
@lru_cache(maxsize=512)
def _normalize_path_cached(path: str) -> str:
    """정규화 결과 캐싱"""
    return _normalize_path(path)
```

### 3. 실시간 라우팅 테이블
```python
class RoutingTable:
    """실시간 라우팅 정보 관리"""

    def get_routing_table(self) -> list[dict]:
        """현재 라우팅 테이블 반환"""
        table = []

        for path, tunnel_id in self._active_paths.items():
            tunnel = self._tunnels.get(tunnel_id)
            if tunnel:
                table.append({
                    "path": path,
                    "tunnel_id": tunnel_id,
                    "local_port": tunnel.local_port,
                    "status": tunnel.status,
                    "url": f"https://{tunnel.custom_domains[0]}{path}"
                })

        # 경로 길이로 정렬 (구체적인 경로 우선)
        return sorted(table, key=lambda x: len(x["path"]), reverse=True)
```

## ❓ 자주 묻는 질문

**Q: FRP의 locations와 완전히 같나요?**
A: 네! FRP의 locations 파라미터를 그대로 활용합니다:
```toml
locations = ["/api", "/v1"]  # FRP가 이 경로만 라우팅
```

**Q: 와일드카드 우선순위는?**
A: FRP와 동일하게:
1. 정확한 매칭 (`/api/users`)
2. 긴 경로 (`/api/v1/*` > `/api/*`)
3. 와일드카드 (`*` < `**`)

**Q: 성능은 어때요?**
A:
- 패턴 컴파일 캐싱: 64개
- 경로 정규화 캐싱: 512개
- 대부분의 앱은 10-50개 경로 사용

**Q: 경로 충돌 해결 방법은?**
A:
1. 더 구체적인 경로 사용 (`/api` → `/api/v1`)
2. 다른 서브도메인 사용
3. 포트 기반 라우팅 고려

## 🎓 핵심 배운 점

1. **FRP 네이티브 기능 활용**
   - locations 파라미터로 경로 라우팅
   - 휠 재발명하지 않기

2. **보안이 최우선**
   - 모든 입력 검증
   - 위험한 패턴 사전 차단

3. **성능 최적화**
   - LRU 캐싱 활용
   - 정규식 컴파일 재사용

## 🎉 완성된 기능

이제 완전한 경로 기반 터널링 시스템이 완성되었습니다!

```python
# 최종 사용 예시
from frp_wrapper import create_tunnel

# 한 줄로 터널 생성!
frontend = create_tunnel("example.com", 3000, "/")
api = create_tunnel("example.com", 8000, "/api")
admin = create_tunnel("example.com", 8080, "/admin")

print(f"""
🚀 서비스가 공개되었습니다:
   Frontend: {frontend}
   API:      {api}
   Admin:    {admin}
""")
```

## 다음 단계

Checkpoint 4까지 완성! 이제:
- Context Manager로 자동 리소스 관리 (Checkpoint 5)
- 서버 도구 (Checkpoint 6)
- 모니터링 (Checkpoint 7)
- 예제와 문서 (Checkpoint 8)

가 남아있습니다.
