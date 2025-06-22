# Checkpoint 5: Context Manager - 자동 정리와 안전한 터널 관리

## 🎯 목적: 왜 Context Manager가 필요해?

터널을 만들고 사용한 뒤에는 반드시 정리해야 합니다. 하지만...

### 문제점들:
1. **수동 정리는 까먹기 쉬움**
   ```python
   # 터널 생성
   client = FRPClient("example.com")
   client.connect()
   tunnel = client.expose_path(3000, "/app")

   # 작업...

   # 어? 정리하는 걸 까먹었네! 😱
   ```

2. **예외 발생시 정리 안 됨**
   ```python
   client = FRPClient("example.com")
   client.connect()

   # 에러 발생! 🔥
   raise Exception("뭔가 잘못됐어!")

   # 이 코드는 실행 안 됨
   client.disconnect()  # 리소스 누수!
   ```

3. **try-finally는 번거로움**
   ```python
   client = None
   try:
       client = FRPClient("example.com")
       client.connect()
       # 작업...
   finally:
       if client:
           client.disconnect()  # 너무 복잡해!
   ```

## 📦 구현 내용: Python의 with 문 마법

Context Manager는 이 모든 걸 자동으로 처리합니다:

```python
# ✨ 깔끔하고 안전한 코드
with FRPClient("example.com") as client:
    tunnel = client.expose_path(3000, "/app")
    # 작업...
# 자동으로 정리됨! 예외가 발생해도 OK

# 더 간단하게
with managed_tunnel("example.com", 3000, "/app") as url:
    print(f"앱 주소: {url}")
    # 사용...
# 자동으로 모든 게 정리됨
```

## 🔧 실제 Context Manager 비교

### 기존 방식 (위험함):
```python
# 1. 모든 걸 수동으로
client = FRPClient("example.com")
tunnel = None

try:
    client.connect()
    tunnel = client.expose_path(3000, "/app")

    # 작업 수행
    response = requests.get(f"https://example.com/app")

    # 수동으로 정리
    if tunnel:
        client.close_tunnel(tunnel.id)
    client.disconnect()

except Exception as e:
    # 에러 처리도 복잡
    print(f"에러: {e}")
    if tunnel:
        try:
            client.close_tunnel(tunnel.id)
        except:
            pass
    try:
        client.disconnect()
    except:
        pass
```

### Context Manager 방식 (안전함):
```python
# 모든 게 자동!
with managed_tunnel("example.com", 3000, "/app") as url:
    response = requests.get(url)
    # 에러가 발생해도 자동 정리됨
```

## 💡 핵심 기능들

### 1. 자동 연결/해제
```python
class FRPClient:
    def __enter__(self):
        """with 문 진입시 자동 실행"""
        if not self.is_connected():
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """with 문 종료시 자동 실행 (예외 발생해도!)"""
        # 모든 터널 정리
        for tunnel in self.list_tunnels():
            self.close_tunnel(tunnel.id)

        # 연결 해제
        if self.is_connected():
            self.disconnect()
```

### 2. 예외 안전성 보장
```python
# 예외가 발생해도 정리됨
with FRPClient("example.com") as client:
    tunnel = client.expose_path(3000, "/app")

    # 여기서 에러 발생!
    raise ValueError("뭔가 잘못됨")

# __exit__이 호출되어 모든 리소스 정리됨 ✅
```

### 3. 중첩 Context Manager
```python
# 여러 레벨의 자동 관리
with FRPClient("example.com") as client:
    with client.tunnel_group("my-services") as group:
        group.add_http_tunnel(3000, "/web")
        group.add_http_tunnel(8000, "/api")
        group.add_tcp_tunnel(5432)

        # 모든 터널 사용
        print("서비스들이 실행 중...")

    # group의 터널들이 자동 정리됨
# client도 자동 정리됨
```

### 4. 간편한 임시 터널
```python
# 한 줄로 터널 생성하고 자동 정리
with managed_tunnel("example.com", 3000, "/demo") as url:
    print(f"데모 사이트: {url}")
    input("엔터를 누르면 종료...")
# 터널 자동 정리됨
```

## 🔍 실제 사용 예시

### 단일 터널 관리:
```python
# 웹 서버 임시 공개
with managed_tunnel("myserver.com", 8080, "/preview") as url:
    print(f"🌐 미리보기 URL: {url}")

    # 동료에게 URL 공유
    send_slack_message(f"PR 미리보기: {url}")

    # 피드백 기다리기
    time.sleep(300)  # 5분

print("✅ 미리보기 종료됨")
```

### 여러 서비스 동시 관리:
```python
# TunnelGroup으로 여러 터널 관리
with tunnel_group_context("example.com") as group:
    # 프론트엔드
    frontend = group.add_http_tunnel(3000, "/")
    print(f"🎨 Frontend: {frontend.url}")

    # API 서버
    api = group.add_http_tunnel(8000, "/api")
    print(f"🔧 API: {api.url}")

    # 데이터베이스
    db = group.add_tcp_tunnel(5432)
    print(f"🗄️ Database: {db.endpoint}")

    # 모두 시작
    group.start_all()

    print("\n✨ 모든 서비스 실행 중!")
    print("Ctrl+C로 종료하세요...")

    # 작업...

# 모든 터널이 자동으로 정리됨!
```

