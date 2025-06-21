# 문제 해결 가이드

## 일반적인 문제

### 연결 문제

#### 문제: "Connection refused" 오류
```python
ConnectionError: Connection refused to tunnel.example.com:7000
```

**원인**
- FRP 서버가 실행되지 않음
- 잘못된 서버 주소 또는 포트
- 방화벽이 연결 차단

**해결 방법**
```python
# 1. 서버 연결 테스트
import socket

def test_connection(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

if not test_connection("tunnel.example.com", 7000):
    print("서버에 연결할 수 없습니다")

# 2. 방화벽 확인 (Linux)
# sudo iptables -L -n | grep 7000
# sudo ufw status

# 3. 다른 포트 시도
client = FRPClient("tunnel.example.com", port=7001)
```

#### 문제: "Authentication failed" 오류
```python
AuthenticationError: Authentication failed: invalid token
```

**원인**
- 잘못된 인증 토큰
- 서버와 클라이언트의 토큰 불일치

**해결 방법**
```python
# 1. 토큰 확인
print(f"사용 중인 토큰: {client.auth_token[:5]}...")

# 2. 환경 변수 확인
import os
token = os.environ.get("FRP_AUTH_TOKEN")
if not token:
    print("FRP_AUTH_TOKEN 환경 변수가 설정되지 않았습니다")

# 3. 토큰 재설정
client = FRPClient(
    "tunnel.example.com",
    auth_token="correct_token_here"
)
```

#### 문제: "Connection timeout" 오류
```python
TimeoutError: Connection timeout after 10 seconds
```

**원인**
- 네트워크 지연
- 서버 과부하
- 잘못된 타임아웃 설정

**해결 방법**
```python
# 1. 타임아웃 증가
client = FRPClient(
    "tunnel.example.com",
    timeout=30  # 30초로 증가
)

# 2. 재시도 로직
import time

def connect_with_retry(max_attempts=3):
    for attempt in range(max_attempts):
        try:
            client.connect()
            return True
        except TimeoutError:
            if attempt < max_attempts - 1:
                wait_time = 2 ** attempt
                print(f"재시도 중... ({wait_time}초 대기)")
                time.sleep(wait_time)
    return False
```

### 터널 생성 문제

#### 문제: "Port already in use" 오류
```python
PortInUseError: Port 3000 is already in use
```

**원인**
- 다른 프로세스가 포트 사용 중
- 이전 터널이 정리되지 않음

**해결 방법**
```python
# 1. 포트 사용 확인
import psutil

def find_process_using_port(port):
    for conn in psutil.net_connections():
        if conn.laddr.port == port:
            return psutil.Process(conn.pid)
    return None

process = find_process_using_port(3000)
if process:
    print(f"포트 3000을 사용 중인 프로세스: {process.name()} (PID: {process.pid})")

# 2. 다른 포트 사용
try:
    tunnel = client.expose_path(3000, "app")
except PortInUseError:
    tunnel = client.expose_path(3001, "app")  # 다른 포트 시도

# 3. 자동 포트 찾기
def find_free_port(start=3000, end=4000):
    for port in range(start, end):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', port))
            sock.close()
            return port
        except:
            continue
    raise RuntimeError("No free ports available")

free_port = find_free_port()
tunnel = client.expose_path(free_port, "app")
```

#### 문제: "Tunnel creation failed" 오류
```python
TunnelCreationError: Failed to create tunnel: proxy name already exists
```

**원인**
- 동일한 이름의 터널이 이미 존재
- 서버 측 설정 문제
- 권한 부족

**해결 방법**
```python
# 1. 기존 터널 확인 및 정리
existing_tunnels = client.list_tunnels()
for tunnel in existing_tunnels:
    if tunnel.config.path == "app":
        tunnel.close()

# 2. 고유한 터널 이름 생성
import uuid
unique_path = f"app-{uuid.uuid4().hex[:8]}"
tunnel = client.expose_path(3000, unique_path)

# 3. 터널 정리 후 재생성
client.close_all_tunnels()
tunnel = client.expose_path(3000, "app")
```

