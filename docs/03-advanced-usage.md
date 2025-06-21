# 고급 사용법

## 프로덕션 환경 설정

### 프로덕션 클라이언트 설정
```python
from frp_wrapper import FRPClient
import logging

# 프로덕션 설정
client = FRPClient(
    server="tunnel.production.com",
    port=7000,
    auth_token=os.environ["FRP_PROD_TOKEN"],
    tls_enable=True,
    tls_verify=True,
    auto_reconnect=True,
    reconnect_interval=60,
    log_level="warning",
    options={
        "pool_count": 20,
        "heartbeat_interval": 30,
        "heartbeat_timeout": 90
    }
)
```

### 고가용성 설정
```python
class HighAvailabilityClient:
    def __init__(self, servers: List[str], **options):
        self.servers = servers
        self.options = options
        self.current_server_index = 0
        self.client = None
        
    def connect(self):
        """여러 서버에 순차적으로 연결 시도"""
        for i in range(len(self.servers)):
            server = self.servers[self.current_server_index]
            try:
                self.client = FRPClient(server, **self.options)
                self.client.connect()
                logging.info(f"Connected to {server}")
                return
            except ConnectionError:
                logging.warning(f"Failed to connect to {server}")
                self.current_server_index = (self.current_server_index + 1) % len(self.servers)
        
        raise ConnectionError("All servers are unavailable")

# 사용
ha_client = HighAvailabilityClient(
    servers=["tunnel1.example.com", "tunnel2.example.com", "tunnel3.example.com"],
    auth_token=os.environ["FRP_TOKEN"]
)
ha_client.connect()
```

## 비동기 프로그래밍

### asyncio 통합
```python
import asyncio
from frp_wrapper import FRPClient

class AsyncFRPClient:
    def __init__(self, *args, **kwargs):
        self.sync_client = FRPClient(*args, **kwargs)
        
    async def connect(self):
        """비동기 연결"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.sync_client.connect)
        
    async def expose_path(self, *args, **kwargs):
        """비동기 터널 생성"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.sync_client.expose_path, 
            *args, 
            **kwargs
        )

# 사용 예제
async def main():
    client = AsyncFRPClient("tunnel.example.com")
    await client.connect()
    
    # 여러 터널 동시 생성
    tunnels = await asyncio.gather(
        client.expose_path(3000, "app1"),
        client.expose_path(3001, "app2"),
        client.expose_path(3002, "app3")
    )
    
    for tunnel in tunnels:
        print(f"Created: {tunnel.url}")

asyncio.run(main())
```

### 비동기 이벤트 처리
```python
import asyncio
from frp_wrapper import FRPClient, EventType

class AsyncEventHandler:
    def __init__(self, client: FRPClient):
        self.client = client
        self.event_queue = asyncio.Queue()
        
        # 이벤트를 큐에 추가
        @client.on(EventType.TUNNEL_CONNECTED)
        def on_connected(data):
            asyncio.create_task(self.event_queue.put(("connected", data)))
            
        @client.on(EventType.TUNNEL_ERROR)
        def on_error(data):
            asyncio.create_task(self.event_queue.put(("error", data)))
    
    async def process_events(self):
        """이벤트 비동기 처리"""
        while True:
            event_type, data = await self.event_queue.get()
            
            if event_type == "connected":
                await self.handle_connected(data)
            elif event_type == "error":
                await self.handle_error(data)
                
    async def handle_connected(self, data):
        # 비동기 작업 수행
        await asyncio.sleep(1)
        print(f"Async handled connection: {data}")
        
    async def handle_error(self, data):
        # 비동기 에러 처리
        await self.notify_admin(data)
```

## 동적 터널 관리

### 터널 풀 관리
```python
from frp_wrapper import FRPClient, Tunnel
from typing import Dict, List
import threading

class TunnelPool:
    """터널 풀 관리자"""
    
    def __init__(self, client: FRPClient, max_tunnels: int = 10):
        self.client = client
        self.max_tunnels = max_tunnels
        self.active_tunnels: Dict[str, Tunnel] = {}
        self.available_ports = list(range(30000, 30000 + max_tunnels))
        self.lock = threading.Lock()
        
    def acquire_tunnel(self, local_port: int, path: str) -> Tunnel:
        """터널 획득"""
        with self.lock:
            # 이미 존재하는 터널 확인
            key = f"{local_port}:{path}"
            if key in self.active_tunnels:
                return self.active_tunnels[key]
            
            # 새 터널 생성
            if len(self.active_tunnels) >= self.max_tunnels:
                # 가장 오래된 터널 제거
                oldest_key = min(self.active_tunnels.keys())
                self.release_tunnel(oldest_key)
            
            tunnel = self.client.expose_path(local_port, path)
            self.active_tunnels[key] = tunnel
            return tunnel
            
    def release_tunnel(self, key: str):
        """터널 해제"""
        with self.lock:
            if key in self.active_tunnels:
                tunnel = self.active_tunnels.pop(key)
                tunnel.close()

# 사용
pool = TunnelPool(client, max_tunnels=5)

# 터널 동적 할당
tunnel1 = pool.acquire_tunnel(3000, "app1")
tunnel2 = pool.acquire_tunnel(3001, "app2")
```

