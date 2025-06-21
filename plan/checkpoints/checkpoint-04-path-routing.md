# Checkpoint 4: 경로 기반 라우팅

## 개요
FRP의 네이티브 `locations` 기능을 활용하여 HTTP 터널을 경로 기반으로 노출하는 핵심 기능을 구현합니다. `https://example.com/myapp/` 형태로 서비스를 접근 가능하게 만듭니다.

## 목표
- FRP locations 파라미터를 활용한 경로 기반 라우팅
- customDomains와 locations 조합으로 직접 라우팅
- 경로 변환 옵션 지원
- WebSocket 지원

## 구현 범위

### 1. HTTP 터널 설정
```python
@dataclass
class HTTPTunnelConfig(TunnelConfig):
    """HTTP 터널 전용 설정"""
    path: str                    # 경로 (예: "myapp")
    custom_domains: List[str]    # 커스텀 도메인 (예: ["example.com"])
    locations: List[str]         # 위치 경로 (예: ["/myapp"])
    strip_path: bool = True      # 경로 제거 여부
    websocket: bool = True       # WebSocket 지원
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
class HTTPTunnel(Tunnel):
    """HTTP 터널 클래스"""
    
    @property
    def url(self) -> str:
        """완전한 접속 URL을 반환합니다"""
        if self.config.custom_domains and self.config.locations:
            domain = self.config.custom_domains[0]
            location = self.config.locations[0]
            return f"https://{domain}{location}/"
        return None
        
    @property
    def domain(self) -> str:
        """사용 중인 도메인을 반환합니다"""
        return self.config.custom_domains[0] if self.config.custom_domains else None
```

### 2. FRPClient 확장
```python
class FRPClient:
    # 기존 메서드들...
    
    def expose_path(
        self,
        local_port: int,
        path: str,
        strip_path: bool = True,
        websocket: bool = True,
        custom_headers: Optional[Dict[str, str]] = None,
        **options
    ) -> HTTPTunnel:
        """로컬 서비스를 서브패스로 노출합니다"""
        
    def expose_http(
        self,
        local_port: int,
        subdomain: Optional[str] = None,
        custom_domains: Optional[List[str]] = None,
        **options
    ) -> HTTPTunnel:
        """로컬 서비스를 HTTP로 노출합니다 (기존 방식)"""
        
    # 내부 메서드
    def _create_http_tunnel_config(
        self,
        local_port: int,
        path: str,
        **options
    ) -> HTTPTunnelConfig
    
    def _generate_tunnel_name(self, path: str) -> str:
        """경로를 위한 터널명 생성"""
```

### 3. FRP 설정 생성기
```python
class FRPConfigGenerator:
    """FRP TOML 설정을 생성하는 유틸리티"""
    
    def __init__(self, server_addr: str, server_port: int = 7000):
        self.server_addr = server_addr
        self.server_port = server_port
        
    def generate_http_proxy(self, name: str, local_port: int, 
                           custom_domains: List[str], locations: List[str]) -> str:
        """HTTP 프록시 설정 생성"""
        
    def generate_full_config(self, proxies: List[Dict]) -> str:
        """전체 FRP 클라이언트 설정 파일 생성"""
```

## 테스트 시나리오

### 유닛 테스트

1. **서브패스 터널 생성**
   ```python
   def test_create_path_tunnel():
       client = FRPClient("tunnel.example.com")
       client.connect()
       
       tunnel = client.expose_path(3000, "myapp")
       
       assert isinstance(tunnel, HTTPTunnel)
       assert tunnel.url == "https://tunnel.example.com/myapp/"
       assert tunnel.config.custom_domains == ["tunnel.example.com"]
       assert tunnel.config.locations == ["/myapp"]
   ```

2. **strip_path 옵션**
   ```python
   def test_strip_path_option():
       # strip_path=True (기본값)
       tunnel1 = client.expose_path(3000, "api", strip_path=True)
       config1 = get_tunnel_config(tunnel1.id)
       assert config1['locations'] == ["/"]  # /api 제거됨
       
       # strip_path=False
       tunnel2 = client.expose_path(3001, "api", strip_path=False)
       config2 = get_tunnel_config(tunnel2.id)
       assert config2['locations'] == ["/api"]  # /api 유지됨
   ```

3. **커스텀 헤더**
   ```python
   def test_custom_headers():
       headers = {
           "X-Forwarded-Path": "/myapp",
           "X-Custom-Header": "value"
       }
       
       tunnel = client.expose_path(
           3000, 
           "myapp",
           custom_headers=headers
       )
       
       config = get_tunnel_config(tunnel.id)
       assert config['headers'] == headers
   ```

4. **FRP 설정 생성**
   ```python
   def test_frp_config_generation():
       generator = FRPConfigGenerator("tunnel.example.com", 7000)
       
       proxy_config = generator.generate_http_proxy(
           "myapp", 3000, ["tunnel.example.com"], ["/myapp"]
       )
       
       assert "customDomains = [\"tunnel.example.com\"]" in proxy_config
       assert "locations = [\"/myapp\"]" in proxy_config
       assert "localPort = 3000" in proxy_config
   ```

### 통합 테스트

1. **실제 HTTP 서비스 테스트**
   ```python
   @pytest.mark.integration
   def test_real_http_tunnel():
       # Flask 앱 시작
       app = create_test_flask_app()
       app_thread = threading.Thread(
           target=lambda: app.run(port=3000)
       )
       app_thread.start()
       
       # 터널 생성
       client = FRPClient("localhost")
       client.connect()
       tunnel = client.expose_path(3000, "testapp")
       
       # HTTP 요청 테스트
       response = requests.get(f"{tunnel.url}api/test")
       assert response.status_code == 200
       assert response.json()['message'] == 'Hello from test app'
   ```

