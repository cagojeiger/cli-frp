# Checkpoint 6: FRP 서버 설정 도구

## 개요
FRP 서버 설정 및 관리를 자동화하는 도구를 제공합니다. locations 기능을 활용한 경로 기반 라우팅을 위한 서버 측 설정을 간소화합니다.

## 목표
- FRP 서버 설정 파일 자동 생성
- SSL/TLS 인증서 관리
- 서버 모니터링 및 관리
- 설치 및 배포 스크립트

## 구현 범위

### 1. FRP 서버 설정 생성기
```python
@dataclass
class FRPServerConfig:
    """FRP 서버 설정"""
    bind_port: int = 7000
    vhost_http_port: int = 80
    vhost_https_port: int = 443
    dashboard_port: int = 7500
    token: Optional[str] = None
    subdomain_host: str = "tunnel.example.com"
    
class FRPServerConfigBuilder:
    """FRP 서버 설정을 동적으로 생성하는 클래스"""
    
    def __init__(self, domain: str):
        self.domain = domain
        self.config = FRPServerConfig()
        
    def set_ports(self, bind_port: int = 7000, http_port: int = 80, https_port: int = 443):
        """포트 설정"""
        
    def enable_dashboard(self, port: int = 7500, user: str = "admin", password: str = None):
        """대시보드 활성화"""
        
    def set_auth_token(self, token: str):
        """인증 토큰 설정"""
        
    def generate_config(self) -> str:
        """FRP 서버 TOML 설정 생성"""
```

### 2. SSL 인증서 관리
```python
class SSLManager:
    """SSL 인증서 관리"""
    
    def __init__(self, domain: str, email: str):
        self.domain = domain
        self.email = email
        
    def setup_certbot(self) -> bool:
        """Certbot 설정 및 인증서 발급"""
        
    def renew_certificates(self) -> bool:
        """인증서 갱신"""
        
    def get_cert_paths(self) -> Tuple[str, str]:
        """인증서 파일 경로 반환"""
```

### 3. 서버 관리자
```python
class FRPServerManager:
    """FRP 서버 관리"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        
    def start_server(self) -> ProcessId:
        """FRP 서버 시작"""
        
    def stop_server(self, process_id: ProcessId) -> bool:
        """FRP 서버 중지"""
        
    def reload_config(self) -> bool:
        """설정 리로드"""
        
    def get_server_status(self) -> Dict[str, Any]:
        """서버 상태 확인"""
```

## 테스트 시나리오

### 유닛 테스트

1. **FRP 서버 설정 생성**
   ```python
   def test_frp_server_config_generation():
       builder = FRPServerConfigBuilder("tunnel.example.com")
       builder.set_ports(7000, 80, 443)
       builder.enable_dashboard(7500, "admin", "secret")
       
       config = builder.generate_config()
       
       assert "bindPort = 7000" in config
       assert "vhostHTTPPort = 80" in config
       assert "vhostHTTPSPort = 443" in config
       assert "[webServer]" in config
       assert "port = 7500" in config
   ```

2. **SSL 관리**
   ```python
   def test_ssl_certificate_setup():
       ssl_manager = SSLManager("tunnel.example.com", "admin@example.com")
       
       # Mock certbot operations
       result = ssl_manager.setup_certbot()
       assert result is True
       
       cert_path, key_path = ssl_manager.get_cert_paths()
       assert cert_path.endswith("fullchain.pem")
       assert key_path.endswith("privkey.pem")
   ```

### 통합 테스트

1. **전체 서버 설정**
   ```python
   def test_complete_server_setup():
       # 1. 설정 생성
       builder = FRPServerConfigBuilder("tunnel.example.com")
       config = builder.generate_config()
       
       # 2. 설정 파일 저장
       config_path = "/tmp/frps.toml"
       with open(config_path, 'w') as f:
           f.write(config)
       
       # 3. 서버 시작
       manager = FRPServerManager(config_path)
       process_id = manager.start_server()
       
       # 4. 상태 확인
       status = manager.get_server_status()
       assert status['running'] is True
   ```

## 배포 스크립트

### 자동 설치 스크립트
```bash
#!/bin/bash
# install-frp-server.sh

set -e

DOMAIN=${1:-"tunnel.example.com"}
EMAIL=${2:-"admin@example.com"}
FRP_VERSION=${3:-"0.52.3"}

echo "Installing FRP Server for domain: $DOMAIN"

# 1. FRP 바이너리 다운로드
wget https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_amd64.tar.gz
tar -xzf frp_${FRP_VERSION}_linux_amd64.tar.gz
sudo mv frp_${FRP_VERSION}_linux_amd64/frps /usr/local/bin/
sudo chmod +x /usr/local/bin/frps

# 2. 설정 디렉토리 생성
sudo mkdir -p /etc/frp
sudo mkdir -p /var/log/frp

# 3. Systemd 서비스 설정
sudo tee /etc/systemd/system/frps.service > /dev/null <<EOF
[Unit]
Description=FRP Server
After=network.target

[Service]
Type=simple
User=frp
Group=frp
ExecStart=/usr/local/bin/frps -c /etc/frp/frps.toml
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# 4. 사용자 생성
sudo useradd -r -s /bin/false frp || true
sudo chown -R frp:frp /etc/frp /var/log/frp

# 5. SSL 인증서 설정 (Let's Encrypt)
sudo apt-get update
sudo apt-get install -y certbot

# 6. 방화벽 설정
sudo ufw allow 7000/tcp  # FRP control port
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

echo "FRP Server installation completed!"
echo "Edit /etc/frp/frps.toml and run: sudo systemctl start frps"
```

## 파일 구조
```
frp_wrapper/
├── server/
│   ├── config_builder.py   # FRP 서버 설정 생성기
│   ├── ssl_manager.py      # SSL 인증서 관리
│   ├── server_manager.py   # 서버 관리
│   └── installer.py        # 설치 도구

scripts/
├── install-frp-server.sh   # 자동 설치 스크립트
├── setup-ssl.sh           # SSL 설정 스크립트
└── frps.toml.template     # 서버 설정 템플릿

tests/
├── test_server_config.py
├── test_ssl_manager.py
└── test_server_manager.py
```

## 완료 기준

### 필수 기능
- [ ] FRP 서버 설정 생성기
- [ ] SSL 인증서 관리
- [ ] 서버 프로세스 관리
- [ ] 자동 설치 스크립트

### 테스트
- [ ] 설정 생성 테스트
- [ ] SSL 관리 테스트
- [ ] 서버 관리 테스트
- [ ] 통합 테스트

### 문서
- [ ] 서버 설정 가이드
- [ ] SSL 설정 가이드
- [ ] 배포 가이드

## 예상 작업 시간
- FRP 서버 설정 생성기: 3시간
- SSL 관리: 2시간
- 서버 관리자: 3시간
- 배포 스크립트: 2시간
- 테스트 작성: 3시간
- 문서화: 2시간

**총 예상 시간**: 15시간 (3.75일)

## 다음 단계 준비
- 모니터링 시스템 연동
- 로그 관리 개선
- 백업 및 복구 기능

## 의존성
- Checkpoint 1-5 완료
- FRP 서버 설정 이해
- SSL/TLS 인증서 지식
- Linux 시스템 관리

## 주의사항
- 보안 설정 철저히 (방화벽, 인증서)
- 서버 재시작 시 자동 복구
- 로그 로테이션 설정
- 모니터링 시스템 연동