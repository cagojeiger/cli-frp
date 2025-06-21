# 보안 고려사항

## 개요

FRP Python Wrapper를 안전하게 사용하기 위한 보안 가이드라인과 베스트 프랙티스를 제공합니다.

## 보안 위협 모델

### 1. 네트워크 레벨 위협
- **중간자 공격 (MITM)**: 암호화되지 않은 트래픽 가로채기
- **포트 스캐닝**: 노출된 포트를 통한 서비스 탐색
- **DDoS 공격**: 서비스 가용성 공격
- **IP 스푸핑**: 허용된 IP 주소 위장

### 2. 애플리케이션 레벨 위협
- **인증 우회**: 약한 토큰 또는 인증 메커니즘
- **권한 상승**: 허용되지 않은 리소스 접근
- **인젝션 공격**: 설정 파일 또는 명령어 인젝션
- **정보 노출**: 로그 또는 에러 메시지를 통한 정보 유출

### 3. 시스템 레벨 위협
- **프로세스 하이재킹**: FRP 프로세스 제어 탈취
- **파일 시스템 공격**: 설정 파일 변조
- **리소스 고갈**: 메모리/CPU 과다 사용
- **권한 문제**: 과도한 시스템 권한

## 보안 설정

### 1. 인증 및 암호화

#### 토큰 기반 인증
```python
import secrets

# 강력한 토큰 생성
def generate_secure_token(length: int = 32) -> str:
    """암호학적으로 안전한 토큰 생성"""
    return secrets.token_urlsafe(length)

# 클라이언트 설정
client = FRPClient(
    server="tunnel.example.com",
    auth_token=os.environ.get("FRP_AUTH_TOKEN"),  # 환경 변수 사용
    tls_enable=True,  # TLS 필수
    tls_verify=True   # 인증서 검증
)
```

#### TLS/SSL 설정
```python
# 서버 측 TLS 설정
server_config = FRPServerConfig()
server_config.set_tls(
    cert_file="/etc/ssl/certs/server.crt",
    key_file="/etc/ssl/private/server.key",
    ca_file="/etc/ssl/certs/ca.crt",  # 클라이언트 인증서 검증
    verify_client=True
)

# 클라이언트 측 TLS 설정
client_options = {
    "tls_enable": True,
    "tls_cert_file": "/etc/ssl/certs/client.crt",
    "tls_key_file": "/etc/ssl/private/client.key",
    "tls_trusted_ca_file": "/etc/ssl/certs/ca.crt",
    "tls_server_name": "tunnel.example.com"  # SNI
}
```

### 2. 접근 제어

#### IP 화이트리스트
```python
# 터널별 IP 제한
tunnel = client.expose_path(
    local_port=8000,
    path="admin",
    allowed_ips=[
        "192.168.1.0/24",    # 내부 네트워크
        "10.0.0.0/8",        # VPN 네트워크
        "203.0.113.5/32"     # 특정 IP
    ]
)

# 전역 IP 제한 (서버 설정)
server_config.set_allowed_ips([
    "0.0.0.0/0",  # 기본적으로 모두 허용
    "!192.168.0.0/16",  # 특정 대역 차단
])
```

#### 포트 제한
```ini
# frps.ini
[common]
allow_ports = 2000-3000,8080,8443
# 특정 포트만 허용
```

#### HTTP 기본 인증
```python
tunnel = client.expose_path(
    local_port=3000,
    path="private",
    basic_auth="admin:secure_password_hash"
)
```

### 3. Rate Limiting

#### Nginx 레벨
```nginx
# 요청 속도 제한
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location ~ ^/api/(.*) {
    limit_req zone=api_limit burst=20 nodelay;
    limit_req_status 429;
    
    proxy_pass http://localhost:8080;
}
```

#### 애플리케이션 레벨
```python
from frp_wrapper.security import RateLimiter

rate_limiter = RateLimiter(
    requests_per_second=10,
    burst_size=20
)

tunnel = client.expose_path(
    local_port=8000,
    path="api",
    middleware=[rate_limiter]
)
```

## 보안 베스트 프랙티스

### 1. 최소 권한 원칙

#### 시스템 사용자
```bash
# FRP 전용 사용자 생성
sudo useradd -r -s /bin/false frp
sudo chown -R frp:frp /etc/frp
sudo chown -R frp:frp /var/log/frp

# systemd 서비스 설정
[Service]
User=frp
Group=frp
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/frp
```

#### 파일 권한
```bash
# 설정 파일 권한
chmod 600 /etc/frp/frpc.ini
chmod 600 ~/.frp_wrapper/config.yaml

# 바이너리 권한
chmod 755 /usr/local/bin/frpc
chmod 755 /usr/local/bin/frps
```

### 2. 보안 헤더

#### HTTP 보안 헤더
```python
security_headers = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}

tunnel = client.expose_path(
    local_port=3000,
    path="app",
    custom_headers=security_headers
)
```

### 3. 로깅 및 모니터링

