# Checkpoint Improvements for AI Implementation

## Checkpoint 1: Process Manager ✅ (Completed)

### Success Criteria (Verified)
- [x] 100% test coverage for ProcessManager (Achieved: 96% for module, 97% overall)
- [x] Context manager support implemented
- [x] Logging integration with structlog
- [x] Binary executable validation
- [x] Shared test fixtures in conftest.py
- [x] All tests pass consistently
- [x] Type hints and documentation complete
- [x] mypy strict mode passes
- [x] ruff linting passes

### Key Implementation Details
- Use `subprocess.Popen[str]` for proper typing
- `__exit__` must return `Literal[False]` for proper exception propagation
- Add `from e` for exception chaining
- Use modern Python 3.11+ union syntax (`X | None` instead of `Optional[X]`)

---

## Checkpoint 2: Basic Client API

### Enhanced Implementation Requirements

#### ConfigBuilder Class (New - Required)
```python
# src/frp_wrapper/core/config.py
class ConfigBuilder:
    """Builds FRP configuration files with validation"""

    def __init__(self):
        self._config_path: Path | None = None
        self._temp_file: tempfile.NamedTemporaryFile | None = None

    def add_server(self, addr: str, port: int = 7000, token: str | None = None) -> 'ConfigBuilder':
        """Add server configuration with validation"""
        # Validate server address format
        # Generate TOML configuration
        # Return self for chaining

    def add_proxy(self, proxy_config: dict) -> 'ConfigBuilder':
        """Add proxy configuration"""
        # Validate proxy settings
        # Append to configuration

    def build(self) -> str:
        """Build configuration file and return path"""
        # Write to temporary file
        # Return absolute path

    def cleanup(self):
        """Clean up temporary files"""
        # Delete temporary configuration file
```

#### Binary Discovery Strategy
1. Check system PATH using `shutil.which('frpc')`
2. Check common installation paths:
   - `/usr/local/bin/frpc`
   - `/opt/frp/frpc`
   - `~/bin/frpc`
   - Windows: `C:\\Program Files\\frp\\frpc.exe`
3. Check environment variable `FRP_BINARY_PATH`
4. Allow user override via parameter

#### Connection Retry Logic
```python
def connect(self, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
    """Connect with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            if self._attempt_connection():
                return True
        except ConnectionError as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Connection attempt {attempt + 1} failed, retrying...")
            time.sleep(retry_delay * (2 ** attempt))
    return False
```

#### Test Enhancements
- Add timeout to all subprocess operations
- Mock time.sleep for retry tests
- Test binary discovery order
- Test cleanup on connection failure

---

## Checkpoint 3: Tunnel Management with Pydantic

### Enhanced Implementation Requirements

#### TunnelManager Architecture
```python
class TunnelManager:
    """Manages tunnel lifecycle with registry pattern"""

    def __init__(self, client: FRPClient, config: TunnelConfig):
        self.client = client
        self.config = config
        self.registry = TunnelRegistry(max_tunnels=config.max_tunnels)
        self._id_generator = TunnelIDGenerator(config.id_strategy)

    def create_tunnel(self, tunnel_type: TunnelType, **kwargs) -> BaseTunnel:
        """Factory method for tunnel creation"""
        tunnel_id = self._id_generator.generate(**kwargs)
        # Validate against existing tunnels
        # Check resource limits
        # Create appropriate tunnel type
```

#### Tunnel ID Generation Strategies
```python
class IDStrategy(str, Enum):
    UUID = "uuid"         # UUID4 for guaranteed uniqueness
    SEQUENTIAL = "seq"    # Sequential integers
    DESCRIPTIVE = "desc"  # Based on type and port: "http-3000-myapp"
    CUSTOM = "custom"     # User-provided with validation

class TunnelIDGenerator:
    """Generates tunnel IDs based on strategy"""

    def generate(self, strategy: IDStrategy = IDStrategy.DESCRIPTIVE, **context) -> str:
        """Generate unique tunnel ID based on strategy"""
```