### 에러 처리 예시:
```python
try:
    with managed_tunnel("example.com", 3000, "/test") as url:
        # 테스트 실행
        response = run_integration_tests(url)

        if not response.ok:
            raise TestFailedError("테스트 실패!")

except TestFailedError:
    print("❌ 테스트 실패")
    # 터널은 이미 자동 정리됨

except Exception as e:
    print(f"❌ 예상치 못한 에러: {e}")
    # 터널은 이미 자동 정리됨
```

## 🛡️ 고급 기능들

### 1. Pydantic 설정 통합
```python
from frp_wrapper.common.context_config import ContextConfig, CleanupStrategy

# 커스텀 정리 설정
config = ContextConfig(
    cleanup_timeout=10.0,  # 정리 대기 시간
    cleanup_strategy=CleanupStrategy.GRACEFUL_THEN_FORCE,
    suppress_cleanup_errors=True,  # 정리 중 에러 무시
)

with FRPClient("example.com", context_config=config) as client:
    # 설정이 적용된 client 사용
    pass
```

### 2. 리소스 추적
```python
# 내부적으로 모든 리소스 추적
class ResourceTracker:
    def register_resource(self, resource_id, resource, cleanup_callback):
        """리소스 등록"""
        self.resources[resource_id] = resource
        self.cleanup_callbacks[resource_id] = cleanup_callback

    def cleanup_all(self):
        """모든 리소스 정리 (LIFO 순서)"""
        for resource_id in reversed(list(self.resources.keys())):
            try:
                self.cleanup_callbacks[resource_id]()
            except Exception as e:
                self.errors.append(f"{resource_id}: {e}")
```

### 3. 병렬 정리
```python
# TunnelGroup은 병렬로 터널 정리 가능
config = TunnelGroupConfig(
    group_name="prod-services",
    parallel_cleanup=True,  # 병렬 정리 활성화
    cleanup_order="lifo",   # LIFO 순서
)

with TunnelGroup(client, config) as group:
    # 10개의 터널 추가
    for i in range(10):
        group.add_http_tunnel(3000 + i, f"/service{i}")

# 모든 터널이 동시에 정리됨 (빠름!)
```

## ❓ 자주 묻는 질문

**Q: with 문이 뭐가 좋은데?**
A: 자동으로 정리를 보장합니다:
- 정상 종료: ✅ 정리됨
- 예외 발생: ✅ 정리됨
- 까먹을 수 없음: ✅ 항상 정리됨

**Q: 중간에 빠져나가면?**
A: `__exit__`이 무조건 호출됩니다:
```python
with managed_tunnel(...) as url:
    if condition:
        return  # 여기서 나가도
    break       # 여기서 나가도
    raise Error # 여기서 나가도
# 항상 정리됨!
```

**Q: 성능 오버헤드는?**
A: 거의 없습니다:
- `__enter__`/`__exit__`은 단순 메서드 호출
- 정리 로직은 어차피 필요한 작업
- 오히려 수동 관리보다 효율적

**Q: 정리 중 에러가 나면?**
A: 설정으로 제어 가능:
```python
# 에러 무시하고 계속 정리
config = ContextConfig(suppress_cleanup_errors=True)

# 에러 로깅만 하고 계속
config = ContextConfig(log_cleanup_errors=True)
```

## 🎓 핵심 배운 점

1. **RAII 패턴 in Python**
   - Resource Acquisition Is Initialization
   - 리소스 획득과 해제를 묶어서 관리
   - C++의 스마트 포인터와 유사한 개념

2. **예외 안전성이 최우선**
   - 어떤 상황에서도 리소스 정리 보장
   - 메모리 누수, 연결 누수 방지
   - 안정적인 프로그램의 핵심

3. **깔끔한 API 설계**
   - 사용자가 정리를 신경 쓸 필요 없음
   - 실수할 수 없는 인터페이스
   - "Pit of Success" 원칙

## 🎉 완성된 Context Manager

이제 안전하고 편리한 터널 관리가 가능합니다!

```python
# 최종 사용 예시 - 너무 간단!
from frp_wrapper import managed_tunnel, tunnel_group_context

# 1. 단일 터널
with managed_tunnel("example.com", 3000, "/demo") as url:
    print(f"🚀 데모: {url}")

# 2. 여러 터널
with tunnel_group_context("example.com") as group:
    group.add_http_tunnel(3000, "/web")
    group.add_http_tunnel(8000, "/api")
    group.start_all()
    # 사용...

# 3. 모든 정리는 자동! 🎉
```

## 다음 단계

Checkpoint 5 완료! 이제 Context Manager로 안전한 리소스 관리가 가능합니다.

남은 체크포인트:
- Checkpoint 6: 서버 측 도구
- Checkpoint 7: 모니터링과 메트릭
- Checkpoint 8: 예제와 문서화

→ [다시 전체 개요로](00-overview.md)
