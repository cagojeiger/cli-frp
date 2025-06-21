# Checkpoint 5: Context Manager 지원

## 개요
Python의 Context Manager 프로토콜을 구현하여 터널과 클라이언트의 자동 리소스 관리를 제공합니다. `with` 문을 사용한 안전하고 Pythonic한 API를 구현합니다.

## 목표
- FRPClient에 Context Manager 프로토콜 구현
- Tunnel에 Context Manager 프로토콜 구현
- 중첩된 context 지원
- 예외 발생 시 안전한 정리

## 구현 범위

### 1. FRPClient Context Manager
```python
class FRPClient:
    # 기존 메서드들...
    
    def __enter__(self) -> 'FRPClient':
        """Context 진입 시 자동 연결"""
        if not self.is_connected():
            self.connect()
        return self
        
    def __exit__(
        self, 
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> None:
        """Context 종료 시 자동 정리"""
        try:
            self.close_all_tunnels()
            self.disconnect()
        except Exception as e:
            # 정리 중 발생한 예외는 로깅만
            logger.error(f"Error during cleanup: {e}")
            
    @contextmanager
    def tunnel(
        self,
        local_port: int,
        path: Optional[str] = None,
        **options
    ) -> Iterator[Tunnel]:
        """임시 터널 생성을 위한 context manager"""
        tunnel = None
        try:
            if path:
                tunnel = self.expose_path(local_port, path, **options)
            else:
                tunnel = self.expose_tcp(local_port, **options)
            yield tunnel
        finally:
            if tunnel:
                tunnel.close()
```

### 2. Tunnel Context Manager
```python
class Tunnel:
    # 기존 메서드들...
    
    def __enter__(self) -> 'Tunnel':
        """터널 context 진입"""
        if self.status == TunnelStatus.CLOSED:
            raise TunnelError("Cannot enter context of closed tunnel")
        return self
        
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> None:
        """터널 자동 종료"""
        self.close()
        
class HTTPTunnel(Tunnel):
    def __enter__(self) -> 'HTTPTunnel':
        """HTTP 터널 context 진입"""
        tunnel = super().__enter__()
        # HTTP 특화 초기화 (필요시)
        return tunnel
```

### 3. 고급 Context Manager 기능
```python
class TunnelGroup:
    """여러 터널을 그룹으로 관리하는 context manager"""
    
    def __init__(self, client: FRPClient):
        self.client = client
        self.tunnels: List[Tunnel] = []
        
    def add(
        self,
        local_port: int,
        path: Optional[str] = None,
        **options
    ) -> 'TunnelGroup':
        """체이닝을 위한 터널 추가"""
        if path:
            tunnel = self.client.expose_path(local_port, path, **options)
        else:
            tunnel = self.client.expose_tcp(local_port, **options)
        self.tunnels.append(tunnel)
        return self
        
    def __enter__(self) -> List[Tunnel]:
        return self.tunnels
        
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # 역순으로 정리 (LIFO)
        for tunnel in reversed(self.tunnels):
            try:
                tunnel.close()
            except Exception as e:
                logger.error(f"Error closing tunnel {tunnel.id}: {e}")

@contextmanager
def temporary_tunnel(
    server: str,
    local_port: int,
    path: str,
    **options
) -> Iterator[HTTPTunnel]:
    """일회성 터널 생성을 위한 편의 함수"""
    client = FRPClient(server, **options)
    with client:
        with client.tunnel(local_port, path) as tunnel:
            yield tunnel
```

## 테스트 시나리오

### 유닛 테스트

1. **기본 Context Manager 사용**
   ```python
   def test_client_context_manager():
       with FRPClient("example.com") as client:
           assert client.is_connected()
           tunnel = client.expose_tcp(3000)
           assert tunnel.status == TunnelStatus.CONNECTED
       
       # Context 종료 후 확인
       assert not client.is_connected()
       assert len(client.list_tunnels()) == 0
   ```

2. **터널 Context Manager**
   ```python
   def test_tunnel_context_manager():
       client = FRPClient("example.com")
       client.connect()
       
       with client.tunnel(3000, "myapp") as tunnel:
           assert tunnel.status == TunnelStatus.CONNECTED
           assert tunnel.url == "https://example.com/myapp/"
       
       # 터널 자동 종료 확인
       assert client.get_tunnel(tunnel.id) is None
   ```

3. **중첩 Context Manager**
   ```python
   def test_nested_context_managers():
       with FRPClient("example.com") as client:
           with client.tunnel(3000, "app1") as tunnel1:
               with client.tunnel(3001, "app2") as tunnel2:
                   assert len(client.list_tunnels()) == 2
               # tunnel2만 종료됨
               assert len(client.list_tunnels()) == 1
           # tunnel1도 종료됨
           assert len(client.list_tunnels()) == 0
   ```

4. **예외 처리**
   ```python
   def test_exception_handling():
       try:
           with FRPClient("example.com") as client:
               tunnel = client.expose_tcp(3000)
               raise ValueError("Test exception")
       except ValueError:
           pass
       
       # 예외 발생해도 정리됨
       assert not client.is_connected()
   ```

### 통합 테스트