#### Concurrent Tunnel Limits
- Implement semaphore-based limiting
- Queue pending tunnels when at limit
- Provide wait/timeout options
- Clear error messages when limit exceeded

#### State Transition Validation
```python
VALID_TRANSITIONS = {
    TunnelStatus.PENDING: [TunnelStatus.CONNECTING, TunnelStatus.ERROR],
    TunnelStatus.CONNECTING: [TunnelStatus.CONNECTED, TunnelStatus.ERROR],
    TunnelStatus.CONNECTED: [TunnelStatus.DISCONNECTED, TunnelStatus.ERROR],
    TunnelStatus.DISCONNECTED: [TunnelStatus.CONNECTING, TunnelStatus.CLOSED],
    TunnelStatus.ERROR: [TunnelStatus.CONNECTING, TunnelStatus.CLOSED],
    TunnelStatus.CLOSED: []  # Terminal state
}

def validate_transition(current: TunnelStatus, new: TunnelStatus) -> bool:
    """Validate state transition is allowed"""
    return new in VALID_TRANSITIONS.get(current, [])
```

---

## Checkpoint 4: Path-Based Routing

### Enhanced Implementation Requirements

#### FRP Configuration Validation
```python
def validate_frp_config(config: dict) -> bool:
    """Validate generated FRP configuration"""
    required_fields = ["type", "localPort", "customDomains", "locations"]
    # Check all required fields present
    # Validate locations format (must start with /)
    # Validate port ranges
    # Check for conflicts with existing proxies
```

#### Path Conflict Detection
```python
class PathConflictDetector:
    """Detects path conflicts between tunnels"""

    def check_conflict(self, new_path: str, existing_paths: list[str]) -> str | None:
        """Check if new path conflicts with existing paths"""
        # Exact match conflict
        # Prefix conflict (e.g., /api vs /api/v1)
        # Wildcard conflict (e.g., /api/* vs /api/users)
        # Return conflicting path or None
```

#### Wildcard Path Support
```python
class PathPattern:
    """Represents a path pattern with wildcard support"""

    def __init__(self, pattern: str):
        # Convert wildcards to regex
        # /api/* -> /api/.*
        # /api/*/users -> /api/.*/users
        self.pattern = pattern
        self.regex = self._compile_pattern()

    def matches(self, path: str) -> bool:
        """Check if path matches pattern"""
```

#### Real FRP Config Generation Test
```python
@pytest.mark.integration
def test_generate_real_frp_config(tmp_path):
    """Test generating actual FRP configuration file"""
    config = HTTPTunnelConfig(
        path="myapp",
        custom_domains=["example.com"],
        websocket=True
    )

    # Generate config file
    config_path = tmp_path / "frpc.toml"
    config_content = generate_frp_config([config])
    config_path.write_text(config_content)

    # Validate with toml parser
    import toml
    parsed = toml.load(config_path)

    # Verify structure matches FRP expectations
    assert "common" in parsed
    assert "proxies" in parsed
    assert parsed["proxies"][0]["locations"] == ["/myapp"]
```

---

## Checkpoint 5: Context Manager

### Enhanced Implementation Requirements

#### Nested Context Exception Handling
```python
class NestedContextManager:
    """Handles nested context managers with proper cleanup"""

    def __init__(self):
        self._stack: list[Any] = []
        self._cleanup_errors: list[Exception] = []

    def push(self, context: Any) -> None:
        """Add context to stack"""
        self._stack.append(context)

    def cleanup_all(self) -> None:
        """Clean up in LIFO order with error collection"""
        while self._stack:
            context = self._stack.pop()
            try:
                if hasattr(context, '__exit__'):
                    context.__exit__(None, None, None)
            except Exception as e:
                self._cleanup_errors.append(e)
```

#### Resource Leak Prevention
```python
import weakref
import atexit

class ResourceLeakDetector:
    """Detects and prevents resource leaks"""

    _active_resources: weakref.WeakSet = weakref.WeakSet()

    @classmethod
    def register(cls, resource: Any) -> None:
        """Register resource for tracking"""
        cls._active_resources.add(resource)

    @classmethod
    def cleanup_leaked(cls) -> None:
        """Clean up any leaked resources at exit"""
        for resource in cls._active_resources:
            logger.warning(f"Leaked resource detected: {resource}")
            try:
                resource.close()
            except Exception as e:
                logger.error(f"Failed to clean up leaked resource: {e}")

# Register cleanup at exit
atexit.register(ResourceLeakDetector.cleanup_leaked)
```

