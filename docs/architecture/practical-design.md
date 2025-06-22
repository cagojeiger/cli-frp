# 실용적 설계 가이드 - TDD + Pydantic

FRP Python Wrapper는 TDD(Test-Driven Development)와 Pydantic v2를 활용한 객체지향 설계를 따릅니다.

## 핵심 원칙

### 1. Test-Driven Development (TDD)
모든 기능은 테스트를 먼저 작성한 후 구현합니다.

```python
# 1. 실패하는 테스트 작성
def test_client_connects_to_server():
    """클라이언트가 서버에 연결되어야 함"""
    client = FRPClient("example.com")
    result = client.connect()
    assert result is True
    assert client.is_connected()

# 2. 최소한의 구현
def connect(self) -> bool:
    # 테스트를 통과시키는 최소 구현
    self.status = ConnectionStatus.CONNECTED
    return True

# 3. 리팩터링
def connect(self) -> bool:
    try:
        # 실제 연결 로직 구현
        self._process_manager.start(self.config_file)
        self.status = ConnectionStatus.CONNECTED
        return True
    except Exception:
        self.status = ConnectionStatus.ERROR
        return False
```

### 2. Pydantic v2 활용
모든 데이터 모델과 설정은 Pydantic으로 정의합니다.

```python
from pydantic import BaseModel, Field, ConfigDict, field_validator

class TunnelConfig(BaseModel):
    """터널 설정 모델"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    local_port: int = Field(..., ge=1, le=65535, description="로컬 포트")
    path: str = Field(..., min_length=1, description="HTTP 경로")
    custom_domains: List[str] = Field(default_factory=list)

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        if v.startswith('/'):
            raise ValueError("경로는 '/'로 시작할 수 없습니다")
        return v
```

### 3. 간단한 예외 처리
복잡한 함수형 패턴 대신 표준 Python 예외를 사용합니다.

```python
class TunnelError(Exception):
    """터널 관련 오류"""
    pass

class ConnectionError(Exception):
    """연결 관련 오류"""
    pass

def create_tunnel(local_port: int, path: str) -> HTTPTunnel:
    """HTTP 터널 생성"""
    if not (1 <= local_port <= 65535):
        raise TunnelError(f"잘못된 포트: {local_port}")

    return HTTPTunnel(
        id=generate_id(),
        local_port=local_port,
        path=path
    )
```

## TDD 사이클

### Red-Green-Refactor

```python
# RED: 실패하는 테스트
def test_tunnel_validates_port():
    """터널이 포트를 검증해야 함"""
    with pytest.raises(TunnelError):
        create_tunnel(0, "test")  # 잘못된 포트

# GREEN: 테스트 통과
def create_tunnel(local_port: int, path: str) -> HTTPTunnel:
    if local_port <= 0:
        raise TunnelError("잘못된 포트")
    return HTTPTunnel(id="test", local_port=local_port, path=path)

# REFACTOR: 코드 개선
def create_tunnel(local_port: int, path: str) -> HTTPTunnel:
    config = TunnelConfig(local_port=local_port, path=path)  # Pydantic 검증
    return HTTPTunnel(
        id=generate_tunnel_id(),
        local_port=config.local_port,
        path=config.path
    )
```

## Pydantic 패턴

### 1. 설정 검증

```python
class ClientConfig(BaseModel):
    """클라이언트 설정"""

    server_host: str = Field(..., min_length=1)
    server_port: int = Field(default=7000, ge=1, le=65535)
    auth_token: Optional[str] = Field(None, min_length=8)

    @field_validator('server_host')
    @classmethod
    def validate_host(cls, v: str) -> str:
        if not v or v.isspace():
            raise ValueError("서버 주소는 필수입니다")
        return v.strip()
```

### 2. 데이터 직렬화

```python
class TunnelStatus(BaseModel):
    """터널 상태"""

    id: str
    status: str
    local_port: int
    url: Optional[str] = None

    def to_json(self) -> str:
        """JSON으로 직렬화"""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> 'TunnelStatus':
        """JSON에서 역직렬화"""
        return cls.model_validate_json(json_str)
```

### 3. 설정 파일 관리

```python
class AppConfig(BaseModel):
    """앱 전체 설정"""

    client: ClientConfig
    tunnels: List[TunnelConfig] = Field(default_factory=list)

    @classmethod
    def load_from_file(cls, file_path: str) -> 'AppConfig':
        """YAML 파일에서 설정 로드"""
        with open(file_path) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)

    def save_to_file(self, file_path: str) -> None:
        """YAML 파일로 설정 저장"""
        with open(file_path, 'w') as f:
            yaml.safe_dump(self.model_dump(), f)
```

## 테스트 전략

### 1. 단위 테스트

