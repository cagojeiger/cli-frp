# Checkpoint 6: 서버 설정 도구

## 개요
FRP 서버와 Nginx를 설정하고 관리하는 도구를 제공합니다. 서브패스 라우팅을 위한 서버 측 설정을 자동화하고, 배포를 간소화합니다.

## 목표
- Nginx 설정 파일 자동 생성
- FRP 서버 설정 관리
- SSL 인증서 통합
- 설치 및 배포 스크립트

## 구현 범위

### 1. Nginx 설정 생성기
```python
class NginxConfigBuilder:
    """Nginx 설정을 동적으로 생성하는 클래스"""
    
    def __init__(
        self,
        domain: str,
        ssl_cert_path: Optional[str] = None,
        ssl_key_path: Optional[str] = None
    ):
        self.domain = domain
        self.ssl_cert_path = ssl_cert_path
        self.ssl_key_path = ssl_key_path
        self.frp_http_port = 8080
        self.paths: List[PathConfig] = []
        
    def add_path(
        self,
        path: str,
        vhost: str,
        options: Optional[Dict[str, Any]] = None
    ) -> 'NginxConfigBuilder':
        """서브패스 라우팅 규칙 추가"""
        
    def set_ssl(
        self,
        cert_path: str,
        key_path: str,
        dhparam_path: Optional[str] = None
    ) -> 'NginxConfigBuilder':
        """SSL 설정"""
        
    def build(self) -> str:
        """완전한 Nginx 설정 파일 생성"""
        
    def write_config(self, output_path: str) -> None:
        """설정 파일 저장"""

@dataclass
class PathConfig:
    """개별 경로 설정"""
    path: str
    vhost: str
    strip_path: bool = True
    websocket: bool = True
    custom_headers: Dict[str, str] = field(default_factory=dict)
    rate_limit: Optional[str] = None
```

### 2. FRP 서버 설정 관리
```python
class FRPServerConfig:
    """FRP 서버 설정 관리"""
    
    def __init__(self):
        self.bind_port = 7000
        self.vhost_http_port = 8080
        self.dashboard_port = 7500
        self.auth_token = None
        self.allow_ports = []
        
    def set_auth(self, token: str) -> 'FRPServerConfig':
        """인증 토큰 설정"""
        
    def set_dashboard(
        self,
        port: int,
        user: str,
        password: str
    ) -> 'FRPServerConfig':
        """대시보드 설정"""
        
    def add_allowed_ports(self, ports: List[int]) -> 'FRPServerConfig':
        """허용 포트 추가"""
        
    def generate_ini(self) -> str:
        """frps.ini 파일 생성"""
        
    def generate_systemd_service(self) -> str:
        """systemd 서비스 파일 생성"""
```

### 3. 서버 설정 자동화
```python
class ServerSetup:
    """서버 설정 자동화 도구"""
    
    def __init__(self, domain: str):
        self.domain = domain
        self.nginx_config = NginxConfigBuilder(domain)
        self.frp_config = FRPServerConfig()
        
    def setup_ssl_with_letsencrypt(self, email: str) -> None:
        """Let's Encrypt로 SSL 인증서 자동 설정"""
        
    def install_dependencies(self) -> None:
        """필요한 패키지 설치"""
        
    def configure_firewall(self, ports: List[int]) -> None:
        """방화벽 규칙 설정"""
        
    def deploy(self) -> None:
        """전체 배포 프로세스 실행"""
        
    def generate_setup_script(self) -> str:
        """설치 스크립트 생성"""
```

### 4. 모니터링 및 관리 도구
```python
class ServerManager:
    """서버 상태 모니터링 및 관리"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        
    def get_status(self) -> Dict[str, Any]:
        """서버 상태 조회"""
        
    def reload_nginx(self) -> None:
        """Nginx 설정 리로드"""
        
    def restart_frp_server(self) -> None:
        """FRP 서버 재시작"""
        
    def list_active_tunnels(self) -> List[Dict[str, Any]]:
        """활성 터널 목록 조회"""
        
    def add_path_mapping(self, path: str, vhost: str) -> None:
        """새 경로 매핑 추가"""
```

