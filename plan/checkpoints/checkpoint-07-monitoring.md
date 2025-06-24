# Checkpoint 7: Unified Monitoring & Observability (TDD Approach)

## Overview
TDD와 Pydantic v2를 활용하여 **클라이언트 터널과 FRP 서버 전체**에 대한 통합 모니터링, 로깅, 메트릭 수집 시스템을 구현합니다. 구조화된 로깅과 강력한 타입 안전성을 제공합니다.

## Goals
- **클라이언트 모니터링**: 터널 상태, 트래픽, 성능 메트릭
- **서버 모니터링**: 서버 상태, 연결된 클라이언트, 리소스 사용량
- **통합 대시보드**: 클라이언트-서버 전체 시스템 가시성
- Pydantic 기반 모니터링 설정 및 메트릭 모델
- 구조화된 로깅 시스템 구축
- 실시간 상태 모니터링 및 이벤트 기반 알림
- TDD 방식의 완전한 테스트 커버리지

## Test-First Implementation with Pydantic

### 1. Monitoring Configuration and Models

```python
# src/frp_wrapper/monitoring/models.py
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any, Union, Callable
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field
from pydantic import IPvAnyAddress, HttpUrl

class LogLevel(str, Enum):
    """Logging levels"""
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MetricType(str, Enum):
    """Types of metrics collected"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

class EventType(str, Enum):
    """Event types for monitoring"""
    # Client tunnel events
    TUNNEL_CREATED = "tunnel_created"
    TUNNEL_CONNECTED = "tunnel_connected"
    TUNNEL_DISCONNECTED = "tunnel_disconnected"
    TUNNEL_ERROR = "tunnel_error"
    TUNNEL_CLOSED = "tunnel_closed"
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"

    # Server events
    SERVER_STARTED = "server_started"
    SERVER_STOPPED = "server_stopped"
    SERVER_ERROR = "server_error"
    SERVER_CLIENT_CONNECTED = "server_client_connected"
    SERVER_CLIENT_DISCONNECTED = "server_client_disconnected"
    SERVER_RESOURCE_WARNING = "server_resource_warning"

    # Monitoring events
    METRIC_THRESHOLD_EXCEEDED = "metric_threshold_exceeded"
    HEALTH_CHECK_FAILED = "health_check_failed"

class LoggingConfig(BaseModel):
    """Pydantic configuration for logging system"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    # Basic logging settings
    level: LogLevel = Field(default=LogLevel.INFO, description="Minimum log level")
    format: str = Field(default="json", pattern="^(json|text)$", description="Log format")

    # File logging
    enable_file_logging: bool = Field(default=True, description="Enable file logging")
    log_file: Optional[str] = Field(None, description="Log file path")
    max_file_size_mb: int = Field(default=100, ge=1, le=1000, description="Maximum log file size in MB")
    backup_count: int = Field(default=5, ge=1, le=50, description="Number of backup log files")

    # Console logging
    enable_console_logging: bool = Field(default=True, description="Enable console logging")
    console_level: LogLevel = Field(default=LogLevel.INFO, description="Console log level")

    # Structured logging
    include_caller_info: bool = Field(default=True, description="Include caller file/line info")
    include_process_info: bool = Field(default=True, description="Include process/thread info")

    @field_validator('log_file')
    @classmethod
    def validate_log_file_path(cls, v: Optional[str]) -> Optional[str]:
        """Validate log file path"""
        if v is not None:
            if not v or len(v.strip()) == 0:
                raise ValueError("Log file path cannot be empty")
            # Additional path validation could be added here
        return v

class TunnelMetrics(BaseModel):
    """Pydantic model for tunnel metrics"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    tunnel_id: str = Field(..., min_length=1, description="Tunnel identifier")

    # Traffic metrics
    bytes_sent: int = Field(default=0, ge=0, description="Total bytes sent")
    bytes_received: int = Field(default=0, ge=0, description="Total bytes received")
    packets_sent: int = Field(default=0, ge=0, description="Total packets sent")
    packets_received: int = Field(default=0, ge=0, description="Total packets received")

    # Connection metrics
    total_connections: int = Field(default=0, ge=0, description="Total connections established")
    active_connections: int = Field(default=0, ge=0, description="Currently active connections")
    failed_connections: int = Field(default=0, ge=0, description="Failed connection attempts")

    # Error metrics
    error_count: int = Field(default=0, ge=0, description="Total error count")
    last_error_time: Optional[datetime] = Field(None, description="Last error timestamp")

    # Performance metrics
    average_latency_ms: float = Field(default=0.0, ge=0, description="Average latency in milliseconds")
    max_latency_ms: float = Field(default=0.0, ge=0, description="Maximum latency in milliseconds")

    # Status tracking
    created_at: datetime = Field(default_factory=datetime.now, description="Metrics creation time")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    uptime_seconds: float = Field(default=0.0, ge=0, description="Tunnel uptime in seconds")

    @computed_field
    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage"""
        if self.total_connections == 0:
            return 0.0
        return (self.error_count / self.total_connections) * 100

    @computed_field
    @property
    def throughput_mbps(self) -> float:
        """Calculate throughput in Mbps"""
        if self.uptime_seconds == 0:
            return 0.0
        total_bytes = self.bytes_sent + self.bytes_received
        return (total_bytes * 8) / (self.uptime_seconds * 1_000_000)  # Convert to Mbps

    def update_activity(self) -> 'TunnelMetrics':
        """Update last activity timestamp"""
        return self.model_copy(update={'last_activity': datetime.now()})

    def add_traffic(self, bytes_sent: int = 0, bytes_received: int = 0) -> 'TunnelMetrics':
        """Add traffic data and update activity"""
        return self.model_copy(update={
            'bytes_sent': self.bytes_sent + bytes_sent,
            'bytes_received': self.bytes_received + bytes_received,
            'last_activity': datetime.now()
        })

class ServerMetrics(BaseModel):
    """Pydantic model for FRP server metrics"""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    server_id: str = Field(..., min_length=1, description="Server identifier")

    # Server status
    server_status: str = Field(default="unknown", description="Current server status")
    bind_port: int = Field(..., ge=1, le=65535, description="Server bind port")
    uptime_seconds: float = Field(default=0.0, ge=0, description="Server uptime in seconds")

    # Client connections
    total_clients_connected: int = Field(default=0, ge=0, description="Total clients ever connected")
    active_clients: int = Field(default=0, ge=0, description="Currently active clients")
    max_concurrent_clients: int = Field(default=0, ge=0, description="Maximum concurrent clients")

    # Proxy statistics
    total_proxies: int = Field(default=0, ge=0, description="Total active proxies")
    http_proxies: int = Field(default=0, ge=0, description="Active HTTP proxies")
    tcp_proxies: int = Field(default=0, ge=0, description="Active TCP proxies")

    # Traffic metrics (aggregated from all clients)
    total_bytes_in: int = Field(default=0, ge=0, description="Total bytes received")
    total_bytes_out: int = Field(default=0, ge=0, description="Total bytes sent")
    bytes_in_per_second: float = Field(default=0.0, ge=0, description="Current bytes in per second")
    bytes_out_per_second: float = Field(default=0.0, ge=0, description="Current bytes out per second")

    # Resource usage
    cpu_usage_percent: float = Field(default=0.0, ge=0, le=100, description="CPU usage percentage")
    memory_usage_mb: float = Field(default=0.0, ge=0, description="Memory usage in MB")
    open_file_descriptors: int = Field(default=0, ge=0, description="Number of open file descriptors")

    # Dashboard metrics
    dashboard_enabled: bool = Field(default=False, description="Whether dashboard is enabled")
    dashboard_port: Optional[int] = Field(None, ge=1, le=65535, description="Dashboard port if enabled")
    dashboard_active_sessions: int = Field(default=0, ge=0, description="Active dashboard sessions")

    # Error tracking
    error_count: int = Field(default=0, ge=0, description="Total error count")
    last_error_time: Optional[datetime] = Field(None, description="Last error timestamp")
    authentication_failures: int = Field(default=0, ge=0, description="Authentication failure count")

    # Timing
    created_at: datetime = Field(default_factory=datetime.now, description="Metrics creation time")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

    @computed_field
    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage"""
        if self.total_clients_connected == 0:
            return 0.0
        return (self.error_count / self.total_clients_connected) * 100

    @computed_field
    @property
    def total_throughput_mbps(self) -> float:
        """Calculate total throughput in Mbps"""
        if self.uptime_seconds == 0:
            return 0.0
        total_bytes = self.total_bytes_in + self.total_bytes_out
        return (total_bytes * 8) / (self.uptime_seconds * 1_000_000)

    @computed_field
    @property
    def client_utilization(self) -> float:
        """Calculate client utilization percentage"""
        if self.max_concurrent_clients == 0:
            return 0.0
        return (self.active_clients / self.max_concurrent_clients) * 100

    def update_uptime(self, start_time: datetime) -> 'ServerMetrics':
        """Update server uptime"""
        uptime = (datetime.now() - start_time).total_seconds()
        return self.model_copy(update={
            'uptime_seconds': uptime,
            'last_updated': datetime.now()
        })

    def add_client_connection(self) -> 'ServerMetrics':
        """Add a new client connection"""
        new_active = self.active_clients + 1
        return self.model_copy(update={
            'total_clients_connected': self.total_clients_connected + 1,
            'active_clients': new_active,
            'max_concurrent_clients': max(self.max_concurrent_clients, new_active),
            'last_updated': datetime.now()
        })

    def remove_client_connection(self) -> 'ServerMetrics':
        """Remove a client connection"""
        return self.model_copy(update={
            'active_clients': max(0, self.active_clients - 1),
            'last_updated': datetime.now()
        })

    def update_traffic(self, bytes_in: int = 0, bytes_out: int = 0) -> 'ServerMetrics':
        """Update traffic statistics"""
        return self.model_copy(update={
            'total_bytes_in': self.total_bytes_in + bytes_in,
            'total_bytes_out': self.total_bytes_out + bytes_out,
            'last_updated': datetime.now()
        })

    def update_resource_usage(self, cpu_percent: float, memory_mb: float, open_fds: int) -> 'ServerMetrics':
        """Update resource usage metrics"""
        return self.model_copy(update={
            'cpu_usage_percent': cpu_percent,
            'memory_usage_mb': memory_mb,
            'open_file_descriptors': open_fds,
            'last_updated': datetime.now()
        })

class MonitoringAlert(BaseModel):
    """Pydantic model for monitoring alerts"""

    model_config = ConfigDict(str_strip_whitespace=True)

    alert_id: str = Field(..., min_length=1, description="Unique alert identifier")
    alert_type: str = Field(..., min_length=1, description="Type of alert")
    severity: str = Field(..., pattern="^(low|medium|high|critical)$", description="Alert severity")
    message: str = Field(..., min_length=1, description="Alert message")

    # Context information
    tunnel_id: Optional[str] = Field(None, description="Related tunnel ID")
    server_id: Optional[str] = Field(None, description="Related server ID")
    client_id: Optional[str] = Field(None, description="Related client ID")
    metric_name: Optional[str] = Field(None, description="Related metric name")
    metric_value: Optional[float] = Field(None, description="Metric value that triggered alert")
    threshold_value: Optional[float] = Field(None, description="Threshold that was exceeded")

    # Timing
    created_at: datetime = Field(default_factory=datetime.now, description="Alert creation time")
    resolved_at: Optional[datetime] = Field(None, description="Alert resolution time")

    @computed_field
    @property
    def is_resolved(self) -> bool:
        """Check if alert is resolved"""
        return self.resolved_at is not None

    @computed_field
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate alert duration in seconds"""
        if self.resolved_at is None:
            return None
        return (self.resolved_at - self.created_at).total_seconds()

class MonitoringConfig(BaseModel):
    """Complete monitoring system configuration"""

    model_config = ConfigDict(str_strip_whitespace=True)

    # Logging configuration
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Monitoring intervals
    metrics_collection_interval: float = Field(default=5.0, ge=0.1, le=300.0, description="Metrics collection interval in seconds")
    health_check_interval: float = Field(default=30.0, ge=1.0, le=3600.0, description="Health check interval in seconds")

    # Client alert thresholds
    error_rate_threshold: float = Field(default=5.0, ge=0.0, le=100.0, description="Error rate threshold percentage")
    latency_threshold_ms: float = Field(default=1000.0, ge=0.0, description="Latency threshold in milliseconds")
    connection_threshold: int = Field(default=1000, ge=1, description="Maximum concurrent connections")

    # Server alert thresholds
    server_cpu_threshold: float = Field(default=80.0, ge=0.0, le=100.0, description="Server CPU usage threshold percentage")
    server_memory_threshold_mb: float = Field(default=1024.0, ge=0.0, description="Server memory usage threshold in MB")
    server_client_threshold: int = Field(default=100, ge=1, description="Maximum concurrent server clients")
    server_error_rate_threshold: float = Field(default=10.0, ge=0.0, le=100.0, description="Server error rate threshold percentage")

    # Data retention
    metrics_retention_hours: int = Field(default=24, ge=1, le=8760, description="Metrics retention period in hours")
    alert_retention_days: int = Field(default=30, ge=1, le=365, description="Alert retention period in days")

    # Dashboard settings
    enable_dashboard: bool = Field(default=False, description="Enable web dashboard")
    dashboard_port: int = Field(default=9999, ge=1, le=65535, description="Dashboard port")
    dashboard_host: str = Field(default="localhost", description="Dashboard host")

    @field_validator('metrics_collection_interval')
    @classmethod
    def validate_collection_interval(cls, v: float) -> float:
        """Ensure reasonable collection interval"""
        if v < 0.1:
            raise ValueError("Collection interval too small, minimum 0.1 seconds")
        if v > 300:
            raise ValueError("Collection interval too large, maximum 300 seconds")
        return v

class LogEvent(BaseModel):
    """Pydantic model for structured log events"""

    model_config = ConfigDict(str_strip_whitespace=True)

    # Basic event info
    timestamp: datetime = Field(default_factory=datetime.now)
    level: LogLevel = Field(..., description="Log level")
    logger_name: str = Field(..., min_length=1, description="Logger name")
    message: str = Field(..., description="Log message")

    # Context information
    tunnel_id: Optional[str] = Field(None, description="Related tunnel ID")
    server_id: Optional[str] = Field(None, description="Related server ID")
    client_id: Optional[str] = Field(None, description="Related client ID")
    event_type: Optional[EventType] = Field(None, description="Event type")

    # Technical details
    module: Optional[str] = Field(None, description="Source module")
    function: Optional[str] = Field(None, description="Source function")
    line_number: Optional[int] = Field(None, ge=1, description="Source line number")
    process_id: Optional[int] = Field(None, description="Process ID")
    thread_name: Optional[str] = Field(None, description="Thread name")

    # Additional context
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="Additional contextual data")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return self.model_dump(mode='json', exclude_none=True)
```

