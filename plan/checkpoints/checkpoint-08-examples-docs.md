# Checkpoint 8: 예제 및 문서

## 개요
실용적인 예제 코드를 작성하고 완성된 문서를 제공합니다. 사용자가 쉽게 시작할 수 있도록 다양한 사용 사례를 다루는 예제와 상세한 문서를 작성합니다.

## 목표
- 다양한 사용 사례를 다루는 예제 코드
- 완성된 API 문서
- 사용자 가이드 및 튜토리얼
- 패키지 배포 준비

## 구현 범위

### 1. 기본 예제 모음
```python
# examples/01_basic_tcp_tunnel.py
"""
기본 TCP 터널 생성 예제
로컬 포트를 외부에 노출하는 가장 간단한 방법
"""
from frp_wrapper import FRPClient

def basic_tcp_tunnel():
    # 클라이언트 생성 및 연결
    client = FRPClient("tunnel.example.com", auth_token="your_token")
    client.connect()
    
    # TCP 터널 생성 (로컬 3000번 -> 외부 8080번)
    tunnel = client.expose_tcp(local_port=3000, remote_port=8080)
    
    print(f"터널이 생성되었습니다!")
    print(f"접속 주소: {client.server}:8080")
    print(f"터널 ID: {tunnel.id}")
    
    # 계속 실행
    try:
        input("Enter 키를 누르면 터널이 종료됩니다...")
    finally:
        tunnel.close()
        client.disconnect()

# examples/02_http_subpath_tunnel.py
"""
HTTP 서브패스 터널 예제
로컬 웹 서비스를 서브패스로 노출
"""
from frp_wrapper import FRPClient

def http_subpath_tunnel():
    # Context Manager 사용
    with FRPClient("tunnel.example.com") as client:
        # /myapp 경로로 노출
        with client.tunnel(3000, "myapp") as tunnel:
            print(f"웹 서비스가 노출되었습니다!")
            print(f"접속 URL: {tunnel.url}")
            print(f"로컬 포트: 3000 -> {tunnel.url}")
            
            input("Enter 키를 누르면 종료됩니다...")

# examples/03_multiple_tunnels.py
"""
다중 터널 관리 예제
여러 서비스를 동시에 노출
"""
from frp_wrapper import FRPClient, TunnelGroup

def multiple_tunnels():
    with FRPClient("tunnel.example.com") as client:
        # TunnelGroup으로 여러 터널 관리
        with TunnelGroup(client) as group:
            # 프론트엔드 (React)
            group.add(3000, "frontend")
            
            # 백엔드 API (FastAPI)
            group.add(8000, "api", strip_path=False)
            
            # 관리자 패널
            group.add(3001, "admin")
            
            # TCP 터널 (SSH)
            group.add(22, None, remote_port=2222)
            
            print("모든 터널이 활성화되었습니다:")
            for tunnel in group.tunnels:
                if hasattr(tunnel, 'url'):
                    print(f"- {tunnel.url}")
                else:
                    print(f"- TCP {client.server}:{tunnel.config.remote_port}")
                    
            input("Enter 키를 누르면 모든 터널이 종료됩니다...")
```

### 2. 실용적인 사용 사례
```python
# examples/04_dev_environment.py
"""
개발 환경 공유 예제
로컬 개발 서버를 팀원과 공유
"""
from frp_wrapper import FRPClient
import subprocess
import time

def share_dev_environment():
    # React 개발 서버 시작
    dev_server = subprocess.Popen(
        ["npm", "start"],
        cwd="./my-react-app"
    )
    
    # 서버 시작 대기
    time.sleep(5)
    
    try:
        with FRPClient("tunnel.example.com") as client:
            # 개발 서버 노출 (WebSocket 지원)
            with client.expose_path(
                3000, 
                "dev-preview",
                websocket=True,  # HMR 지원
                custom_headers={
                    "X-Dev-Server": "React",
                    "Cache-Control": "no-cache"
                }
            ) as tunnel:
                print(f"개발 서버가 공유되었습니다!")
                print(f"공유 URL: {tunnel.url}")
                print(f"WebSocket (HMR) 지원: ✓")
                
                input("Enter 키를 누르면 종료됩니다...")
    finally:
        dev_server.terminate()

# examples/05_api_gateway.py
"""
API 게이트웨이 예제
마이크로서비스를 하나의 도메인으로 통합
"""
from frp_wrapper import FRPClient
import asyncio

async def api_gateway():
    services = {
        "auth": {"port": 3001, "path": "api/auth"},
        "users": {"port": 3002, "path": "api/users"},
        "products": {"port": 3003, "path": "api/products"},
        "orders": {"port": 3004, "path": "api/orders"}
    }
    
    with FRPClient("api.example.com") as client:
        tunnels = {}
        
        # 모든 서비스 노출
        for name, config in services.items():
            tunnel = client.expose_path(
                config["port"],
                config["path"],
                strip_path=False,  # API 경로 유지
                custom_headers={
                    "X-Service-Name": name,
                    "X-API-Version": "v1"
                }
            )
            tunnels[name] = tunnel
            
        print("API Gateway 구성 완료:")
        for name, tunnel in tunnels.items():
            print(f"- {name}: {tunnel.url}")
            
        # 상태 모니터링
        while True:
            await asyncio.sleep(30)
            for name, tunnel in tunnels.items():
                if tunnel.status != "connected":
                    print(f"경고: {name} 서비스 연결 끊김")

# examples/06_webhook_receiver.py
"""
Webhook 수신 예제
외부 서비스의 webhook을 로컬에서 받기
"""
from frp_wrapper import FRPClient, temporary_tunnel
from flask import Flask, request, jsonify
import threading

def webhook_receiver():
    app = Flask(__name__)
    received_webhooks = []
    
    @app.route('/webhook', methods=['POST'])
    def handle_webhook():
        data = request.json
        received_webhooks.append(data)
        print(f"Webhook 수신: {data}")
        return jsonify({"status": "received"}), 200
        
    # Flask 서버를 별도 스레드에서 실행
    server_thread = threading.Thread(
        target=lambda: app.run(port=5000, debug=False)
    )
    server_thread.daemon = True
    server_thread.start()
    
    # 임시 터널 생성
    with temporary_tunnel(
        "tunnel.example.com",
        5000,
        "webhook-test"
    ) as tunnel:
        print(f"Webhook URL: {tunnel.url}webhook")
        print("이 URL을 외부 서비스에 등록하세요.")
        print(f"수신된 webhook 수: {len(received_webhooks)}")
        
        input("Enter 키를 누르면 종료됩니다...")
```