2. **WebSocket 지원 테스트**
   ```python
   def test_websocket_support():
       # WebSocket 서버 시작
       ws_server = start_websocket_server(3000)
       
       # 터널 생성
       tunnel = client.expose_path(3000, "ws", websocket=True)
       
       # WebSocket 연결 테스트
       ws = websocket.WebSocket()
       ws.connect(f"wss://example.com/ws/")
       ws.send("Hello")
       
       assert ws.recv() == "Echo: Hello"
   ```

## 구현 상세

### expose_path 구현
```python
def expose_path(
    self,
    local_port: int,
    path: str,
    strip_path: bool = True,
    **options
) -> HTTPTunnel:
    """로컬 서비스를 서브패스로 노출합니다"""
    
    # 1. 경로 검증
    if not path or path.startswith('/'):
        raise ValueError("Path must not start with '/'")
    
    # 2. 도메인 가져오기 (기본값 또는 설정에서)
    domain = options.get('domain', self.default_domain)
    
    # 3. HTTP 터널 설정 생성
    config = HTTPTunnelConfig(
        local_port=local_port,
        tunnel_type='http',
        path=path,
        custom_domains=[domain],
        locations=[f'/{path}'],
        strip_path=strip_path,
        websocket=options.get('websocket', True),
        custom_headers=options.get('custom_headers', {})
    )
    
    # 4. FRP 설정 구성 (locations 기능 사용)
    frp_config = {
        'type': 'http',
        'localPort': local_port,
        'customDomains': [domain],
        'locations': [f'/{path}'],  # FRP 네이티브 기능!
        'useCompression': True,
        'useEncryption': True
    }
    
    # 5. 경로 재작성 설정 (선택사항)
    if strip_path:
        # 로컬 서비스에서 경로 제거 처리를 원하는 경우
        # 헤더를 통해 원본 경로 정보 전달
        frp_config['hostHeaderRewrite'] = '127.0.0.1'
        frp_config['requestHeaders'] = {
            'set': {'X-Original-Path': f'/{path}'}
        }
    
    # 6. 헤더 설정
    if config.custom_headers:
        frp_config['headers'] = config.custom_headers
    
    # 7. 터널 생성 (기존 프로세스 활용)
    tunnel_id = self._generate_tunnel_id()
    self._config_builder.add_tunnel(tunnel_id, frp_config)
    
    # 8. HTTPTunnel 객체 생성
    tunnel = HTTPTunnel(tunnel_id, config, self)
    self._tunnel_manager.add_tunnel(tunnel)
    
    # 9. 설정 적용
    self._update_config_and_restart()
    
    # 10. 연결 확인
    if self._wait_for_tunnel_ready(tunnel_id):
        tunnel.status = TunnelStatus.CONNECTED
    
    return tunnel
```

### FRP TOML 설정 템플릿
```python
FRP_PROXY_TEMPLATE = """
[[proxies]]
name = "{name}"
type = "http"
localPort = {local_port}
customDomains = ["{domain}"]
locations = ["{location}"]

# 선택사항: 경로 리라이트
# pathRewrite = {{ "{location}" = "/" }}

# 선택사항: 커스텀 헤더
# [proxies.requestHeaders.set]
# "X-Forwarded-Path" = "{location}"
# "X-Real-IP" = "$remote_addr"

# 선택사항: WebSocket 지원 (기본 활성화)
# websocket = true
"""
```

## 파일 구조
```
frp_wrapper/
├── http_tunnel.py      # HTTPTunnel 클래스
├── client.py           # expose_path 메서드 추가
├── config_builder.py   # FRP TOML 설정 생성기
└── path_utils.py       # 경로 관련 유틸리티

frp_config/
├── client.toml.template # FRP 클라이언트 설정 템플릿
└── README.md          # FRP 설정 가이드

tests/
├── test_path_routing.py
├── test_frp_config.py  # FRP 설정 생성 테스트
└── fixtures/
    └── test_app.py     # 테스트용 Flask 앱
```

## 완료 기준

### 필수 기능
- [ ] expose_path 메서드 구현
- [ ] FRP locations 기능 활용
- [ ] customDomains 지원
- [ ] strip_path 옵션
- [ ] 커스텀 헤더 지원
- [ ] WebSocket 지원

### 테스트
- [ ] 경로 기반 터널 생성 테스트
- [ ] URL 생성 정확성 테스트
- [ ] locations 파라미터 테스트
- [ ] FRP TOML 설정 생성 테스트

### 문서
- [ ] FRP locations 기반 라우팅 설명
- [ ] FRP 서버 설정 가이드
- [ ] 사용 예제 코드

## 예상 작업 시간
- HTTPTunnel 구현: 2시간 (단순화됨)
- expose_path 메서드: 2시간 (FRP 네이티브 기능 활용)
- FRP 설정 생성기: 1시간 (TOML 생성만)
- 테스트 작성: 3시간
- 문서화: 2시간

**총 예상 시간**: 10시간 (2.5일)

## 다음 단계 준비
- Context Manager 지원
- 자동 리소스 정리
- 중첩 터널 관리

## 의존성
- Checkpoint 1-3 완료
- FRP locations 기능 이해
- TOML 설정 포맷 지식

## 주의사항
- 경로 검증 철저히 (/ 시작하지 않도록)
- customDomains와 locations 조합 올바른 사용
- WebSocket 호환성 확인
- FRP 네이티브 기능 최대 활용