#### 보안 로깅
```python
from frp_wrapper.security import SecurityLogger

security_logger = SecurityLogger()

# 보안 이벤트 로깅
@client.on(EventType.AUTHENTICATION_FAILED)
def on_auth_failed(data):
    security_logger.log_auth_failure(
        ip=data['remote_ip'],
        reason=data['reason']
    )

@client.on(EventType.SUSPICIOUS_ACTIVITY)
def on_suspicious(data):
    security_logger.log_suspicious_activity(
        tunnel_id=data['tunnel_id'],
        activity=data['activity']
    )
```

#### 감사 로그
```python
# 모든 터널 생성/삭제 기록
audit_config = {
    "enabled": True,
    "log_file": "/var/log/frp/audit.log",
    "include_payload": False,  # 민감한 데이터 제외
    "retention_days": 90
}

client = FRPClient(
    server="tunnel.example.com",
    audit_config=audit_config
)
```

### 4. 입력 검증

#### 경로 검증
```python
import re

def validate_path(path: str) -> bool:
    """안전한 경로 검증"""
    # 허용된 문자만 포함
    if not re.match(r'^[a-zA-Z0-9_-]+$', path):
        return False
    
    # 예약된 경로 차단
    reserved_paths = ['admin', 'api', 'health', 'metrics']
    if path.lower() in reserved_paths:
        return False
    
    # 길이 제한
    if len(path) > 50:
        return False
    
    return True

# 사용
if validate_path(user_input_path):
    tunnel = client.expose_path(3000, user_input_path)
else:
    raise ValueError("Invalid path")
```

#### 포트 검증
```python
def validate_port(port: int) -> bool:
    """안전한 포트 범위 검증"""
    # 시스템 포트 차단
    if port < 1024:
        return False
    
    # 알려진 서비스 포트 차단
    blocked_ports = [3306, 5432, 6379, 27017]  # DB 포트들
    if port in blocked_ports:
        return False
    
    # 유효한 범위
    if not 1024 <= port <= 65535:
        return False
    
    return True
```

## 보안 설정 예제

### 개발 환경
```yaml
# dev-security.yaml
security:
  tls_enable: false  # 로컬 개발은 TLS 선택적
  auth_token: ${DEV_TOKEN}
  allowed_ips:
    - 127.0.0.1/32
    - 10.0.0.0/8
  log_level: debug
  audit: false
```

### 프로덕션 환경
```yaml
# prod-security.yaml
security:
  tls_enable: true
  tls_verify: true
  tls_cert_file: /etc/ssl/certs/client.crt
  tls_key_file: /etc/ssl/private/client.key
  auth_token: ${PROD_TOKEN}  # 환경 변수 필수
  allowed_ips:
    - 10.0.0.0/8      # 내부 네트워크
    - 172.16.0.0/12   # Docker 네트워크
  rate_limit:
    requests_per_second: 100
    burst: 200
  log_level: warning
  audit: true
  audit_file: /var/log/frp/audit.log
  
tunnels:
  - name: api
    type: http
    local_port: 8000
    path: api
    security:
      basic_auth: ${API_BASIC_AUTH}
      allowed_methods: ["GET", "POST"]
      allowed_origins: ["https://app.example.com"]
      csrf_protection: true
```

## 보안 체크리스트

### 배포 전 확인사항

- [ ] **인증**
  - [ ] 강력한 토큰 사용 (최소 32자)
  - [ ] 토큰을 환경 변수로 관리
  - [ ] 정기적 토큰 교체 정책

- [ ] **암호화**
  - [ ] 프로덕션에서 TLS 활성화
  - [ ] 유효한 SSL 인증서 사용
  - [ ] 인증서 만료 모니터링

- [ ] **접근 제어**
  - [ ] IP 화이트리스트 설정
  - [ ] 불필요한 포트 차단
  - [ ] Rate limiting 적용

- [ ] **시스템 보안**
  - [ ] 전용 사용자로 실행
  - [ ] 파일 권한 확인 (600)
  - [ ] 최소 권한 원칙 적용

- [ ] **로깅 및 모니터링**
  - [ ] 보안 이벤트 로깅
  - [ ] 이상 징후 감지
  - [ ] 로그 보관 정책

- [ ] **업데이트**
  - [ ] FRP 최신 버전 사용
  - [ ] 정기적 보안 패치
  - [ ] 의존성 취약점 스캔

## 사고 대응

### 보안 사고 발생 시

1. **즉시 조치**
   ```python
   # 모든 터널 즉시 종료
   client.emergency_shutdown()
   
   # 특정 터널만 차단
   client.block_tunnel(tunnel_id)
   ```

2. **조사**
   - 감사 로그 확인
   - 접속 기록 분석
   - 시스템 로그 검토

3. **복구**
   - 토큰 재발급
   - IP 화이트리스트 업데이트
   - 보안 설정 강화

4. **예방**
   - 사고 원인 분석
   - 보안 정책 업데이트
   - 모니터링 강화

## 보안 도구

### 취약점 스캔
```bash
# 의존성 취약점 검사
pip-audit

# 코드 보안 검사
bandit -r frp_wrapper/

# SAST 도구
semgrep --config=auto
```

### 침투 테스트
```python
from frp_wrapper.security import PenTestKit

# 자동 보안 테스트
pen_test = PenTestKit(client)
report = pen_test.run_all_tests()
print(report.summary())
```