```python
class TestTunnelConfig:
    def test_valid_config_creation(self):
        """유효한 설정 생성"""
        config = TunnelConfig(
            local_port=3000,
            path="myapp"
        )
        assert config.local_port == 3000
        assert config.path == "myapp"

    def test_invalid_port_raises_error(self):
        """잘못된 포트로 오류 발생"""
        with pytest.raises(ValidationError):
            TunnelConfig(local_port=0, path="test")

    def test_path_validation(self):
        """경로 검증"""
        with pytest.raises(ValidationError):
            TunnelConfig(local_port=3000, path="/invalid")
```

### 2. Property-based 테스트

```python
from hypothesis import given, strategies as st

@given(
    port=st.integers(min_value=1, max_value=65535),
    path=st.text(min_size=1, max_size=50).filter(lambda x: not x.startswith('/'))
)
def test_valid_inputs_always_work(port: int, path: str):
    """유효한 입력은 항상 동작해야 함"""
    config = TunnelConfig(local_port=port, path=path)
    assert config.local_port == port
    assert config.path == path
```

### 3. 통합 테스트

```python
@pytest.mark.integration
class TestFRPClientIntegration:
    def test_real_tunnel_creation(self):
        """실제 터널 생성 테스트"""
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value.poll.return_value = None

            client = FRPClient("example.com")
            client.connect()

            tunnel = client.expose_path(3000, "test")
            assert tunnel.local_port == 3000
            assert tunnel.path == "test"
```

## 실용적인 패턴

### 1. Context Manager

```python
class FRPClient:
    def __enter__(self):
        """자동 연결"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """자동 정리"""
        try:
            for tunnel in self._tunnels:
                tunnel.close()
            self.disconnect()
        except Exception as e:
            logger.error(f"정리 중 오류: {e}")
```

### 2. 설정 빌더

```python
class ConfigBuilder:
    """설정 빌더"""

    def __init__(self):
        self._server_config = None
        self._tunnels = []

    def server(self, host: str, port: int = 7000) -> 'ConfigBuilder':
        """서버 설정"""
        self._server_config = ClientConfig(
            server_host=host,
            server_port=port
        )
        return self

    def tunnel(self, local_port: int, path: str) -> 'ConfigBuilder':
        """터널 추가"""
        tunnel_config = TunnelConfig(
            local_port=local_port,
            path=path
        )
        self._tunnels.append(tunnel_config)
        return self

    def build(self) -> AppConfig:
        """최종 설정 빌드"""
        if not self._server_config:
            raise ValueError("서버 설정이 필요합니다")

        return AppConfig(
            client=self._server_config,
            tunnels=self._tunnels
        )

# 사용 예
config = (ConfigBuilder()
    .server("example.com", 7000)
    .tunnel(3000, "app1")
    .tunnel(3001, "app2")
    .build())
```

### 3. 팩토리 패턴

```python
class TunnelFactory:
    """터널 팩토리"""

    @staticmethod
    def create_http_tunnel(local_port: int, path: str, **kwargs) -> HTTPTunnel:
        """HTTP 터널 생성"""
        config = TunnelConfig(
            local_port=local_port,
            path=path,
            **kwargs
        )

        return HTTPTunnel(
            id=generate_tunnel_id(),
            local_port=config.local_port,
            path=config.path,
            custom_domains=config.custom_domains
        )

    @staticmethod
    def create_tcp_tunnel(local_port: int, remote_port: Optional[int] = None) -> TCPTunnel:
        """TCP 터널 생성"""
        return TCPTunnel(
            id=generate_tunnel_id(),
            local_port=local_port,
            remote_port=remote_port
        )
```

## 성능 최적화

### 1. Pydantic 최적화

```python
class OptimizedConfig(BaseModel):
    """최적화된 설정"""

    model_config = ConfigDict(
        # 검증 최적화
        validate_assignment=False,  # 할당 시 검증 비활성화
        use_enum_values=True,      # enum 값 직접 사용
        arbitrary_types_allowed=True,  # 임의 타입 허용
    )
```

### 2. 지연 로딩

```python
class LazyClient:
    """지연 로딩 클라이언트"""

    def __init__(self, config: ClientConfig):
        self.config = config
        self._process_manager = None

    @property
    def process_manager(self) -> ProcessManager:
        """필요할 때만 생성"""
        if self._process_manager is None:
            self._process_manager = ProcessManager(self.config.binary_path)
        return self._process_manager
```

## 장점

1. **예측 가능성**: TDD로 모든 동작이 테스트됨
2. **타입 안전성**: Pydantic으로 런타임 타입 검증
3. **가독성**: 간단하고 직관적인 Python 코드
4. **유지보수성**: 표준 패턴으로 이해하기 쉬움
5. **성능**: Pydantic v2의 Rust 기반 빠른 검증

## 주의사항

1. **테스트 커버리지**: 95% 이상 유지
2. **Pydantic 버전**: v2 기능 활용하되 하위 호환성 고려
3. **예외 처리**: 명확하고 구체적인 오류 메시지
4. **문서화**: docstring과 type hint 적극 활용

이 접근 방식은 복잡한 함수형 패턴 없이도 견고하고 유지보수하기 쉬운 코드를 만들 수 있게 해줍니다.