### 2. Enhanced Monitoring Tests

```python
# tests/test_monitoring_models.py
import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from frp_wrapper.monitoring.models import (
    LoggingConfig, TunnelMetrics, ServerMetrics, MonitoringAlert, MonitoringConfig,
    LogEvent, LogLevel, EventType
)

class TestLoggingConfig:
    def test_logging_config_defaults(self):
        """Test LoggingConfig creation with default values"""
        config = LoggingConfig()

        assert config.level == LogLevel.INFO
        assert config.format == "json"
        assert config.enable_file_logging is True
        assert config.max_file_size_mb == 100
        assert config.backup_count == 5
        assert config.enable_console_logging is True

    def test_logging_config_validation_errors(self):
        """Test LoggingConfig validation with invalid values"""
        # Invalid format
        with pytest.raises(ValidationError, match="String should match pattern"):
            LoggingConfig(format="invalid")

        # Invalid file size
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            LoggingConfig(max_file_size_mb=0)

        with pytest.raises(ValidationError, match="less than or equal to 1000"):
            LoggingConfig(max_file_size_mb=1001)

        # Invalid backup count
        with pytest.raises(ValidationError, match="less than or equal to 50"):
            LoggingConfig(backup_count=51)

    def test_log_file_validation(self):
        """Test log file path validation"""
        # Valid log file
        config = LoggingConfig(log_file="/var/log/frp/frps.log")
        assert config.log_file == "/var/log/frp/frps.log"

        # Empty log file
        with pytest.raises(ValidationError, match="cannot be empty"):
            LoggingConfig(log_file="")

        with pytest.raises(ValidationError, match="cannot be empty"):
            LoggingConfig(log_file="   ")

class TestTunnelMetrics:
    def test_tunnel_metrics_creation(self):
        """Test TunnelMetrics creation with default values"""
        metrics = TunnelMetrics(tunnel_id="test-tunnel")

        assert metrics.tunnel_id == "test-tunnel"
        assert metrics.bytes_sent == 0
        assert metrics.bytes_received == 0
        assert metrics.total_connections == 0
        assert metrics.error_count == 0
        assert metrics.uptime_seconds == 0.0
        assert isinstance(metrics.created_at, datetime)

    def test_tunnel_metrics_validation_errors(self):
        """Test TunnelMetrics validation with invalid values"""
        # Empty tunnel ID
        with pytest.raises(ValidationError, match="at least 1 character"):
            TunnelMetrics(tunnel_id="")

        # Negative values
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            TunnelMetrics(tunnel_id="test", bytes_sent=-1)

        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            TunnelMetrics(tunnel_id="test", error_count=-1)

    def test_tunnel_metrics_computed_fields(self):
        """Test computed fields in TunnelMetrics"""
        metrics = TunnelMetrics(
            tunnel_id="test-tunnel",
            total_connections=100,
            error_count=5,
            bytes_sent=1_000_000,
            bytes_received=2_000_000,
            uptime_seconds=60.0  # 1 minute
        )

        # Test error rate calculation
        assert metrics.error_rate == 5.0  # 5 errors out of 100 connections = 5%

        # Test throughput calculation (3MB in 60 seconds = 0.4 Mbps)
        expected_throughput = (3_000_000 * 8) / (60 * 1_000_000)
        assert abs(metrics.throughput_mbps - expected_throughput) < 0.001

    def test_tunnel_metrics_update_methods(self):
        """Test update methods for TunnelMetrics"""
        metrics = TunnelMetrics(tunnel_id="test-tunnel")

        # Test activity update
        updated_metrics = metrics.update_activity()
        assert updated_metrics.last_activity is not None
        assert updated_metrics.tunnel_id == "test-tunnel"  # Other fields preserved

        # Test traffic addition
        traffic_metrics = metrics.add_traffic(bytes_sent=1024, bytes_received=2048)
        assert traffic_metrics.bytes_sent == 1024
        assert traffic_metrics.bytes_received == 2048
        assert traffic_metrics.last_activity is not None

    def test_tunnel_metrics_immutability(self):
        """Test that TunnelMetrics is immutable"""
        metrics = TunnelMetrics(tunnel_id="test-tunnel", bytes_sent=1000)
        updated_metrics = metrics.add_traffic(bytes_sent=500)

        # Original should be unchanged
        assert metrics.bytes_sent == 1000
        assert updated_metrics.bytes_sent == 1500

class TestServerMetrics:
    def test_server_metrics_creation(self):
        """Test ServerMetrics creation with default values"""
        metrics = ServerMetrics(server_id="test-server", bind_port=7000)

        assert metrics.server_id == "test-server"
        assert metrics.bind_port == 7000
        assert metrics.server_status == "unknown"
        assert metrics.active_clients == 0
        assert metrics.total_clients_connected == 0
        assert metrics.cpu_usage_percent == 0.0
        assert metrics.memory_usage_mb == 0.0
        assert isinstance(metrics.created_at, datetime)

    def test_server_metrics_validation_errors(self):
        """Test ServerMetrics validation with invalid values"""
        # Empty server ID
        with pytest.raises(ValidationError, match="at least 1 character"):
            ServerMetrics(server_id="", bind_port=7000)

        # Invalid port
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            ServerMetrics(server_id="test", bind_port=0)

        # Invalid CPU percentage
        with pytest.raises(ValidationError, match="less than or equal to 100"):
            ServerMetrics(server_id="test", bind_port=7000, cpu_usage_percent=101.0)

    def test_server_metrics_computed_fields(self):
        """Test computed fields in ServerMetrics"""
        metrics = ServerMetrics(
            server_id="test-server",
            bind_port=7000,
            total_clients_connected=50,
            error_count=3,
            total_bytes_in=1_000_000,
            total_bytes_out=2_000_000,
            uptime_seconds=60.0,  # 1 minute
            active_clients=25,
            max_concurrent_clients=30
        )

        # Test error rate calculation
        assert metrics.error_rate == 6.0  # 3 errors out of 50 clients = 6%

        # Test throughput calculation (3MB in 60 seconds = 0.4 Mbps)
        expected_throughput = (3_000_000 * 8) / (60 * 1_000_000)
        assert abs(metrics.total_throughput_mbps - expected_throughput) < 0.001

        # Test client utilization
        assert metrics.client_utilization == 83.33333333333334  # 25/30 * 100

    def test_server_metrics_update_methods(self):
        """Test update methods for ServerMetrics"""
        metrics = ServerMetrics(server_id="test-server", bind_port=7000)

        # Test client connection
        updated_metrics = metrics.add_client_connection()
        assert updated_metrics.total_clients_connected == 1
        assert updated_metrics.active_clients == 1
        assert updated_metrics.max_concurrent_clients == 1

        # Test client disconnection
        disconnected_metrics = updated_metrics.remove_client_connection()
        assert disconnected_metrics.active_clients == 0
        assert disconnected_metrics.total_clients_connected == 1  # Total doesn't decrease

        # Test traffic update
        traffic_metrics = metrics.update_traffic(bytes_in=1024, bytes_out=2048)
        assert traffic_metrics.total_bytes_in == 1024
        assert traffic_metrics.total_bytes_out == 2048
        assert traffic_metrics.last_updated is not None

        # Test resource usage update
        resource_metrics = metrics.update_resource_usage(cpu_percent=75.5, memory_mb=512.0, open_fds=100)
        assert resource_metrics.cpu_usage_percent == 75.5
        assert resource_metrics.memory_usage_mb == 512.0
        assert resource_metrics.open_file_descriptors == 100

    def test_server_metrics_uptime_calculation(self):
        """Test uptime calculation"""
        start_time = datetime.now() - timedelta(seconds=120)  # 2 minutes ago
        metrics = ServerMetrics(server_id="test-server", bind_port=7000)

        updated_metrics = metrics.update_uptime(start_time)
        assert updated_metrics.uptime_seconds >= 119  # Should be close to 120 seconds
        assert updated_metrics.last_updated is not None

    def test_server_metrics_immutability(self):
        """Test that ServerMetrics is immutable"""
        metrics = ServerMetrics(server_id="test-server", bind_port=7000, active_clients=5)
        updated_metrics = metrics.add_client_connection()

        # Original should be unchanged
        assert metrics.active_clients == 5
        assert updated_metrics.active_clients == 6

class TestMonitoringAlert:
    def test_monitoring_alert_creation(self):
        """Test MonitoringAlert creation"""
        alert = MonitoringAlert(
            alert_id="alert-001",
            alert_type="threshold_exceeded",
            severity="high",
            message="Error rate exceeded threshold",
            tunnel_id="tunnel-123",
            metric_name="error_rate",
            metric_value=10.5,
            threshold_value=5.0
        )

        assert alert.alert_id == "alert-001"
        assert alert.severity == "high"
        assert alert.tunnel_id == "tunnel-123"
        assert alert.metric_value == 10.5
        assert alert.is_resolved is False
        assert alert.duration_seconds is None

    def test_monitoring_alert_validation_errors(self):
        """Test MonitoringAlert validation"""
        # Invalid severity
        with pytest.raises(ValidationError, match="String should match pattern"):
            MonitoringAlert(
                alert_id="test",
                alert_type="test",
                severity="invalid",
                message="test"
            )

        # Empty required fields
        with pytest.raises(ValidationError, match="at least 1 character"):
            MonitoringAlert(
                alert_id="",
                alert_type="test",
                severity="high",
                message="test"
            )

    def test_monitoring_alert_resolution(self):
        """Test alert resolution functionality"""
        alert = MonitoringAlert(
            alert_id="alert-001",
            alert_type="test",
            severity="medium",
            message="Test alert"
        )

        # Initially not resolved
        assert alert.is_resolved is False
        assert alert.duration_seconds is None

        # Resolve alert
        resolved_alert = alert.model_copy(update={'resolved_at': datetime.now()})
        assert resolved_alert.is_resolved is True
        assert resolved_alert.duration_seconds is not None
        assert resolved_alert.duration_seconds >= 0

class TestMonitoringConfig:
    def test_monitoring_config_creation(self):
        """Test MonitoringConfig creation with defaults"""
        config = MonitoringConfig()

        assert isinstance(config.logging, LoggingConfig)
        assert config.metrics_collection_interval == 5.0
        assert config.health_check_interval == 30.0
        assert config.error_rate_threshold == 5.0
        assert config.server_cpu_threshold == 80.0
        assert config.server_memory_threshold_mb == 1024.0
        assert config.server_client_threshold == 100
        assert config.server_error_rate_threshold == 10.0
        assert config.enable_dashboard is False

    def test_monitoring_config_validation_errors(self):
        """Test MonitoringConfig validation"""
        # Invalid collection interval
        with pytest.raises(ValidationError, match="Collection interval too small"):
            MonitoringConfig(metrics_collection_interval=0.05)

        with pytest.raises(ValidationError, match="Collection interval too large"):
            MonitoringConfig(metrics_collection_interval=400.0)

        # Invalid thresholds
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            MonitoringConfig(error_rate_threshold=-1.0)

        with pytest.raises(ValidationError, match="less than or equal to 100"):
            MonitoringConfig(error_rate_threshold=101.0)

    def test_monitoring_config_custom_settings(self):
        """Test MonitoringConfig with custom settings"""
        custom_logging = LoggingConfig(
            level=LogLevel.DEBUG,
            enable_file_logging=False,
            log_file=None
        )

        config = MonitoringConfig(
            logging=custom_logging,
            metrics_collection_interval=1.0,
            error_rate_threshold=10.0,
            enable_dashboard=True,
            dashboard_port=8080
        )

        assert config.logging.level == LogLevel.DEBUG
        assert config.metrics_collection_interval == 1.0
        assert config.error_rate_threshold == 10.0
        assert config.enable_dashboard is True
        assert config.dashboard_port == 8080

class TestLogEvent:
    def test_log_event_creation(self):
        """Test LogEvent creation"""
        event = LogEvent(
            level=LogLevel.INFO,
            logger_name="frp_wrapper.client",
            message="Tunnel connected successfully",
            tunnel_id="tunnel-123",
            event_type=EventType.TUNNEL_CONNECTED,
            module="client.py",
            function="connect_tunnel",
            line_number=42,
            extra_data={"local_port": 3000, "remote_port": 8080}
        )

        assert event.level == LogLevel.INFO
        assert event.logger_name == "frp_wrapper.client"
        assert event.tunnel_id == "tunnel-123"
        assert event.event_type == EventType.TUNNEL_CONNECTED
        assert event.extra_data["local_port"] == 3000
        assert isinstance(event.timestamp, datetime)

    def test_log_event_validation_errors(self):
        """Test LogEvent validation"""
        # Empty logger name
        with pytest.raises(ValidationError, match="at least 1 character"):
            LogEvent(
                level=LogLevel.INFO,
                logger_name="",
                message="test"
            )

        # Invalid line number
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            LogEvent(
                level=LogLevel.INFO,
                logger_name="test",
                message="test",
                line_number=0
            )

    def test_log_event_serialization(self):
        """Test LogEvent serialization to dictionary"""
        event = LogEvent(
            level=LogLevel.ERROR,
            logger_name="test_logger",
            message="Test error message",
            tunnel_id="tunnel-456",
            extra_data={"error_code": 500}
        )

        event_dict = event.to_dict()

        assert event_dict["level"] == "error"
        assert event_dict["logger_name"] == "test_logger"
        assert event_dict["message"] == "Test error message"
        assert event_dict["tunnel_id"] == "tunnel-456"
        assert event_dict["extra_data"]["error_code"] == 500
        assert "timestamp" in event_dict

# Integration tests
class TestMonitoringIntegration:
    def test_complete_monitoring_scenario(self):
        """Test complete monitoring scenario with all models"""
        # Create monitoring configuration
        config = MonitoringConfig(
            metrics_collection_interval=1.0,
            error_rate_threshold=10.0,
            enable_dashboard=True
        )

        # Create tunnel metrics
        metrics = TunnelMetrics(
            tunnel_id="integration-test-tunnel",
            total_connections=50,
            error_count=3,
            bytes_sent=1_000_000,
            uptime_seconds=300.0
        )

        # Check if error rate exceeds threshold
        if metrics.error_rate > config.error_rate_threshold:
            # Create alert
            alert = MonitoringAlert(
                alert_id="alert-integration-001",
                alert_type="error_rate_exceeded",
                severity="medium",
                message=f"Error rate {metrics.error_rate:.1f}% exceeds threshold {config.error_rate_threshold}%",
                tunnel_id=metrics.tunnel_id,
                metric_name="error_rate",
                metric_value=metrics.error_rate,
                threshold_value=config.error_rate_threshold
            )

            # Log the event
            log_event = LogEvent(
                level=LogLevel.WARNING,
                logger_name="monitoring.alerting",
                message=alert.message,
                tunnel_id=metrics.tunnel_id,
                event_type=EventType.METRIC_THRESHOLD_EXCEEDED,
                extra_data={
                    "alert_id": alert.alert_id,
                    "metric_value": alert.metric_value,
                    "threshold": alert.threshold_value
                }
            )

            # Verify everything is properly structured
            assert metrics.error_rate == 6.0  # 3 errors / 50 connections
            assert alert.severity == "medium"
            assert log_event.event_type == EventType.METRIC_THRESHOLD_EXCEEDED
            assert log_event.extra_data["alert_id"] == "alert-integration-001"

    def test_metrics_progression_over_time(self):
        """Test metrics evolution over time"""
        # Initial metrics
        metrics = TunnelMetrics(tunnel_id="time-test-tunnel")

        # Simulate traffic over time
        metrics_t1 = metrics.add_traffic(bytes_sent=1000, bytes_received=500)
        assert metrics_t1.bytes_sent == 1000
        assert metrics_t1.bytes_received == 500

        metrics_t2 = metrics_t1.add_traffic(bytes_sent=2000, bytes_received=1500)
        assert metrics_t2.bytes_sent == 3000
        assert metrics_t2.bytes_received == 2000

        # Verify immutability chain
        assert metrics.bytes_sent == 0  # Original unchanged
        assert metrics_t1.bytes_sent == 1000  # First update unchanged
        assert metrics_t2.bytes_sent == 3000  # Final state

    def test_monitoring_config_serialization(self):
        """Test monitoring configuration serialization"""
        config = MonitoringConfig(
            logging=LoggingConfig(
                level=LogLevel.DEBUG,
                log_file="/var/log/frp/test.log"
            ),
            metrics_collection_interval=2.0,
            error_rate_threshold=15.0,
            enable_dashboard=True,
            dashboard_port=9998
        )

        # Serialize to dict
        config_dict = config.model_dump()

        # Verify structure
        assert config_dict["logging"]["level"] == "debug"
        assert config_dict["logging"]["log_file"] == "/var/log/frp/test.log"
        assert config_dict["metrics_collection_interval"] == 2.0
        assert config_dict["error_rate_threshold"] == 15.0
        assert config_dict["enable_dashboard"] is True

        # Deserialize back
        restored_config = MonitoringConfig.model_validate(config_dict)
        assert restored_config.logging.level == LogLevel.DEBUG
        assert restored_config.error_rate_threshold == 15.0
```