### 3. 고급 예제
```python
# examples/07_monitoring_integration.py
"""
모니터링 통합 예제
터널 상태를 실시간으로 모니터링
"""
from frp_wrapper import FRPClient, EventType
import time

def monitoring_example():
    client = FRPClient("tunnel.example.com")
    
    # 이벤트 핸들러 등록
    @client.on(EventType.TUNNEL_CONNECTED)
    def on_tunnel_connected(data):
        print(f"✅ 터널 연결됨: {data['tunnel_id']}")
        
    @client.on(EventType.TUNNEL_DISCONNECTED)
    def on_tunnel_disconnected(data):
        print(f"❌ 터널 연결 끊김: {data['tunnel_id']}")
        
    @client.on(EventType.METRIC_THRESHOLD)
    def on_metric_threshold(data):
        print(f"⚠️  메트릭 임계값 초과: {data['metric_name']} = {data['value']}")
    
    # 모니터링 대시보드 시작
    client.start_dashboard(port=9999)
    print("모니터링 대시보드: http://localhost:9999")
    
    with client:
        # 여러 터널 생성
        tunnels = []
        for i in range(3):
            tunnel = client.expose_tcp(3000 + i, 8080 + i)
            tunnels.append(tunnel)
            
        # 주기적으로 메트릭 출력
        while True:
            time.sleep(10)
            print("\n--- 터널 상태 ---")
            for tunnel in tunnels:
                metrics = client.get_tunnel_metrics(tunnel.id)
                print(f"{tunnel.id}: {metrics.bytes_sent} bytes sent, "
                      f"{metrics.connection_count} connections")

# examples/08_production_deployment.py
"""
프로덕션 배포 예제
안정적인 프로덕션 환경 구성
"""
from frp_wrapper import FRPClient
import logging
import signal
import sys

class ProductionTunnelManager:
    def __init__(self, config_file: str):
        self.config = self._load_config(config_file)
        self.client = None
        self.tunnels = []
        self._setup_logging()
        self._setup_signal_handlers()
        
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('tunnel.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def _setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        self.logger.info(f"Signal {signum} received, shutting down...")
        self.shutdown()
        sys.exit(0)
        
    def start(self):
        self.logger.info("Starting production tunnel manager...")
        
        self.client = FRPClient(
            self.config['server'],
            auth_token=self.config['auth_token'],
            auto_reconnect=True,
            reconnect_interval=30
        )
        
        self.client.connect()
        
        # 설정된 모든 터널 생성
        for tunnel_config in self.config['tunnels']:
            tunnel = self._create_tunnel(tunnel_config)
            self.tunnels.append(tunnel)
            self.logger.info(f"Tunnel created: {tunnel.id} -> {tunnel.url}")
            
    def _create_tunnel(self, config):
        if config['type'] == 'http':
            return self.client.expose_path(
                config['local_port'],
                config['path'],
                **config.get('options', {})
            )
        elif config['type'] == 'tcp':
            return self.client.expose_tcp(
                config['local_port'],
                config.get('remote_port')
            )
            
    def shutdown(self):
        self.logger.info("Shutting down tunnels...")
        if self.client:
            self.client.close_all_tunnels()
            self.client.disconnect()
```

### 4. 문서 구조
```markdown
# docs/README.md
# FRP Python Wrapper

간단하고 직관적인 Python API로 FRP 터널을 관리하세요.

## 특징
- 🚀 5분 안에 시작 가능
- 🔧 프로그래밍 방식의 터널 관리
- 🌐 서브패스 기반 HTTP 라우팅
- 🔄 자동 재연결
- 📊 실시간 모니터링
- 🐍 Pythonic API (Context Manager 지원)

## 빠른 시작
```python
from frp_wrapper import FRPClient

