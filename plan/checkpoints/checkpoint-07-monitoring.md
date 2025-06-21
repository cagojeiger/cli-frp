# Checkpoint 7: 모니터링 및 로깅

## 개요
터널 상태 모니터링, 구조화된 로깅, 메트릭 수집 기능을 구현합니다. 운영 중 발생하는 문제를 빠르게 감지하고 디버깅할 수 있는 도구를 제공합니다.

## 목표
- 구조화된 로깅 시스템 구축
- 터널 상태 실시간 모니터링
- 이벤트 기반 알림 시스템
- 메트릭 수집 및 분석

## 구현 범위

### 1. 로깅 시스템
```python
import structlog
from typing import Any, Dict, Optional
from enum import Enum

class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class FRPLogger:
    """구조화된 로깅을 위한 래퍼"""
    
    def __init__(self, name: str, level: LogLevel = LogLevel.INFO):
        self.logger = structlog.get_logger(name)
        self.level = level
        self._configure_structlog()
        
    def _configure_structlog(self):
        """structlog 설정"""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
    def log_tunnel_event(
        self,
        event: str,
        tunnel_id: str,
        **kwargs
    ):
        """터널 관련 이벤트 로깅"""
        self.logger.info(
            event,
            tunnel_id=tunnel_id,
            **kwargs
        )
        
    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ):
        """에러 로깅"""
        self.logger.error(
            "error_occurred",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context or {}
        )
```

### 2. 터널 모니터링
```python
@dataclass
class TunnelMetrics:
    """터널 메트릭 정보"""
    tunnel_id: str
    bytes_sent: int = 0
    bytes_received: int = 0
    connection_count: int = 0
    error_count: int = 0
    last_activity: Optional[datetime] = None
    uptime_seconds: float = 0.0

class TunnelMonitor:
    """터널 상태 모니터링"""
    
    def __init__(self, check_interval: float = 5.0):
        self.check_interval = check_interval
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._metrics: Dict[str, TunnelMetrics] = {}
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
    def start_monitoring(self):
        """모니터링 시작"""
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self._monitor_thread.start()
        
    def stop_monitoring(self):
        """모니터링 중지"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join()
            
    def register_callback(
        self,
        event: str,
        callback: Callable[[str, TunnelMetrics], None]
    ):
        """이벤트 콜백 등록"""
        self._callbacks[event].append(callback)
        
    def get_metrics(self, tunnel_id: str) -> Optional[TunnelMetrics]:
        """특정 터널의 메트릭 조회"""
        return self._metrics.get(tunnel_id)
        
    def _monitor_loop(self):
        """모니터링 루프"""
        while self._monitoring:
            for tunnel_id, metrics in self._metrics.items():
                # 상태 체크 로직
                self._check_tunnel_health(tunnel_id, metrics)
            time.sleep(self.check_interval)
            
    def _check_tunnel_health(
        self,
        tunnel_id: str,
        metrics: TunnelMetrics
    ):
        """터널 상태 확인"""
        # 구현 예정
        pass
```

### 3. 이벤트 시스템
```python
class EventType(Enum):
    TUNNEL_CREATED = "tunnel_created"
    TUNNEL_CONNECTED = "tunnel_connected"
    TUNNEL_DISCONNECTED = "tunnel_disconnected"
    TUNNEL_ERROR = "tunnel_error"
    TUNNEL_CLOSED = "tunnel_closed"
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"
    METRIC_THRESHOLD = "metric_threshold"

class EventEmitter:
    """이벤트 발생 및 처리"""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._logger = FRPLogger("event_emitter")
        
    def on(
        self,
        event_type: EventType,
        handler: Callable[[Dict[str, Any]], None]
    ):
        """이벤트 핸들러 등록"""
        self._handlers[event_type].append(handler)
        
    def emit(
        self,
        event_type: EventType,
        data: Dict[str, Any]
    ):
        """이벤트 발생"""
        self._logger.log_tunnel_event(
            f"event_emitted_{event_type.value}",
            tunnel_id=data.get('tunnel_id', 'N/A'),
            event_data=data
        )
        
        for handler in self._handlers[event_type]:
            try:
                handler(data)
            except Exception as e:
                self._logger.log_error(e, {'event_type': event_type.value})
```