### 프로세스 관리 문제

#### 문제: "Binary not found" 오류
```python
BinaryNotFoundError: frpc binary not found in PATH
```

**원인**
- FRP 바이너리가 설치되지 않음
- PATH에 바이너리 경로가 없음

**해결 방법**
```python
# 1. 자동 설치
from frp_wrapper import ensure_frp_installed
ensure_frp_installed()

# 2. 수동 경로 지정
client = FRPClient(
    "tunnel.example.com",
    binary_path="/usr/local/bin/frpc"
)

# 3. 바이너리 위치 확인
import shutil
frpc_path = shutil.which("frpc")
if frpc_path:
    print(f"frpc 위치: {frpc_path}")
else:
    print("frpc를 찾을 수 없습니다")
```

#### 문제: 프로세스가 예기치 않게 종료됨
```
Process terminated unexpectedly
```

**원인**
- 메모리 부족
- 설정 파일 오류
- 시스템 리소스 제한

**해결 방법**
```python
# 1. 프로세스 출력 확인
output = client._process_manager.get_output()
errors = client._process_manager.get_errors()
print(f"출력: {output}")
print(f"에러: {errors}")

# 2. 자동 재시작 설정
class AutoRestartClient(FRPClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._monitor_thread = threading.Thread(target=self._monitor_process)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
        
    def _monitor_process(self):
        while True:
            if not self._process_manager.is_running():
                print("프로세스가 종료됨. 재시작 중...")
                self.reconnect()
            time.sleep(5)

# 3. 리소스 제한 확인
import resource
soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
print(f"파일 디스크립터 제한: {soft}/{hard}")
```

### 네트워크 문제

#### 문제: 간헐적인 연결 끊김
```
Tunnel disconnected intermittently
```

**원인**
- 불안정한 네트워크
- 서버 과부하
- 타임아웃 설정

**해결 방법**
```python
# 1. 하트비트 설정
client = FRPClient(
    "tunnel.example.com",
    options={
        "heartbeat_interval": 30,
        "heartbeat_timeout": 90
    }
)

# 2. 자동 재연결
@client.on(EventType.TUNNEL_DISCONNECTED)
def on_disconnect(data):
    tunnel_id = data['tunnel_id']
    print(f"터널 {tunnel_id} 연결 끊김. 재연결 시도...")
    # 재연결 로직

# 3. 연결 품질 모니터링
import ping3

def check_connection_quality(host):
    latencies = []
    for _ in range(10):
        latency = ping3.ping(host)
        if latency:
            latencies.append(latency * 1000)  # ms
    
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        packet_loss = (10 - len(latencies)) / 10 * 100
        print(f"평균 지연: {avg_latency:.2f}ms")
        print(f"패킷 손실: {packet_loss:.1f}%")
```

#### 문제: 느린 응답 속도
```
Tunnel response is very slow
```

**원인**
- 네트워크 대역폭 부족
- 압축 미사용
- 서버 위치

**해결 방법**
```python
# 1. 압축 활성화
tunnel = client.expose_path(
    3000,
    "app",
    use_compression=True,
    compression_level=6
)

# 2. 대역폭 측정
def measure_bandwidth(tunnel_url):
    import requests
    import time
    
    # 1MB 테스트 데이터
    test_data = b'x' * (1024 * 1024)
    
    start = time.time()
    response = requests.post(f"{tunnel_url}/test", data=test_data)
    duration = time.time() - start
    
    bandwidth_mbps = (len(test_data) * 8) / (duration * 1000000)
    print(f"업로드 대역폭: {bandwidth_mbps:.2f} Mbps")

# 3. CDN 사용 고려
tunnel = client.expose_path(
    3000,
    "app",
    custom_headers={
        'Cache-Control': 'public, max-age=86400',
        'CDN-Cache-Control': 'max-age=86400'
    }
)
```