### 3. Monitoring System Implementation

```python
# src/frp_wrapper/monitoring/system.py
import asyncio
import json
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path

from .models import (
    MonitoringConfig, TunnelMetrics, MonitoringAlert, LogEvent,
    LogLevel, EventType, MetricType
)

logger = logging.getLogger(__name__)

class MetricsCollector:
    """TDD-driven metrics collection system"""

    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.metrics: Dict[str, TunnelMetrics] = {}
        self.alerts: List[MonitoringAlert] = []
        self._running = False
        self._collection_thread: Optional[threading.Thread] = None
        self._alert_callbacks: List[Callable[[MonitoringAlert], None]] = []
        self._lock = threading.RLock()

    def start_collection(self) -> None:
        """Start metrics collection"""
        if self._running:
            return

        self._running = True
        self._collection_thread = threading.Thread(
            target=self._collection_loop,
            daemon=True,
            name="MetricsCollector"
        )
        self._collection_thread.start()
        logger.info("Metrics collection started")

    def stop_collection(self) -> None:
        """Stop metrics collection"""
        if not self._running:
            return

        self._running = False
        if self._collection_thread:
            self._collection_thread.join(timeout=5.0)
        logger.info("Metrics collection stopped")

    def register_tunnel(self, tunnel_id: str) -> None:
        """Register new tunnel for monitoring"""
        with self._lock:
            if tunnel_id not in self.metrics:
                self.metrics[tunnel_id] = TunnelMetrics(tunnel_id=tunnel_id)
                logger.info(f"Registered tunnel for monitoring: {tunnel_id}")

    def unregister_tunnel(self, tunnel_id: str) -> None:
        """Unregister tunnel from monitoring"""
        with self._lock:
            if tunnel_id in self.metrics:
                del self.metrics[tunnel_id]
                logger.info(f"Unregistered tunnel from monitoring: {tunnel_id}")

    def update_metrics(self, tunnel_id: str, **updates) -> None:
        """Update metrics for a tunnel"""
        with self._lock:
            if tunnel_id in self.metrics:
                current_metrics = self.metrics[tunnel_id]
                self.metrics[tunnel_id] = current_metrics.model_copy(update=updates)

    def add_traffic(self, tunnel_id: str, bytes_sent: int = 0, bytes_received: int = 0) -> None:
        """Add traffic data for a tunnel"""
        with self._lock:
            if tunnel_id in self.metrics:
                self.metrics[tunnel_id] = self.metrics[tunnel_id].add_traffic(
                    bytes_sent=bytes_sent,
                    bytes_received=bytes_received
                )

    def get_metrics(self, tunnel_id: str) -> Optional[TunnelMetrics]:
        """Get current metrics for a tunnel"""
        with self._lock:
            return self.metrics.get(tunnel_id)

    def get_all_metrics(self) -> Dict[str, TunnelMetrics]:
        """Get all current metrics"""
        with self._lock:
            return self.metrics.copy()

    def add_alert_callback(self, callback: Callable[[MonitoringAlert], None]) -> None:
        """Add callback for alert notifications"""
        self._alert_callbacks.append(callback)

    def _collection_loop(self) -> None:
        """Main collection loop"""
        while self._running:
            try:
                self._collect_and_check()
                time.sleep(self.config.metrics_collection_interval)
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                time.sleep(1.0)  # Avoid tight loop on errors

    def _collect_and_check(self) -> None:
        """Collect metrics and check thresholds"""
        with self._lock:
            current_time = datetime.now()

            for tunnel_id, metrics in self.metrics.items():
                # Update uptime
                uptime_delta = (current_time - metrics.created_at).total_seconds()
                updated_metrics = metrics.model_copy(update={'uptime_seconds': uptime_delta})
                self.metrics[tunnel_id] = updated_metrics

                # Check thresholds
                self._check_thresholds(tunnel_id, updated_metrics)

    def _check_thresholds(self, tunnel_id: str, metrics: TunnelMetrics) -> None:
        """Check if metrics exceed configured thresholds"""
        alerts_to_create = []

        # Check error rate threshold
        if metrics.error_rate > self.config.error_rate_threshold:
            alert = MonitoringAlert(
                alert_id=f"error_rate_{tunnel_id}_{int(datetime.now().timestamp())}",
                alert_type="error_rate_exceeded",
                severity="high" if metrics.error_rate > 20 else "medium",
                message=f"Error rate {metrics.error_rate:.1f}% exceeds threshold {self.config.error_rate_threshold}%",
                tunnel_id=tunnel_id,
                metric_name="error_rate",
                metric_value=metrics.error_rate,
                threshold_value=self.config.error_rate_threshold
            )
            alerts_to_create.append(alert)

        # Check latency threshold
        if metrics.average_latency_ms > self.config.latency_threshold_ms:
            alert = MonitoringAlert(
                alert_id=f"latency_{tunnel_id}_{int(datetime.now().timestamp())}",
                alert_type="latency_exceeded",
                severity="medium",
                message=f"Latency {metrics.average_latency_ms:.1f}ms exceeds threshold {self.config.latency_threshold_ms}ms",
                tunnel_id=tunnel_id,
                metric_name="average_latency_ms",
                metric_value=metrics.average_latency_ms,
                threshold_value=self.config.latency_threshold_ms
            )
            alerts_to_create.append(alert)

        # Check connection threshold
        if metrics.active_connections > self.config.connection_threshold:
            alert = MonitoringAlert(
                alert_id=f"connections_{tunnel_id}_{int(datetime.now().timestamp())}",
                alert_type="connection_limit_exceeded",
                severity="high",
                message=f"Active connections {metrics.active_connections} exceeds threshold {self.config.connection_threshold}",
                tunnel_id=tunnel_id,
                metric_name="active_connections",
                metric_value=float(metrics.active_connections),
                threshold_value=float(self.config.connection_threshold)
            )
            alerts_to_create.append(alert)

        # Process alerts
        for alert in alerts_to_create:
            self.alerts.append(alert)
            logger.warning(f"Alert created: {alert.message}")

            # Notify callbacks
            for callback in self._alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")

class StructuredLogger:
    """Structured logging system with Pydantic models"""

    def __init__(self, config: MonitoringConfig):
        self.config = config
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Setup logging configuration"""
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.logging.level.value.upper()))

        # Clear existing handlers
        root_logger.handlers.clear()

        # Setup console handler
        if self.config.logging.enable_console_logging:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(
                getattr(logging, self.config.logging.console_level.value.upper())
            )

            if self.config.logging.format == "json":
                console_handler.setFormatter(JSONFormatter())
            else:
                console_handler.setFormatter(
                    logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    )
                )
            root_logger.addHandler(console_handler)

        # Setup file handler
        if self.config.logging.enable_file_logging and self.config.logging.log_file:
            from logging.handlers import RotatingFileHandler

            log_path = Path(self.config.logging.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                self.config.logging.log_file,
                maxBytes=self.config.logging.max_file_size_mb * 1024 * 1024,
                backupCount=self.config.logging.backup_count
            )
            file_handler.setLevel(getattr(logging, self.config.logging.level.value.upper()))

            if self.config.logging.format == "json":
                file_handler.setFormatter(JSONFormatter())
            else:
                file_handler.setFormatter(
                    logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    )
                )
            root_logger.addHandler(file_handler)

    def log_event(self, event: LogEvent) -> None:
        """Log a structured event"""
        logger = logging.getLogger(event.logger_name)
        level = getattr(logging, event.level.value.upper())

        # Create extra context for the log record
        extra = {
            'tunnel_id': event.tunnel_id,
            'client_id': event.client_id,
            'event_type': event.event_type.value if event.event_type else None,
            'extra_data': event.extra_data
        }

        # Add technical details if available
        if event.module:
            extra['module'] = event.module
        if event.function:
            extra['function'] = event.function
        if event.line_number:
            extra['line_number'] = event.line_number

        logger.log(level, event.message, extra=extra)

    def log_tunnel_event(
        self,
        level: LogLevel,
        message: str,
        tunnel_id: str,
        event_type: Optional[EventType] = None,
        **extra_data
    ) -> None:
        """Convenience method for logging tunnel events"""
        event = LogEvent(
            level=level,
            logger_name="frp_wrapper.monitoring",
            message=message,
            tunnel_id=tunnel_id,
            event_type=event_type,
            extra_data=extra_data
        )
        self.log_event(event)

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname.lower(),
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process': record.process,
            'thread': record.thread,
            'thread_name': record.threadName
        }

        # Add extra fields if present
        for key, value in record.__dict__.items():
            if key not in log_data and not key.startswith('_'):
                if key in ['tunnel_id', 'client_id', 'event_type', 'extra_data']:
                    log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)

class MonitoringSystem:
    """Complete monitoring system combining all components"""

    def __init__(self, config: Optional[MonitoringConfig] = None):
        self.config = config or MonitoringConfig()
        self.metrics_collector = MetricsCollector(self.config)
        self.logger = StructuredLogger(self.config)
        self._event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)

    def start(self) -> None:
        """Start the monitoring system"""
        self.metrics_collector.start_collection()
        self.logger.log_tunnel_event(
            LogLevel.INFO,
            "Monitoring system started",
            tunnel_id="system",
            event_type=EventType.CLIENT_CONNECTED
        )

    def stop(self) -> None:
        """Stop the monitoring system"""
        self.metrics_collector.stop_collection()
        self.logger.log_tunnel_event(
            LogLevel.INFO,
            "Monitoring system stopped",
            tunnel_id="system",
            event_type=EventType.CLIENT_DISCONNECTED
        )

    def register_tunnel(self, tunnel_id: str) -> None:
        """Register a tunnel for monitoring"""
        self.metrics_collector.register_tunnel(tunnel_id)
        self.logger.log_tunnel_event(
            LogLevel.INFO,
            f"Tunnel registered for monitoring: {tunnel_id}",
            tunnel_id=tunnel_id,
            event_type=EventType.TUNNEL_CREATED
        )

    def unregister_tunnel(self, tunnel_id: str) -> None:
        """Unregister a tunnel from monitoring"""
        self.metrics_collector.unregister_tunnel(tunnel_id)
        self.logger.log_tunnel_event(
            LogLevel.INFO,
            f"Tunnel unregistered from monitoring: {tunnel_id}",
            tunnel_id=tunnel_id,
            event_type=EventType.TUNNEL_CLOSED
        )

    def on_event(self, event_type: EventType, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register event handler"""
        self._event_handlers[event_type].append(handler)

    def emit_event(self, event_type: EventType, data: Dict[str, Any]) -> None:
        """Emit event to all registered handlers"""
        tunnel_id = data.get('tunnel_id', 'unknown')

        # Log the event
        self.logger.log_tunnel_event(
            LogLevel.INFO,
            f"Event emitted: {event_type.value}",
            tunnel_id=tunnel_id,
            event_type=event_type,
            event_data=data
        )

        # Call handlers
        for handler in self._event_handlers[event_type]:
            try:
                handler(data)
            except Exception as e:
                self.logger.log_tunnel_event(
                    LogLevel.ERROR,
                    f"Error in event handler: {e}",
                    tunnel_id=tunnel_id,
                    error=str(e)
                )
```