### 4. 상태 대시보드
```python
class MonitoringDashboard:
    """간단한 모니터링 대시보드"""
    
    def __init__(self, client: FRPClient):
        self.client = client
        self.monitor = TunnelMonitor()
        self._server: Optional[HTTPServer] = None
        
    def start(self, port: int = 9999):
        """대시보드 서버 시작"""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        
        class DashboardHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/api/status':
                    self._serve_status()
                elif self.path == '/':
                    self._serve_dashboard()
                    
        self._server = HTTPServer(('', port), DashboardHandler)
        threading.Thread(
            target=self._server.serve_forever,
            daemon=True
        ).start()
        
    def get_status(self) -> Dict[str, Any]:
        """현재 상태 정보"""
        return {
            'client': {
                'connected': self.client.is_connected(),
                'server': self.client.server,
                'uptime': self.client.get_uptime()
            },
            'tunnels': [
                {
                    'id': tunnel.id,
                    'type': tunnel.config.tunnel_type,
                    'local_port': tunnel.config.local_port,
                    'url': tunnel.url,
                    'status': tunnel.status.value,
                    'metrics': self.monitor.get_metrics(tunnel.id)
                }
                for tunnel in self.client.list_tunnels()
            ]
        }
```

## 테스트 시나리오

### 유닛 테스트

1. **구조화된 로깅**
   ```python
   def test_structured_logging():
       logger = FRPLogger("test")
       
       # 로그 캡처
       with capture_logs() as cap_logs:
           logger.log_tunnel_event(
               "tunnel_created",
               "tunnel_123",
               local_port=3000,
               remote_port=8080
           )
       
       log = cap_logs[0]
       assert log['event'] == 'tunnel_created'
       assert log['tunnel_id'] == 'tunnel_123'
       assert log['local_port'] == 3000
   ```

2. **메트릭 수집**
   ```python
   def test_tunnel_metrics():
       monitor = TunnelMonitor()
       monitor.start_monitoring()
       
       # 메트릭 업데이트
       metrics = TunnelMetrics(tunnel_id="test_tunnel")
       metrics.bytes_sent = 1024
       metrics.connection_count = 5
       
       monitor._metrics["test_tunnel"] = metrics
       
       retrieved = monitor.get_metrics("test_tunnel")
       assert retrieved.bytes_sent == 1024
       assert retrieved.connection_count == 5
   ```

3. **이벤트 시스템**
   ```python
   def test_event_system():
       emitter = EventEmitter()
       received_events = []
       
       def handler(data):
           received_events.append(data)
       
       emitter.on(EventType.TUNNEL_CREATED, handler)
       emitter.emit(EventType.TUNNEL_CREATED, {
           'tunnel_id': 'test_123',
           'local_port': 3000
       })
       
       assert len(received_events) == 1
       assert received_events[0]['tunnel_id'] == 'test_123'
   ```

4. **상태 임계값 알림**
   ```python
   def test_threshold_alerts():
       monitor = TunnelMonitor()
       alerts = []
       
       def alert_handler(tunnel_id, metrics):
           alerts.append((tunnel_id, metrics))
       
       monitor.register_callback('high_error_rate', alert_handler)
       
       # 높은 에러율 시뮬레이션
       metrics = TunnelMetrics(tunnel_id="test")
       metrics.error_count = 100
       metrics.connection_count = 110
       
       monitor._check_tunnel_health("test", metrics)
       
       assert len(alerts) == 1
       assert alerts[0][0] == "test"
   ```

### 통합 테스트

1. **실시간 모니터링**
   ```python
   @pytest.mark.integration
   def test_real_time_monitoring():
       client = FRPClient("localhost")
       monitor = TunnelMonitor()
       
       with client:
           tunnel = client.expose_tcp(3000)
           monitor.start_monitoring()
           
           # 트래픽 생성
           generate_test_traffic(3000)
           
           time.sleep(10)  # 메트릭 수집 대기
           
           metrics = monitor.get_metrics(tunnel.id)
           assert metrics.bytes_sent > 0
           assert metrics.connection_count > 0
   ```

2. **대시보드 테스트**
   ```python
   def test_monitoring_dashboard():
       client = FRPClient("localhost")
       dashboard = MonitoringDashboard(client)
       
       dashboard.start(9999)
       
       with client:
           tunnel1 = client.expose_tcp(3000)
           tunnel2 = client.expose_path(8000, "api")
           
           # API 엔드포인트 테스트
           response = requests.get("http://localhost:9999/api/status")
           status = response.json()
           
           assert status['client']['connected']
           assert len(status['tunnels']) == 2
   ```