### 자동 스케일링
```python
class AutoScalingTunnelManager:
    """부하에 따라 터널을 자동으로 스케일링"""
    
    def __init__(self, client: FRPClient, base_port: int = 3000):
        self.client = client
        self.base_port = base_port
        self.tunnels: List[Tunnel] = []
        self.current_load = 0
        self.scale_threshold = 0.8  # 80% 부하
        
    def update_load(self, load: float):
        """현재 부하 업데이트"""
        self.current_load = load
        
        if load > self.scale_threshold:
            self.scale_up()
        elif load < self.scale_threshold * 0.5:
            self.scale_down()
            
    def scale_up(self):
        """터널 추가"""
        if len(self.tunnels) < 10:  # 최대 10개
            port = self.base_port + len(self.tunnels)
            tunnel = self.client.expose_path(port, f"app-{len(self.tunnels)}")
            self.tunnels.append(tunnel)
            print(f"Scaled up: {tunnel.url}")
            
    def scale_down(self):
        """터널 제거"""
        if len(self.tunnels) > 1:  # 최소 1개 유지
            tunnel = self.tunnels.pop()
            tunnel.close()
            print(f"Scaled down: removed tunnel")
```

## 멀티테넌트 지원

### 테넌트별 터널 관리
```python
from frp_wrapper import FRPClient
from typing import Dict, Optional
import uuid

class MultiTenantTunnelManager:
    """멀티테넌트 환경에서 터널 관리"""
    
    def __init__(self, client: FRPClient):
        self.client = client
        self.tenant_tunnels: Dict[str, Dict[str, Tunnel]] = {}
        
    def create_tenant_tunnel(
        self, 
        tenant_id: str, 
        service_name: str,
        local_port: int
    ) -> Tunnel:
        """테넌트별 터널 생성"""
        # 테넌트별 고유 경로 생성
        path = f"{tenant_id}/{service_name}"
        
        # 터널 생성
        tunnel = self.client.expose_path(
            local_port=local_port,
            path=path,
            custom_headers={
                "X-Tenant-ID": tenant_id,
                "X-Service": service_name
            }
        )
        
        # 저장
        if tenant_id not in self.tenant_tunnels:
            self.tenant_tunnels[tenant_id] = {}
        self.tenant_tunnels[tenant_id][service_name] = tunnel
        
        return tunnel
        
    def get_tenant_tunnels(self, tenant_id: str) -> Dict[str, Tunnel]:
        """특정 테넌트의 모든 터널 조회"""
        return self.tenant_tunnels.get(tenant_id, {})
        
    def remove_tenant(self, tenant_id: str):
        """테넌트의 모든 터널 제거"""
        if tenant_id in self.tenant_tunnels:
            for tunnel in self.tenant_tunnels[tenant_id].values():
                tunnel.close()
            del self.tenant_tunnels[tenant_id]

# 사용 예제
manager = MultiTenantTunnelManager(client)

# 테넌트 A
manager.create_tenant_tunnel("tenant-a", "api", 8000)
manager.create_tenant_tunnel("tenant-a", "web", 3000)

# 테넌트 B
manager.create_tenant_tunnel("tenant-b", "api", 8001)
manager.create_tenant_tunnel("tenant-b", "web", 3001)
```

## 로드 밸런싱

### 라운드 로빈 로드 밸런서
```python
class LoadBalancedTunnels:
    """여러 백엔드 서비스에 대한 로드 밸런싱"""
    
    def __init__(self, client: FRPClient, path: str):
        self.client = client
        self.path = path
        self.backends: List[int] = []
        self.tunnels: List[Tunnel] = []
        self.current_index = 0
        self.proxy_port = 9999
        
    def add_backend(self, port: int):
        """백엔드 추가"""
        self.backends.append(port)
        
    def start(self):
        """로드 밸런서 시작"""
        # 프록시 서버 시작
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import requests
        
        class LoadBalancerHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                # 라운드 로빈으로 백엔드 선택
                backend_port = self.server.parent.get_next_backend()
                
                # 요청 전달
                resp = requests.get(f"http://localhost:{backend_port}{self.path}")
                
                # 응답 전달
                self.send_response(resp.status_code)
                for key, value in resp.headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(resp.content)
                
        # 프록시 서버 실행
        server = HTTPServer(('localhost', self.proxy_port), LoadBalancerHandler)
        server.parent = self
        
        # 터널 생성
        tunnel = self.client.expose_path(self.proxy_port, self.path)
        print(f"Load balancer: {tunnel.url}")
        
        # 서버 실행
        server.serve_forever()
        
    def get_next_backend(self) -> int:
        """다음 백엔드 선택"""
        port = self.backends[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.backends)
        return port
```

