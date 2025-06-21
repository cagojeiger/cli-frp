# Checkpoint 4: 서브패스 라우팅

## 개요
HTTP 터널을 서브패스 기반으로 노출하는 핵심 기능을 구현합니다. `https://tunnel.example.com/myapp/` 형태로 서비스를 접근 가능하게 만듭니다.

## 목표
- HTTP 터널을 서브패스로 매핑
- 가상 호스트를 통한 라우팅 구현
- 경로 변환 옵션 (strip_path) 지원
- WebSocket 지원

## 구현 범위

### 1. HTTP 터널 설정
```python
@dataclass
class HTTPTunnelConfig(TunnelConfig):
    """HTTP 터널 전용 설정"""
    path: str                    # 서브패스 (예: "myapp")
    vhost: str                   # 가상 호스트 (예: "myapp.local")
    strip_path: bool = True      # 경로 제거 여부
    websocket: bool = True       # WebSocket 지원
    custom_headers: Dict[str, str] = field(default_factory=dict)
    rewrite_rules: List[Tuple[str, str]] = field(default_factory=list)
    
class HTTPTunnel(Tunnel):
    """HTTP 터널 클래스"""
    
    @property
    def url(self) -> str:
        """완전한 접속 URL을 반환합니다"""
        base_url = self._client.options.get('base_url', f"https://{self._client.server}")
        return f"{base_url}/{self.config.path}/"
        
    @property
    def vhost(self) -> str:
        """가상 호스트명을 반환합니다"""
        return self.config.vhost
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
    
    def _generate_vhost_for_path(self, path: str) -> str:
        """서브패스를 위한 가상 호스트명 생성"""
```

### 3. Nginx 설정 생성기
```python
class NginxConfigGenerator:
    """서버 측 Nginx 설정을 생성하는 유틸리티"""
    
    def __init__(self, domain: str, frp_http_port: int = 8080):
        self.domain = domain
        self.frp_http_port = frp_http_port
        
    def generate_server_block(self) -> str:
        """Nginx server 블록 생성"""
        
    def generate_location_block(self, path: str, vhost: str) -> str:
        """특정 경로에 대한 location 블록 생성"""
        
    def generate_full_config(self, paths: List[Tuple[str, str]]) -> str:
        """전체 Nginx 설정 파일 생성"""
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
       assert tunnel.vhost == "myapp.local"
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

4. **Nginx 설정 생성**
   ```python
   def test_nginx_config_generation():
       generator = NginxConfigGenerator("tunnel.example.com")
       
       location = generator.generate_location_block("myapp", "myapp.local")
       
       assert "location ~ ^/myapp/(.*)" in location
       assert "proxy_set_header Host myapp.local" in location
       assert "proxy_pass http://localhost:8080" in location
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
       ws.connect(f"wss://tunnel.example.com/ws/")
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
    
    # 2. 가상 호스트 생성
    vhost = self._generate_vhost_for_path(path)
    
    # 3. HTTP 터널 설정 생성
    config = HTTPTunnelConfig(
        local_port=local_port,
        tunnel_type='http',
        path=path,
        vhost=vhost,
        strip_path=strip_path,
        websocket=options.get('websocket', True),
        custom_headers=options.get('custom_headers', {})
    )
    
    # 4. FRP 설정 구성
    frp_config = {
        'type': 'http',
        'local_ip': '127.0.0.1',
        'local_port': local_port,
        'custom_domains': vhost,
        'use_compression': True,
        'use_encryption': True
    }
    
    # 5. 경로 재작성 설정
    if strip_path:
        # FRP는 직접적인 경로 재작성을 지원하지 않으므로
        # 프록시 미들웨어나 Nginx에서 처리 필요
        frp_config['route_config'] = {
            'strip_prefix': f'/{path}'
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

### Nginx 설정 템플릿
```python
NGINX_LOCATION_TEMPLATE = """
    location ~ ^/{path}/(.*) {{
        set $upstream_path /$1;
        
        proxy_pass http://localhost:{frp_port};
        proxy_http_version 1.1;
        
        # 호스트 헤더 설정 (FRP 라우팅용)
        proxy_set_header Host {vhost};
        
        # 원본 경로 정보 전달
        proxy_set_header X-Original-URI $request_uri;
        proxy_set_header X-Forwarded-Path /{path};
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 지원
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 타임아웃 설정
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
        send_timeout 600;
    }}
"""
```

## 파일 구조
```
frp_wrapper/
├── http_tunnel.py      # HTTPTunnel 클래스
├── client.py           # expose_path 메서드 추가
├── nginx_config.py     # Nginx 설정 생성기
└── path_utils.py       # 경로 관련 유틸리티

server_setup/
├── nginx.conf.template # Nginx 전체 설정 템플릿
├── install_nginx.sh    # Nginx 설치 스크립트
└── README.md          # 서버 설정 가이드

tests/
├── test_path_routing.py
├── test_nginx_config.py
└── fixtures/
    └── test_app.py     # 테스트용 Flask 앱
```

## 완료 기준

### 필수 기능
- [x] expose_path 메서드 구현
- [x] 가상 호스트 매핑
- [x] strip_path 옵션
- [x] 커스텀 헤더 지원
- [x] WebSocket 지원

### 테스트
- [x] 서브패스 터널 생성 테스트
- [x] URL 생성 정확성 테스트
- [x] 경로 변환 테스트
- [x] Nginx 설정 생성 테스트

### 문서
- [x] 서브패스 라우팅 설명
- [x] 서버 설정 가이드
- [x] 사용 예제 코드

## 예상 작업 시간
- HTTPTunnel 구현: 3시간
- expose_path 메서드: 4시간
- Nginx 설정 생성기: 3시간
- 테스트 작성: 5시간
- 문서화: 2시간

**총 예상 시간**: 17시간 (4일)

## 다음 단계 준비
- Context Manager 지원
- 자동 리소스 정리
- 중첩 터널 관리

## 의존성
- Checkpoint 1-3 완료
- HTTP 프록시 이해
- Nginx 설정 지식

## 주의사항
- 경로 검증 철저히
- 가상 호스트 충돌 방지
- WebSocket 호환성
- 보안 헤더 설정