## 구현 상세

### 프로세스 출력 파싱
```python
class OutputParser:
    """FRP 프로세스 출력 파싱"""
    
    # 정규표현식 패턴
    PATTERNS = {
        'tunnel_connected': re.compile(
            r'\[(.+?)\] \[I\] \[proxy\] \[(.+?)\] proxy started'
        ),
        'tunnel_error': re.compile(
            r'\[(.+?)\] \[E\] \[proxy\] \[(.+?)\] (.+)'
        ),
        'traffic_stats': re.compile(
            r'\[(.+?)\] \[I\] \[proxy\] \[(.+?)\] in:(\d+) out:(\d+)'
        )
    }
    
    def parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """로그 라인 파싱"""
        for event_type, pattern in self.PATTERNS.items():
            match = pattern.match(line)
            if match:
                return self._extract_data(event_type, match)
        return None
        
    def _extract_data(
        self,
        event_type: str,
        match: re.Match
    ) -> Dict[str, Any]:
        """매치된 데이터 추출"""
        if event_type == 'tunnel_connected':
            return {
                'type': 'tunnel_connected',
                'timestamp': match.group(1),
                'tunnel_id': match.group(2)
            }
        # ... 기타 이벤트 타입 처리
```

### 메트릭 집계
```python
class MetricsAggregator:
    """메트릭 집계 및 분석"""
    
    def __init__(self, window_size: int = 300):  # 5분 윈도우
        self.window_size = window_size
        self._data_points: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        
    def add_data_point(
        self,
        tunnel_id: str,
        metric_type: str,
        value: float,
        timestamp: Optional[datetime] = None
    ):
        """데이터 포인트 추가"""
        timestamp = timestamp or datetime.now()
        key = f"{tunnel_id}:{metric_type}"
        self._data_points[key].append((timestamp, value))
        
    def get_average(
        self,
        tunnel_id: str,
        metric_type: str,
        time_range: Optional[int] = None
    ) -> float:
        """평균값 계산"""
        key = f"{tunnel_id}:{metric_type}"
        points = self._data_points.get(key, [])
        
        if not points:
            return 0.0
            
        if time_range:
            cutoff = datetime.now() - timedelta(seconds=time_range)
            points = [(t, v) for t, v in points if t > cutoff]
            
        return sum(v for _, v in points) / len(points)
```

## 파일 구조
```
frp_wrapper/
├── monitoring/
│   ├── __init__.py
│   ├── logger.py       # 로깅 시스템
│   ├── monitor.py      # 터널 모니터링
│   ├── events.py       # 이벤트 시스템
│   ├── metrics.py      # 메트릭 수집
│   ├── dashboard.py    # 대시보드
│   └── parser.py       # 출력 파싱
└── client.py           # 모니터링 통합

tests/
├── test_logging.py
├── test_monitoring.py
├── test_events.py
├── test_metrics.py
└── test_dashboard.py
```

## 완료 기준

### 필수 기능
- [x] 구조화된 로깅
- [x] 터널 상태 모니터링
- [x] 이벤트 시스템
- [x] 메트릭 수집
- [x] 기본 대시보드

### 테스트
- [x] 로깅 출력 테스트
- [x] 이벤트 발생/처리 테스트
- [x] 메트릭 집계 테스트
- [x] 대시보드 API 테스트

### 문서
- [x] 로깅 설정 가이드
- [x] 모니터링 API 문서
- [x] 이벤트 타입 설명

## 예상 작업 시간
- 로깅 시스템: 3시간
- 모니터링 구현: 4시간
- 이벤트 시스템: 3시간
- 대시보드: 3시간
- 테스트 작성: 4시간

**총 예상 시간**: 17시간 (3일)

## 다음 단계 준비
- 예제 코드 작성
- 전체 문서 정리
- 패키지 배포 준비

## 의존성
- structlog
- threading
- http.server (표준 라이브러리)
- Optional: prometheus_client

## 주의사항
- 스레드 안전성
- 메모리 사용량 관리
- 로그 파일 크기 제한
- 성능 영향 최소화