## 플러그인 시스템

### 터널 미들웨어
```python
from abc import ABC, abstractmethod
from typing import Any, Dict

class TunnelMiddleware(ABC):
    """터널 미들웨어 인터페이스"""
    
    @abstractmethod
    def before_create(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """터널 생성 전 처리"""
        pass
        
    @abstractmethod
    def after_create(self, tunnel: Tunnel) -> None:
        """터널 생성 후 처리"""
        pass
        
    @abstractmethod
    def before_close(self, tunnel: Tunnel) -> None:
        """터널 종료 전 처리"""
        pass

class LoggingMiddleware(TunnelMiddleware):
    """로깅 미들웨어"""
    
    def before_create(self, config: Dict[str, Any]) -> Dict[str, Any]:
        print(f"Creating tunnel with config: {config}")
        return config
        
    def after_create(self, tunnel: Tunnel) -> None:
        print(f"Tunnel created: {tunnel.id}")
        
    def before_close(self, tunnel: Tunnel) -> None:
        print(f"Closing tunnel: {tunnel.id}")

class SecurityMiddleware(TunnelMiddleware):
    """보안 미들웨어"""
    
    def before_create(self, config: Dict[str, Any]) -> Dict[str, Any]:
        # 보안 헤더 추가
        if 'custom_headers' not in config:
            config['custom_headers'] = {}
            
        config['custom_headers'].update({
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block'
        })
        
        return config
        
    def after_create(self, tunnel: Tunnel) -> None:
        # 보안 검사
        self._security_scan(tunnel)
        
    def before_close(self, tunnel: Tunnel) -> None:
        # 감사 로그
        self._audit_log(tunnel)

# 미들웨어 적용
client.add_middleware(LoggingMiddleware())
client.add_middleware(SecurityMiddleware())
```

## 커스텀 프로토콜

### 사용자 정의 프로토콜 터널
```python
class CustomProtocolTunnel:
    """사용자 정의 프로토콜 지원"""
    
    def __init__(self, client: FRPClient):
        self.client = client
        
    def expose_grpc(self, local_port: int, service_name: str) -> Tunnel:
        """gRPC 서비스 노출"""
        return self.client.expose_tcp(
            local_port=local_port,
            remote_port=None,
            metadata={
                "protocol": "grpc",
                "service": service_name
            }
        )
        
    def expose_mqtt(self, local_port: int = 1883) -> Tunnel:
        """MQTT 브로커 노출"""
        # MQTT는 TCP와 WebSocket 모두 필요
        tcp_tunnel = self.client.expose_tcp(local_port, 1883)
        ws_tunnel = self.client.expose_path(
            local_port=local_port,
            path="mqtt-ws",
            websocket=True
        )
        
        return {
            "tcp": tcp_tunnel,
            "websocket": ws_tunnel
        }
```

## 모니터링 통합

### Prometheus 메트릭
```python
from prometheus_client import Counter, Gauge, Histogram
import time

# 메트릭 정의
tunnel_created_total = Counter('frp_tunnel_created_total', 'Total tunnels created')
tunnel_active_gauge = Gauge('frp_tunnel_active', 'Currently active tunnels')
tunnel_duration_seconds = Histogram('frp_tunnel_duration_seconds', 'Tunnel duration')

class MonitoredFRPClient(FRPClient):
    """Prometheus 모니터링이 통합된 클라이언트"""
    
    def expose_path(self, *args, **kwargs):
        start_time = time.time()
        
        # 터널 생성
        tunnel = super().expose_path(*args, **kwargs)
        
        # 메트릭 업데이트
        tunnel_created_total.inc()
        tunnel_active_gauge.inc()
        
        # 종료 시 메트릭 업데이트를 위한 래핑
        original_close = tunnel.close
        def monitored_close():
            duration = time.time() - start_time
            tunnel_duration_seconds.observe(duration)
            tunnel_active_gauge.dec()
            original_close()
            
        tunnel.close = monitored_close
        
        return tunnel
```

