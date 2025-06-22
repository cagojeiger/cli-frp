# 순환 의존성 해결: Protocol 패턴 적용

## 문제 상황

FRP Wrapper 프로젝트에서 `tunnels/models.py`와 `tunnels/manager.py` 사이에 순환 의존성(circular dependency) 문제가 발생했습니다.

### 순환 의존성 구조

```
tunnels/models.py  ←──→  tunnels/manager.py
      ↓                         ↑
  BaseTunnel.manager      TunnelManager
  필드가 TunnelManager     클래스가 tunnel
  타입을 참조              모델들을 import
```

## 적용 전 구조 (문제 상황)

### models.py (Before)
```python
# tunnels/models.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import TunnelManager  # 순환 import 회피용

class BaseTunnel(BaseModel):
    manager: "TunnelManager | None" = Field(...)  # 문자열 타입 힌트

    def with_manager(self, manager: "TunnelManager") -> "BaseTunnel":
        return self.model_copy(update={"manager": manager})
```

### manager.py (Before)
```python
# tunnels/manager.py
from .models import BaseTunnel, HTTPTunnel, TCPTunnel  # 직접 import

class TunnelManager:
    def create_http_tunnel(...) -> HTTPTunnel:
        ...

# 파일 끝에 model_rebuild() 호출로 forward reference 해결
BaseTunnel.model_rebuild()
HTTPTunnel.model_rebuild()
TCPTunnel.model_rebuild()
```

### 문제점
1. `TYPE_CHECKING` 가드로 런타임 import 회피 (취약한 해결책)
2. 문자열 타입 힌트 사용 ("TunnelManager")
3. `model_rebuild()` 호출 필요
4. import 순서에 민감함
5. 타입 체커 혼란 가능성

## Protocol 패턴 적용 후 구조

### 1. 새로운 interfaces.py 파일
```python
# tunnels/interfaces.py
from __future__ import annotations
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .models import BaseTunnel  # 타입 체킹시에만 import

class TunnelRegistryProtocol(Protocol):
    """Tunnel 레지스트리 연산을 위한 Protocol"""
    def get_tunnel(self, tunnel_id: str) -> BaseTunnel | None: ...
    def update_tunnel_status(self, tunnel_id: str, status: Any) -> None: ...

class TunnelManagerProtocol(Protocol):
    """Tunnel 매니저 연산을 위한 Protocol"""
    @property
    def registry(self) -> TunnelRegistryProtocol: ...
    def start_tunnel(self, tunnel_id: str) -> bool: ...
    def stop_tunnel(self, tunnel_id: str) -> bool: ...
    def remove_tunnel(self, tunnel_id: str) -> BaseTunnel: ...
```

### 2. 개선된 models.py
```python
# tunnels/models.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .interfaces import TunnelManagerProtocol  # 타입 체킹시에만 import

class BaseTunnel(BaseModel):
    model_config = ConfigDict(frozen=True, extra='allow')  # extra 허용

    # manager는 Pydantic 필드가 아닌 property로 구현
    @property
    def manager(self) -> "TunnelManagerProtocol | None":
        """Get associated tunnel manager."""
        return getattr(self, '_manager', None)

    def with_manager(self, manager: "TunnelManagerProtocol") -> "BaseTunnel":
        """Associate tunnel with a manager."""
        new_tunnel = self.model_copy()
        object.__setattr__(new_tunnel, '_manager', manager)  # frozen 모델에서도 작동
        return new_tunnel
```

### 3. 개선된 manager.py
```python
# tunnels/manager.py
from .models import BaseTunnel, HTTPTunnel, TCPTunnel  # 정상적인 import

class TunnelManager:  # 자동으로 TunnelManagerProtocol 구현
    def create_http_tunnel(...) -> HTTPTunnel:
        ...

# model_rebuild() 호출 불필요 - 삭제됨
```

## 개선 효과

### 의존성 흐름 (After)
```
interfaces.py (Protocol 정의)
      ↑              ↑
      │              │
models.py ────→ manager.py
(Protocol 사용)  (Protocol 구현)
```

### 장점
1. **명확한 의존성 방향**: 순환 없이 단방향 흐름
2. **타입 안정성**: Protocol을 통한 명시적 인터페이스
3. **유연성**: TunnelManager가 Protocol을 자동으로 만족
4. **단순성**: TYPE_CHECKING 가드나 model_rebuild() 불필요
5. **확장성**: 새로운 매니저 구현체 추가 가능

## Protocol 패턴이란?

Python의 Protocol은 구조적 서브타이핑(structural subtyping)을 지원하는 기능입니다.
명시적으로 상속하지 않아도 필요한 메서드를 구현하면 자동으로 Protocol을 만족합니다.

```python
from typing import Protocol

class Drawable(Protocol):
    def draw(self) -> None: ...

class Circle:  # Drawable을 상속하지 않음
    def draw(self) -> None:
        print("Drawing circle")

# Circle은 자동으로 Drawable Protocol을 만족
def render(obj: Drawable) -> None:
    obj.draw()

render(Circle())  # 정상 작동
```

이 패턴을 통해 순환 의존성을 깔끔하게 해결하면서도 타입 안정성을 유지할 수 있습니다.

## 구현 세부사항

### Pydantic과 Protocol의 호환성 문제 해결

Pydantic은 Protocol 타입을 직접 필드로 사용할 수 없으므로, 다음과 같은 방법으로 해결했습니다:

1. **Property 패턴 사용**: manager를 Pydantic 필드가 아닌 property로 구현
2. **Extra 속성 허용**: `model_config`에 `extra='allow'` 설정
3. **Frozen 모델 대응**: `object.__setattr__` 사용으로 frozen 모델에서도 속성 설정 가능

이 접근 방식의 장점:
- Pydantic 검증 로직과 분리되어 Protocol 타입 사용 가능
- 타입 체커는 여전히 올바른 타입 정보 제공
- 런타임 오류 없이 안정적으로 작동