## 테스트 시나리오

### 유닛 테스트

1. **Nginx 설정 생성**
   ```python
   def test_nginx_config_generation():
       builder = NginxConfigBuilder("tunnel.example.com")
       builder.add_path("app1", "app1.local")
       builder.add_path("app2", "app2.local", {
           "rate_limit": "10r/s"
       })
       
       config = builder.build()
       
       assert "server_name tunnel.example.com" in config
       assert "location ~ ^/app1/" in config
       assert "proxy_set_header Host app1.local" in config
       assert "limit_req" in config  # rate limiting
   ```

2. **SSL 설정**
   ```python
   def test_ssl_configuration():
       builder = NginxConfigBuilder("tunnel.example.com")
       builder.set_ssl(
           "/etc/ssl/cert.pem",
           "/etc/ssl/key.pem"
       )
       
       config = builder.build()
       
       assert "listen 443 ssl http2" in config
       assert "ssl_certificate /etc/ssl/cert.pem" in config
       assert "ssl_protocols TLSv1.2 TLSv1.3" in config
   ```

3. **FRP 서버 설정**
   ```python
   def test_frp_server_config():
       config = FRPServerConfig()
       config.set_auth("secret123")
       config.set_dashboard(7500, "admin", "password")
       config.add_allowed_ports([20000, 30000])
       
       ini_content = config.generate_ini()
       
       assert "[common]" in ini_content
       assert "bind_port = 7000" in ini_content
       assert "token = secret123" in ini_content
       assert "allow_ports = 20000-30000" in ini_content
   ```

4. **Systemd 서비스 생성**
   ```python
   def test_systemd_service():
       config = FRPServerConfig()
       service = config.generate_systemd_service()
       
       assert "[Unit]" in service
       assert "Description=FRP Server" in service
       assert "ExecStart=/usr/local/bin/frps" in service
       assert "Restart=always" in service
   ```

### 통합 테스트

1. **완전한 서버 설정**
   ```python
   @pytest.mark.integration
   def test_complete_server_setup():
       setup = ServerSetup("test.example.com")
       
       # 경로 추가
       setup.nginx_config.add_path("api", "api.local")
       setup.nginx_config.add_path("web", "web.local")
       
       # FRP 설정
       setup.frp_config.set_auth("test_token")
       
       # 설정 파일 생성
       with tempfile.TemporaryDirectory() as tmpdir:
           nginx_path = os.path.join(tmpdir, "nginx.conf")
           frp_path = os.path.join(tmpdir, "frps.ini")
           
           setup.nginx_config.write_config(nginx_path)
           with open(frp_path, 'w') as f:
               f.write(setup.frp_config.generate_ini())
           
           # 설정 검증
           assert os.path.exists(nginx_path)
           assert os.path.exists(frp_path)
   ```

2. **설치 스크립트 생성**
   ```python
   def test_setup_script_generation():
       setup = ServerSetup("tunnel.example.com")
       script = setup.generate_setup_script()
       
       assert "#!/bin/bash" in script
       assert "apt-get install nginx" in script
       assert "wget https://github.com/fatedier/frp" in script
       assert "systemctl enable frps" in script
   ```

## 구현 상세

### Nginx 설정 템플릿
```python
NGINX_SERVER_TEMPLATE = """
server {{
    listen 80;
    listen [::]:80;
    server_name {domain};
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {domain};
    
    # SSL Configuration
    ssl_certificate {ssl_cert};
    ssl_certificate_key {ssl_key};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    
    # Logging
    access_log /var/log/nginx/{domain}_access.log;
    error_log /var/log/nginx/{domain}_error.log;
    
    # Path-based routing
    {locations}
}}
"""

NGINX_LOCATION_TEMPLATE = """
    location ~ ^/{path}/(.*) {{
        # Rate limiting (optional)
        {rate_limit}
        
        # Proxy settings
        proxy_pass http://127.0.0.1:{frp_port};
        proxy_http_version 1.1;
        
        # Headers
        proxy_set_header Host {vhost};
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Original-URI $request_uri;
        proxy_set_header X-Forwarded-Path /{path};
        
        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        
        # Timeouts
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
        
        # Custom headers
        {custom_headers}
    }}
"""
```