#### Async Context Manager Support
```python
class AsyncProcessManager:
    """Async version of ProcessManager"""

    async def __aenter__(self) -> 'AsyncProcessManager':
        """Async context entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Async context exit"""
        await self.stop()
        return False
```

#### Timeout Handling
```python
class TimeoutContext:
    """Context manager with timeout support"""

    def __init__(self, timeout: float):
        self.timeout = timeout
        self._timer: threading.Timer | None = None

    def __enter__(self):
        def timeout_handler():
            raise TimeoutError(f"Operation timed out after {self.timeout}s")

        self._timer = threading.Timer(self.timeout, timeout_handler)
        self._timer.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._timer:
            self._timer.cancel()
        return False
```

---

## Checkpoint 6: Server Tools

### Enhanced Implementation Requirements

#### Server Configuration Templates
```python
# src/frp_wrapper/server/templates.py
TEMPLATES = {
    "basic": """
        [common]
        bind_addr = "{bind_addr}"
        bind_port = {bind_port}
        token = "{token}"
        log_level = "info"
    """,

    "production": """
        [common]
        bind_addr = "0.0.0.0"
        bind_port = 7000
        kcp_bind_port = 7000

        vhost_http_port = 80
        vhost_https_port = 443

        token = "{token}"

        # Performance
        max_pool_count = 10
        heartbeat_timeout = 90

        # Security
        tls_enable = true
        tls_cert_file = "{cert_path}"
        tls_key_file = "{key_path}"

        # Logging
        log_level = "info"
        log_max_days = 30
        log_file = "./frps.log"
    """
}
```

#### Docker/Docker-Compose Examples
```yaml
# docker-compose.yml
version: '3.8'
services:
  frps:
    image: snowdreamtech/frps:latest
    restart: unless-stopped
    ports:
      - "7000:7000"
      - "80:80"
      - "443:443"
    volumes:
      - ./frps.toml:/etc/frp/frps.toml
      - ./certs:/etc/frp/certs
    environment:
      - FRP_TOKEN=${FRP_TOKEN}
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:7500/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### SSL Certificate Auto-Renewal
```python
class CertbotManager:
    """Manages Let's Encrypt certificates with Certbot"""

    def __init__(self, domain: str, email: str):
        self.domain = domain
        self.email = email

    def obtain_certificate(self) -> tuple[str, str]:
        """Obtain new certificate"""
        cmd = [
            "certbot", "certonly",
            "--standalone",
            "-d", self.domain,
            "--email", self.email,
            "--agree-tos",
            "--non-interactive"
        ]
        # Run certbot
        # Return (cert_path, key_path)

    def setup_auto_renewal(self) -> None:
        """Setup cron job for auto-renewal"""
        cron_job = "0 0 * * * certbot renew --quiet --post-hook 'systemctl reload frps'"
        # Add to crontab
```

#### Server Monitoring API
```python
class ServerMonitor:
    """Monitors FRP server status"""

    async def get_status(self) -> ServerStatus:
        """Get current server status"""
        # Check process running
        # Check port listening
        # Check recent logs for errors
        # Get connection count

    async def get_metrics(self) -> dict:
        """Get server metrics"""
        # CPU usage
        # Memory usage
        # Connection count
        # Bandwidth usage
        # Error rate
```

---

## Checkpoint 7: Monitoring & Observability

### Enhanced Implementation Requirements

#### Metrics Collection Configuration
```python
class MetricsConfig(BaseModel):
    """Configuration for metrics collection"""

    collection_interval: float = Field(default=60.0, description="Seconds between collections")
    retention_period: timedelta = Field(default=timedelta(days=7))

    # Metric-specific intervals
    tunnel_metrics_interval: float = 30.0
    system_metrics_interval: float = 60.0
    error_metrics_interval: float = 10.0