## Implementation Timeline (TDD + Pydantic)

### Day 1: Unified Monitoring Models & Configuration
1. **Write client monitoring tests**: TunnelMetrics, LogEvent validation
2. **Write server monitoring tests**: ServerMetrics, resource usage validation
3. **Implement Pydantic models**: Client and server monitoring data models
4. **Write configuration tests**: MonitoringConfig with client+server thresholds
5. **Implement configuration**: Type-safe unified monitoring system configuration

### Day 2: Metrics Collection & Logging
1. **Write client metrics collector tests**: Tunnel collection, thresholds, alerts
2. **Write server metrics collector tests**: Server resource monitoring, client tracking
3. **Implement MetricsCollector**: Real-time client and server metrics collection
4. **Write structured logging tests**: Unified JSON formatting, log levels, file rotation
5. **Implement StructuredLogger**: Pydantic-based structured logging for all components

### Day 3: Integration & Unified Dashboard
1. **Write unified monitoring system tests**: Client-server integrated monitoring
2. **Implement MonitoringSystem**: Coordinated monitoring for both client and server
3. **Write unified dashboard tests**: Combined client-server web interface
4. **Implement unified dashboard**: Real-time visibility into entire FRP system
5. **Integration testing**: End-to-end monitoring scenarios with real FRP client and server