1. **실제 서비스와 함께 사용**
   ```python
   @pytest.mark.integration
   def test_with_real_service():
       # Flask 앱과 함께 사용
       app = create_flask_app()
       
       with FRPClient("localhost") as client:
           with client.tunnel(5000, "testapp") as tunnel:
               # 별도 스레드에서 Flask 실행
               app_thread = Thread(target=lambda: app.run(port=5000))
               app_thread.start()
               
               # 외부에서 접근 테스트
               response = requests.get(f"{tunnel.url}health")
               assert response.status_code == 200
   ```

2. **TunnelGroup 사용**
   ```python
   def test_tunnel_group():
       with FRPClient("example.com") as client:
           with TunnelGroup(client) as group:
               group.add(3000, "frontend")
               group.add(8000, "api") 
               group.add(5432, None)  # TCP tunnel
               
               tunnels = group.tunnels
               assert len(tunnels) == 3
               assert all(t.status == TunnelStatus.CONNECTED for t in tunnels)
       
       # 모든 터널이 정리됨
       assert len(client.list_tunnels()) == 0
   ```

## 구현 상세

### 리소스 추적 및 정리
```python
class ResourceTracker:
    """리소스 생명주기 추적을 위한 내부 클래스"""
    
    def __init__(self):
        self._resources: List[Tuple[str, Any]] = []
        self._cleanup_callbacks: List[Callable] = []
        
    def register(self, resource_type: str, resource: Any, cleanup: Callable):
        """리소스 등록"""
        self._resources.append((resource_type, resource))
        self._cleanup_callbacks.append(cleanup)
        
    def cleanup_all(self):
        """모든 리소스 정리"""
        # 역순으로 정리 (LIFO)
        for callback in reversed(self._cleanup_callbacks):
            try:
                callback()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                
        self._resources.clear()
        self._cleanup_callbacks.clear()

class FRPClient:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._resource_tracker = ResourceTracker()
        
    def _register_tunnel(self, tunnel: Tunnel):
        """터널 리소스 등록"""
        self._resource_tracker.register(
            'tunnel',
            tunnel,
            lambda: self.close_tunnel(tunnel.id)
        )
```

### 예외 안전성 보장
```python
def __exit__(self, exc_type, exc_val, exc_tb):
    """안전한 종료 보장"""
    errors = []
    
    # 1. 모든 터널 종료
    for tunnel in self.list_tunnels():
        try:
            tunnel.close()
        except Exception as e:
            errors.append(f"Tunnel {tunnel.id}: {e}")
    
    # 2. 클라이언트 연결 종료
    try:
        if self.is_connected():
            self.disconnect()
    except Exception as e:
        errors.append(f"Disconnect: {e}")
    
    # 3. 임시 파일 정리
    try:
        self._cleanup_temp_files()
    except Exception as e:
        errors.append(f"Temp files: {e}")
    
    # 4. 에러 로깅
    if errors:
        logger.error(f"Cleanup errors: {'; '.join(errors)}")
    
    # 원본 예외는 재발생시키지 않음 (PEP 343)
    return False
```

### 편의 함수 구현
```python
@contextmanager
def expose_local_server(
    server: str,
    local_port: int,
    path: str,
    start_server: Callable,
    **options
) -> Iterator[Tuple[HTTPTunnel, Any]]:
    """로컬 서버와 터널을 함께 관리"""
    
    server_instance = None
    
    with FRPClient(server, **options) as client:
        with client.tunnel(local_port, path) as tunnel:
            try:
                # 서버 시작
                server_instance = start_server(local_port)
                yield tunnel, server_instance
            finally:
                # 서버 종료
                if server_instance and hasattr(server_instance, 'shutdown'):
                    server_instance.shutdown()
```

## 파일 구조
```
frp_wrapper/
├── client.py           # Context Manager 추가
├── tunnel.py           # Tunnel Context Manager
├── context.py          # TunnelGroup, 편의 함수
├── resource_tracker.py # 리소스 추적 클래스
└── exceptions.py       # Context 관련 예외

tests/
├── test_context_manager.py
├── test_tunnel_group.py
├── test_exception_handling.py
└── test_resource_cleanup.py
```

## 완료 기준

### 필수 기능
- [x] FRPClient Context Manager
- [x] Tunnel Context Manager
- [x] 중첩 context 지원
- [x] 예외 시 안전한 정리
- [x] TunnelGroup 구현

### 테스트
- [x] 기본 with 문 테스트
- [x] 중첩 context 테스트
- [x] 예외 처리 테스트
- [x] 리소스 누수 테스트

### 문서
- [x] Context Manager 사용법
- [x] 베스트 프랙티스
- [x] 예제 코드

## 예상 작업 시간
- Context Manager 구현: 3시간
- 리소스 추적: 2시간
- TunnelGroup: 2시간
- 테스트 작성: 4시간
- 문서화: 2시간

**총 예상 시간**: 13시간 (3일)

## 다음 단계 준비
- 서버 설정 도구
- FRP 서버 설정 통합
- 배포 자동화

## 의존성
- Checkpoint 1-4 완료
- Python 3.8+ (contextlib)
- 로깅 시스템

## 주의사항
- 예외 전파 규칙 준수
- 리소스 정리 순서
- 순환 참조 방지
- 스레드 안전성