### 보안 문제

#### 문제: "Access denied" 오류
```
Access denied from IP 192.168.1.100
```

**원인**
- IP 화이트리스트 설정
- 인증 실패
- 권한 부족

**해결 방법**
```python
# 1. IP 화이트리스트 확인
tunnel = client.expose_path(
    3000,
    "app",
    allowed_ips=["0.0.0.0/0"]  # 모든 IP 허용 (주의!)
)

# 2. 기본 인증 설정
tunnel = client.expose_path(
    3000,
    "app",
    basic_auth="user:password"
)

# 3. 디버그 모드로 확인
client = FRPClient(
    "tunnel.example.com",
    log_level="debug"
)
```

### 설정 문제

#### 문제: 설정 파일 로드 실패
```
ConfigurationError: Failed to load config file
```

**원인**
- 잘못된 YAML/JSON 형식
- 파일 권한 문제
- 경로 오류

**해결 방법**
```python
# 1. 설정 파일 검증
import yaml

try:
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    print("설정 파일 유효")
except yaml.YAMLError as e:
    print(f"YAML 오류: {e}")

# 2. 파일 권한 확인
import os
import stat

file_stat = os.stat("config.yaml")
permissions = stat.filemode(file_stat.st_mode)
print(f"파일 권한: {permissions}")

# 3. 절대 경로 사용
import os
config_path = os.path.abspath("config.yaml")
client = FRPClient.from_config(config_path)
```

## 디버깅 도구

### 로그 레벨 설정
```python
# 상세 로그 출력
import logging

logging.basicConfig(level=logging.DEBUG)

client = FRPClient(
    "tunnel.example.com",
    log_level="debug"
)
```

### 프로세스 모니터링
```python
def monitor_frp_process():
    """FRP 프로세스 상태 모니터링"""
    
    while True:
        if client._process_manager.is_running():
            process = client._process_manager.process
            
            # CPU/메모리 사용량
            import psutil
            p = psutil.Process(process.pid)
            print(f"CPU: {p.cpu_percent()}%")
            print(f"메모리: {p.memory_info().rss / 1024 / 1024:.2f} MB")
            
            # 열린 파일/연결 수
            print(f"열린 파일: {len(p.open_files())}")
            print(f"연결 수: {len(p.connections())}")
        
        time.sleep(5)
```

### 네트워크 진단
```python
def diagnose_network():
    """네트워크 연결 진단"""
    
    # DNS 확인
    try:
        import socket
        ip = socket.gethostbyname("tunnel.example.com")
        print(f"DNS 확인 성공: {ip}")
    except:
        print("DNS 확인 실패")
    
    # 포트 스캔
    ports = [7000, 8080, 443]
    for port in ports:
        if test_connection("tunnel.example.com", port):
            print(f"포트 {port}: 열림")
        else:
            print(f"포트 {port}: 닫힘")
    
    # 트레이스라우트
    import subprocess
    result = subprocess.run(
        ["traceroute", "-n", "tunnel.example.com"],
        capture_output=True,
        text=True
    )
    print("경로 추적:")
    print(result.stdout)
```

## 성능 튜닝

### 메모리 사용 최적화
```python
# 1. 터널 수 제한
MAX_TUNNELS = 10
if len(client.list_tunnels()) >= MAX_TUNNELS:
    # 가장 오래된 터널 종료
    oldest = min(client.list_tunnels(), key=lambda t: t.created_at)
    oldest.close()

# 2. 가비지 컬렉션 강제 실행
import gc
gc.collect()

# 3. 메모리 프로파일링
from memory_profiler import profile

@profile
def create_tunnel():
    return client.expose_path(3000, "app")
```