```

#### Alert Threshold Configuration
```python
class AlertThreshold(BaseModel):
    """Configurable alert thresholds"""

    metric_name: str
    operator: Literal["gt", "lt", "eq", "gte", "lte"]
    value: float
    duration: timedelta = timedelta(minutes=5)
    severity: Literal["info", "warning", "critical"]

    def check(self, current_value: float) -> bool:
        """Check if threshold is exceeded"""

class AlertManager:
    """Manages metric alerts"""

    def __init__(self):
        self.thresholds: list[AlertThreshold] = []
        self.alert_history: deque[Alert] = deque(maxlen=1000)

    def add_threshold(self, threshold: AlertThreshold) -> None:
        """Add alert threshold"""

    def check_thresholds(self, metrics: dict[str, float]) -> list[Alert]:
        """Check all thresholds against current metrics"""
```

#### Log Rotation Implementation
```python
class LogRotator:
    """Handles log rotation with size and time limits"""

    def __init__(self,
                 log_file: Path,
                 max_size: int = 100 * 1024 * 1024,  # 100MB
                 max_files: int = 10,
                 compress: bool = True):
        self.log_file = log_file
        self.max_size = max_size
        self.max_files = max_files
        self.compress = compress

    def should_rotate(self) -> bool:
        """Check if rotation needed"""
        return self.log_file.stat().st_size >= self.max_size

    def rotate(self) -> None:
        """Perform log rotation"""
        # Rename current log
        # Compress if enabled
        # Delete old logs beyond max_files
```

#### Prometheus/Grafana Integration
```python
# Prometheus metrics endpoint
from prometheus_client import Counter, Gauge, Histogram, generate_latest

# Define metrics
tunnel_count = Gauge('frp_tunnel_count', 'Number of active tunnels', ['type'])
tunnel_traffic = Counter('frp_tunnel_traffic_bytes', 'Tunnel traffic in bytes', ['tunnel_id', 'direction'])
tunnel_latency = Histogram('frp_tunnel_latency_seconds', 'Tunnel latency', ['tunnel_id'])

class PrometheusExporter:
    """Exports metrics in Prometheus format"""

    def __init__(self, port: int = 9090):
        self.port = port
        self.app = FastAPI()

    def export_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        return generate_latest()
```

---

## Checkpoint 8: Examples & Documentation

### Enhanced Implementation Requirements

#### Real-World Use Case Examples

##### Web Development Server
```python
# examples/web_dev_server.py
"""Expose local development server with hot reload support"""

from frp_wrapper import FRPClient
import os

def expose_dev_server():
    # Detect framework
    if os.path.exists("package.json"):
        port = 3000  # React/Next.js default
    elif os.path.exists("manage.py"):
        port = 8000  # Django default
    else:
        port = 5000  # Flask default

    with FRPClient("tunnel.example.com") as client:
        with client.tunnel(port, "dev", websocket=True) as tunnel:
            print(f"🚀 Dev server available at: {tunnel.url}")
            print("Press Ctrl+C to stop")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\\nShutting down tunnel...")
```

##### Database Tunneling
```python
# examples/database_tunnel.py
"""Secure database access through FRP tunnel"""

from frp_wrapper import FRPClient, TCPTunnel
import psycopg2

def create_db_tunnel():
    with FRPClient("tunnel.example.com") as client:
        # Expose PostgreSQL
        pg_tunnel = client.expose_tcp(5432, remote_port=15432)

        # Expose Redis
        redis_tunnel = client.expose_tcp(6379, remote_port=16379)

        print(f"PostgreSQL: {pg_tunnel.endpoint}")
        print(f"Redis: {redis_tunnel.endpoint}")

        # Example connection
        conn = psycopg2.connect(
            host=client.server,
            port=15432,
            database="mydb",
            user="user",
            password="pass"
        )
```

##### WebSocket Application
```python
# examples/websocket_app.py
"""WebSocket application with FRP"""

from frp_wrapper import FRPClient
import asyncio
import websockets