# 터널 생성
with FRPClient("tunnel.example.com") as client:
    with client.tunnel(3000, "myapp") as tunnel:
        print(f"접속 URL: {tunnel.url}")
        input("Enter를 눌러 종료...")
```

# docs/api-reference.md
# API Reference

## FRPClient

메인 클라이언트 클래스입니다.

### 초기화
```python
client = FRPClient(
    server: str,
    port: int = 7000,
    auth_token: Optional[str] = None,
    binary_path: Optional[str] = None,
    auto_reconnect: bool = True,
    **options
)
```

### 메서드

#### connect()
서버에 연결합니다.

#### disconnect()
서버 연결을 종료합니다.

#### expose_tcp(local_port, remote_port=None)
TCP 포트를 외부에 노출합니다.

#### expose_path(local_port, path, **options)
HTTP 서비스를 서브패스로 노출합니다.

...

# docs/deployment-guide.md
# 배포 가이드

## 서버 설정

### 1. 필수 구성 요소
- Ubuntu 20.04+ 또는 CentOS 8+
- Nginx 1.18+
- Python 3.8+
- 도메인 및 SSL 인증서

### 2. 서버 설치
```bash
# 자동 설치 스크립트
curl -sSL https://example.com/install.sh | bash

# 또는 수동 설치
apt-get update
apt-get install -y nginx certbot python3-certbot-nginx
```

...
```

## 테스트 시나리오

### 예제 코드 테스트
```python
def test_all_examples():
    """모든 예제가 정상 실행되는지 확인"""
    examples_dir = Path("examples")
    
    for example_file in examples_dir.glob("*.py"):
        # 각 예제를 subprocess로 실행
        result = subprocess.run(
            [sys.executable, str(example_file), "--test-mode"],
            capture_output=True,
            timeout=30
        )
        
        assert result.returncode == 0, f"Example {example_file} failed"
```

### 문서 검증
```python
def test_documentation_links():
    """문서 내 모든 링크가 유효한지 확인"""
    docs_dir = Path("docs")
    
    for doc_file in docs_dir.rglob("*.md"):
        content = doc_file.read_text()
        links = extract_links(content)
        
        for link in links:
            if link.startswith("http"):
                response = requests.head(link)
                assert response.status_code < 400
```

## 파일 구조
```
examples/
├── 01_basic_tcp_tunnel.py
├── 02_http_subpath_tunnel.py
├── 03_multiple_tunnels.py
├── 04_dev_environment.py
├── 05_api_gateway.py
├── 06_webhook_receiver.py
├── 07_monitoring_integration.py
├── 08_production_deployment.py
├── config/
│   ├── dev_config.yaml
│   └── prod_config.yaml
└── README.md

docs/
├── README.md
├── quickstart.md
├── installation.md
├── api-reference.md
├── deployment-guide.md
├── troubleshooting.md
├── changelog.md
└── contributing.md

tests/
├── test_examples.py
├── test_documentation.py
└── test_integration.py
```

## 완료 기준

### 필수 항목
- [x] 8개 이상의 실용적 예제
- [x] 완성된 API 문서
- [x] 배포 가이드
- [x] 문제 해결 가이드
- [x] 기여 가이드

### 테스트
- [x] 모든 예제 실행 가능
- [x] 문서 링크 검증
- [x] 코드 블록 구문 검증
- [x] 패키지 설치 테스트

### 배포 준비
- [x] setup.py 작성
- [x] PyPI 패키지 메타데이터
- [x] GitHub Actions CI/CD
- [x] 버전 관리

## 예상 작업 시간
- 예제 코드 작성: 5시간
- API 문서: 3시간
- 사용자 가이드: 3시간
- 배포 준비: 2시간
- 테스트: 2시간

**총 예상 시간**: 15시간 (3일)

## 체크리스트

### 예제 코드
- [ ] 각 예제에 상세한 주석
- [ ] 실행 가능한 완전한 코드
- [ ] 오류 처리 포함
- [ ] 베스트 프랙티스 적용

### 문서
- [ ] 명확한 설치 방법
- [ ] 단계별 튜토리얼
- [ ] API 전체 커버
- [ ] 실제 사용 사례

### 품질
- [ ] 코드 스타일 일관성
- [ ] 타입 힌트 완성도
- [ ] 테스트 커버리지 95%+
- [ ] 문서 오타 검사

## 릴리스 준비

### 버전 1.0.0 체크리스트
- [ ] 모든 테스트 통과
- [ ] 문서 검토 완료
- [ ] 보안 취약점 스캔
- [ ] 성능 벤치마크
- [ ] 라이선스 확인
- [ ] CHANGELOG 업데이트
- [ ] 릴리스 노트 작성

### 배포 프로세스
1. 버전 태그 생성
2. GitHub Release 생성
3. PyPI 업로드
4. 문서 사이트 업데이트
5. 공지사항 작성