### CPU 사용 최적화
```python
# 1. 프로세스 우선순위 조정
import os
os.nice(10)  # 낮은 우선순위

# 2. 스레드 풀 크기 조정
client = FRPClient(
    "tunnel.example.com",
    options={
        "worker_threads": 4
    }
)
```

## 로그 분석

### 로그 파서
```python
import re
from datetime import datetime

class FRPLogParser:
    def __init__(self, log_file):
        self.log_file = log_file
        
    def parse_errors(self):
        """에러 로그 추출"""
        errors = []
        with open(self.log_file, 'r') as f:
            for line in f:
                if '[E]' in line or 'ERROR' in line:
                    errors.append(line.strip())
        return errors
    
    def parse_tunnel_events(self):
        """터널 이벤트 추출"""
        events = []
        pattern = r'\[(.*?)\].*\[proxy\].*\[(.*?)\].*'
        
        with open(self.log_file, 'r') as f:
            for line in f:
                match = re.search(pattern, line)
                if match:
                    timestamp = match.group(1)
                    tunnel_name = match.group(2)
                    events.append({
                        'timestamp': timestamp,
                        'tunnel': tunnel_name,
                        'message': line.strip()
                    })
        return events
```

## 복구 절차

### 전체 시스템 재시작
```python
def full_system_restart():
    """전체 시스템 재시작"""
    
    print("1. 모든 터널 종료...")
    client.close_all_tunnels()
    
    print("2. 클라이언트 연결 해제...")
    client.disconnect()
    
    print("3. 프로세스 정리...")
    time.sleep(2)
    
    print("4. 클라이언트 재연결...")
    client.connect()
    
    print("5. 터널 재생성...")
    # 필요한 터널 재생성
    
    print("시스템 재시작 완료!")
```

### 백업 및 복구
```python
import json

def backup_tunnel_config():
    """터널 설정 백업"""
    tunnels = []
    for tunnel in client.list_tunnels():
        tunnels.append({
            'type': tunnel.config.tunnel_type,
            'local_port': tunnel.config.local_port,
            'path': getattr(tunnel.config, 'path', None),
            'options': tunnel.config.__dict__
        })
    
    with open('tunnel_backup.json', 'w') as f:
        json.dump(tunnels, f, indent=2)
    
    print(f"{len(tunnels)}개 터널 설정 백업 완료")

def restore_tunnels():
    """터널 설정 복구"""
    with open('tunnel_backup.json', 'r') as f:
        tunnels = json.load(f)
    
    for config in tunnels:
        if config['type'] == 'http' and config['path']:
            client.expose_path(
                config['local_port'],
                config['path']
            )
        elif config['type'] == 'tcp':
            client.expose_tcp(
                config['local_port']
            )
    
    print(f"{len(tunnels)}개 터널 복구 완료")
```

## 도움 받기

### 디버그 정보 수집
```python
def collect_debug_info():
    """디버그 정보 수집"""
    
    info = {
        'version': frp_wrapper.__version__,
        'python_version': sys.version,
        'platform': platform.platform(),
        'client_config': {
            'server': client.server,
            'port': client.port,
            'connected': client.is_connected()
        },
        'tunnels': len(client.list_tunnels()),
        'errors': client._process_manager.get_errors()[-100:]  # 최근 100줄
    }
    
    with open('debug_info.json', 'w') as f:
        json.dump(info, f, indent=2)
    
    print("디버그 정보가 debug_info.json에 저장되었습니다")
```

### 지원 요청 시 필요한 정보
1. 오류 메시지 전문
2. 사용 중인 버전
3. 운영체제 및 Python 버전
4. 설정 파일 (민감한 정보 제거)
5. 디버그 로그
6. 재현 가능한 최소 코드

### 추가 리소스
- 📝 [GitHub Issues](https://github.com/yourusername/frp-wrapper/issues)
- 💬 [Discord 커뮤니티](https://discord.gg/frp-wrapper)
- 📧 기술 지원: support@example.com