async def handle_websocket(websocket, path):
    async for message in websocket:
        await websocket.send(f"Echo: {message}")

async def main():
    # Start WebSocket server
    server = await websockets.serve(handle_websocket, "localhost", 8765)

    # Expose through FRP
    with FRPClient("tunnel.example.com") as client:
        tunnel = client.expose_path(8765, "ws", websocket=True)
        print(f"WebSocket endpoint: {tunnel.websocket_url}")

        await asyncio.Future()  # Run forever
```

#### Troubleshooting Guide
```markdown
# Troubleshooting Guide

## Common Issues

### 1. Binary Not Found
**Error**: `BinaryNotFoundError: frpc binary not found`

**Solutions**:
- Install FRP: `wget https://github.com/fatedier/frp/releases/download/v0.51.0/frp_0.51.0_linux_amd64.tar.gz`
- Set environment variable: `export FRP_BINARY_PATH=/path/to/frpc`
- Pass binary path: `FRPClient(binary_path="/custom/path/frpc")`

### 2. Connection Failed
**Error**: `ConnectionError: Failed to connect to server`

**Solutions**:
- Check server address and port
- Verify authentication token
- Check firewall rules
- Test with `telnet server.com 7000`

### 3. Port Already in Use
**Error**: `OSError: [Errno 48] Address already in use`

**Solutions**:
- Find process: `lsof -i :PORT`
- Kill process: `kill -9 PID`
- Use different port

### 4. Path Conflicts
**Error**: `TunnelError: Path /api already in use`

**Solutions**:
- Use unique paths for each tunnel
- Check existing tunnels: `client.list_tunnels()`
- Use path prefixes: `/app1/api`, `/app2/api`
```

#### Performance Tuning Guide
```markdown
# Performance Tuning Guide

## Client-Side Optimization

### 1. Connection Pooling
```python
# Reuse client connections
client = FRPClient("server.com", max_pool_size=10)
```

### 2. Compression
```python
# Enable compression for HTTP tunnels
tunnel = client.expose_path(3000, "app", compression=True)
```

### 3. Keep-Alive Settings
```python
# Adjust heartbeat for stable connections
client = FRPClient("server.com", heartbeat_interval=30)
```

## Server-Side Optimization

### 1. Increase Connection Limits
```toml
[common]
max_pool_count = 50
max_ports_per_client = 20
```

### 2. Enable KCP Protocol
```toml
[common]
kcp_bind_port = 7000
```

### 3. Optimize Buffer Sizes
```toml
[common]
tcp_mux_keepalive_interval = 30
```

## Monitoring Performance

### 1. Enable Metrics
```python
client = FRPClient("server.com", enable_metrics=True)
metrics = client.get_metrics()
print(f"Latency: {metrics.avg_latency}ms")
```

### 2. Use Prometheus
```python
from frp_wrapper.monitoring import PrometheusExporter
exporter = PrometheusExporter(client)
exporter.start(port=9090)
```
```

#### Security Best Practices
```markdown
# Security Best Practices

## Authentication

### 1. Strong Tokens
```python
import secrets
token = secrets.token_urlsafe(32)
client = FRPClient("server.com", auth_token=token)
```

### 2. Token Rotation
```python
# Rotate tokens periodically
client.rotate_token(new_token)
```

## Encryption

### 1. Enable TLS
```python
client = FRPClient("server.com", tls_enable=True)
```

### 2. Certificate Validation
```python
client = FRPClient(
    "server.com",
    tls_cert_path="/path/to/cert.pem",
    tls_verify=True
)
```

## Access Control

### 1. IP Whitelisting
```toml
[common]
allow_ports = "3000-4000"
```

### 2. Rate Limiting
```python
tunnel = client.expose_path(
    3000, "api",
    rate_limit=100,  # requests per minute
)
```

## Monitoring

### 1. Audit Logging
```python
client = FRPClient("server.com", audit_log=True)
```

### 2. Intrusion Detection
```python
from frp_wrapper.security import IntrusionDetector
detector = IntrusionDetector(client)
detector.add_rule("suspicious_pattern", action="block")
```
```