### 사용자 정의 대시보드
```python
from flask import Flask, render_template_string
import json

def create_monitoring_dashboard(client: FRPClient):
    """커스텀 모니터링 대시보드 생성"""
    app = Flask(__name__)
    
    DASHBOARD_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FRP Tunnels Dashboard</title>
        <meta http-equiv="refresh" content="5">
    </head>
    <body>
        <h1>Active Tunnels</h1>
        <table border="1">
            <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Local Port</th>
                <th>URL/Endpoint</th>
                <th>Status</th>
                <th>Metrics</th>
            </tr>
            {% for tunnel in tunnels %}
            <tr>
                <td>{{ tunnel.id }}</td>
                <td>{{ tunnel.type }}</td>
                <td>{{ tunnel.local_port }}</td>
                <td>{{ tunnel.url }}</td>
                <td>{{ tunnel.status }}</td>
                <td>{{ tunnel.metrics }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    
    @app.route('/')
    def dashboard():
        tunnels_data = []
        for tunnel in client.list_tunnels():
            metrics = client.get_tunnel_metrics(tunnel.id)
            tunnels_data.append({
                'id': tunnel.id,
                'type': tunnel.config.tunnel_type,
                'local_port': tunnel.config.local_port,
                'url': getattr(tunnel, 'url', tunnel.endpoint),
                'status': tunnel.status.value,
                'metrics': f"{metrics.bytes_sent} bytes sent" if metrics else "N/A"
            })
            
        return render_template_string(DASHBOARD_TEMPLATE, tunnels=tunnels_data)
    
    return app
```

## 보안 강화

### 엔드투엔드 암호화
```python
from cryptography.fernet import Fernet
import base64

class EncryptedTunnel:
    """엔드투엔드 암호화를 지원하는 터널"""
    
    def __init__(self, client: FRPClient, key: bytes = None):
        self.client = client
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)
        
    def create_encrypted_tunnel(self, local_port: int, path: str):
        """암호화된 터널 생성"""
        # 로컬 프록시 서버 생성 (암호화/복호화 담당)
        proxy_port = self._create_crypto_proxy(local_port)
        
        # 터널 생성
        tunnel = self.client.expose_path(proxy_port, path)
        
        # 클라이언트에게 키 전달 방법 제공
        tunnel.encryption_key = base64.b64encode(self.key).decode()
        
        return tunnel
```

### Zero Trust 네트워크
```python
class ZeroTrustTunnel:
    """Zero Trust 보안 모델 구현"""
    
    def __init__(self, client: FRPClient, auth_service_url: str):
        self.client = client
        self.auth_service_url = auth_service_url
        
    def create_secure_tunnel(
        self, 
        local_port: int, 
        path: str,
        required_permissions: List[str]
    ):
        """인증이 필요한 터널 생성"""
        
        # 인증 프록시 생성
        auth_proxy_port = self._create_auth_proxy(
            local_port,
            required_permissions
        )
        
        # 터널 생성
        tunnel = self.client.expose_path(
            auth_proxy_port,
            path,
            custom_headers={
                "X-Auth-Required": "true",
                "X-Required-Permissions": ",".join(required_permissions)
            }
        )
        
        return tunnel
```

## 성능 최적화

### 연결 풀링
```python
class PooledTunnelClient(FRPClient):
    """연결 풀링을 사용하는 클라이언트"""
    
    def __init__(self, *args, **kwargs):
        # 연결 풀 크기 설정
        kwargs.setdefault('pool_count', 50)
        kwargs.setdefault('tcp_keepalive', True)
        kwargs.setdefault('tcp_keepalive_interval', 30)
        
        super().__init__(*args, **kwargs)
        
    def create_pooled_tunnel(self, local_port: int, path: str, pool_size: int = 10):
        """풀링된 연결을 사용하는 터널"""
        return self.expose_path(
            local_port,
            path,
            options={
                'connection_pool_size': pool_size,
                'reuse_connections': True
            }
        )
```

### 압축 및 캐싱
```python
def create_optimized_tunnel(client: FRPClient, local_port: int, path: str):
    """성능 최적화된 터널 생성"""
    return client.expose_path(
        local_port,
        path,
        use_compression=True,
        compression_level=6,
        custom_headers={
            'Cache-Control': 'public, max-age=3600',
            'Vary': 'Accept-Encoding'
        }
    )
```

## 다음 단계

- 🛠️ [문제 해결](04-troubleshooting.md) - 일반적인 문제 해결
- 🔐 [보안 가이드](../spec/04-security.md) - 보안 강화 방법
- 📊 [모니터링](../plan/checkpoints/checkpoint-07-monitoring.md) - 상세 모니터링 설정