## File Structure
```
src/frp_wrapper/
├── __init__.py
├── monitoring/
│   ├── __init__.py
│   ├── models.py          # Pydantic monitoring models
│   ├── system.py          # Complete monitoring system
│   ├── dashboard.py       # Optional web dashboard
│   └── exporters.py       # Metrics exporters (Prometheus, etc.)

tests/
├── __init__.py
├── test_monitoring_models.py    # Pydantic model tests
├── test_metrics_collector.py    # Metrics collection tests
├── test_structured_logging.py   # Logging system tests
└── test_monitoring_integration.py  # Integration tests
```

## Success Criteria
- [ ] 100% test coverage for unified monitoring system
- [ ] All Pydantic validation scenarios tested (client + server)
- [ ] Real-time client tunnel metrics collection working
- [ ] Real-time server resource metrics collection working
- [ ] Unified structured logging with JSON output
- [ ] Client and server alert threshold systems functional
- [ ] Thread-safe metrics handling for both components
- [ ] Integration with FRP tunnels and server tested
- [ ] Unified dashboard showing complete system status
- [ ] End-to-end monitoring scenarios validated

## Key Pydantic Benefits for Unified Monitoring
1. **Comprehensive Validation**: Client and server metrics with full validation
2. **Type Safety**: Complete IDE support for all monitoring data structures
3. **Unified Serialization**: Consistent JSON export for integrated dashboards
4. **Computed Fields**: Automatic calculation of derived metrics for both client and server
5. **Immutability**: Safe concurrent access to all metrics data
6. **Self-Documentation**: Auto-documenting monitoring configuration for entire system
7. **Consistent Patterns**: Identical monitoring patterns for client and server components

This approach provides production-ready unified monitoring with comprehensive validation, excellent performance, and robust error handling suitable for enterprise deployments, offering complete visibility into the entire FRP system from a single interface.