### 설치 스크립트 템플릿
```bash
#!/bin/bash
set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}FRP Server Setup Script${NC}"
echo "Domain: {domain}"
echo ""

# 1. 시스템 업데이트
echo -e "${YELLOW}Updating system packages...${NC}"
apt-get update && apt-get upgrade -y

# 2. Nginx 설치
echo -e "${YELLOW}Installing Nginx...${NC}"
apt-get install -y nginx certbot python3-certbot-nginx

# 3. FRP 다운로드 및 설치
echo -e "${YELLOW}Installing FRP...${NC}"
FRP_VERSION="0.51.0"
wget https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_amd64.tar.gz
tar -xzf frp_${FRP_VERSION}_linux_amd64.tar.gz
cp frp_${FRP_VERSION}_linux_amd64/frps /usr/local/bin/
chmod +x /usr/local/bin/frps

# 4. 설정 파일 복사
echo -e "${YELLOW}Copying configuration files...${NC}"
cp nginx.conf /etc/nginx/sites-available/{domain}
ln -sf /etc/nginx/sites-available/{domain} /etc/nginx/sites-enabled/
cp frps.ini /etc/frp/frps.ini

# 5. Systemd 서비스 설정
echo -e "${YELLOW}Setting up systemd services...${NC}"
cp frps.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable frps
systemctl start frps

# 6. SSL 인증서 설정
echo -e "${YELLOW}Setting up SSL certificate...${NC}"
certbot --nginx -d {domain} --non-interactive --agree-tos -m {email}

# 7. 방화벽 설정
echo -e "${YELLOW}Configuring firewall...${NC}"
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 7000/tcp
ufw allow 7500/tcp

# 8. 서비스 시작
echo -e "${YELLOW}Starting services...${NC}"
nginx -t && systemctl reload nginx

echo -e "${GREEN}Setup completed successfully!${NC}"
```

## 파일 구조
```
server_setup/
├── nginx_config.py     # Nginx 설정 생성기
├── frp_config.py       # FRP 서버 설정
├── server_setup.py     # 통합 설정 도구
├── server_manager.py   # 서버 관리 도구
├── templates/
│   ├── nginx.conf.j2
│   ├── frps.ini.j2
│   └── setup.sh.j2
├── scripts/
│   ├── install.sh
│   ├── upgrade.sh
│   └── uninstall.sh
└── README.md

tests/
├── test_nginx_config.py
├── test_frp_config.py
├── test_server_setup.py
└── test_templates.py
```

## 완료 기준

### 필수 기능
- [x] Nginx 설정 생성기
- [x] FRP 서버 설정 관리
- [x] SSL 통합
- [x] 설치 스크립트
- [x] Systemd 서비스

### 테스트
- [x] 설정 파일 생성 테스트
- [x] 템플릿 렌더링 테스트
- [x] 스크립트 검증
- [x] 통합 설정 테스트

### 문서
- [x] 서버 설정 가이드
- [x] 보안 권장사항
- [x] 문제 해결 가이드

## 예상 작업 시간
- Nginx 설정 생성기: 4시간
- FRP 서버 설정: 3시간
- 설치 스크립트: 3시간
- 테스트 작성: 4시간
- 문서화: 2시간

**총 예상 시간**: 16시간 (3일)

## 다음 단계 준비
- 모니터링 시스템
- 로깅 통합
- 메트릭 수집

## 의존성
- Nginx
- Let's Encrypt
- systemd
- Python 3.8+

## 주의사항
- 보안 설정 확인
- SSL 인증서 자동 갱신
- 방화벽 규칙 검증
- 백업 전략