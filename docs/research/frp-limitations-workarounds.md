# FRP 제약사항과 우회 방안 연구

## 개요

FRP(Fast Reverse Proxy)는 강력한 터널링 솔루션이지만, K8s 환경에서 분산 서비스 프록시로 활용하기 위해서는 몇 가지 중요한 제약사항을 이해하고 우회 방안을 마련해야 합니다. 이 문서는 실제 구현 시 직면할 수 있는 기술적 한계와 해결책을 체계적으로 정리합니다.

## 1. 로드 밸런싱 제약사항

### 문제 정의

FRP의 그룹 로드 밸런싱은 다음과 같은 제약이 있습니다:

1. **TCP 전용**: HTTP/HTTPS 타입에서는 그룹 로드 밸런싱 미지원
2. **알고리즘 제한**: 랜덤 분산만 지원 (라운드로빈, 가중치 기반 등 미지원)
3. **동적 가중치 조정 불가**: 백엔드 성능에 따른 동적 조정 불가능

### 현재 동작 방식

```ini
# frpc.ini - TCP 그룹 로드 밸런싱
[service1]
type = tcp
local_port = 8080
remote_port = 80
group = web-pool
group_key = secret123

[service2]
type = tcp
local_port = 8081
remote_port = 80
group = web-pool
group_key = secret123
```

### 우회 방안

#### 방안 1: TCP 프록시로 HTTP 서비스 래핑

```python
# HTTP 서비스를 TCP로 노출하는 래퍼
class HTTPOverTCPProxy:
    """HTTP 서비스를 FRP TCP 그룹으로 노출"""

    def __init__(self, http_port: int, tcp_port: int):
        self.http_port = http_port
        self.tcp_port = tcp_port

    def start(self):
        # TCP 포트로 들어온 요청을 HTTP 포트로 전달
        # 이를 통해 HTTP 서비스도 그룹 로드 밸런싱 가능
```

#### 방안 2: 상위 레이어 로드 밸런서 추가

```yaml
# K8s Service로 추가 로드 밸런싱
apiVersion: v1
kind: Service
metadata:
  name: frp-lb
spec:
  type: LoadBalancer
  sessionAffinity: ClientIP  # 세션 유지
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800
  selector:
    app: frp-client
```

#### 방안 3: 커스텀 로드 밸런싱 구현

```python
class AdvancedLoadBalancer:
    """FRP 상위에서 고급 로드 밸런싱 제공"""

    def __init__(self, backends: List[FRPBackend]):
        self.backends = backends
        self.health_checker = HealthChecker()

    def select_backend(self, request: Request) -> FRPBackend:
        """가중치 기반, 최소 연결, 응답 시간 기반 등 구현"""
        healthy_backends = self.health_checker.get_healthy(self.backends)
        return self.weighted_round_robin(healthy_backends)
```

## 2. 동적 설정 관리 제약사항

### 문제 정의

1. **설정 리로드 필요**: 백엔드 추가/제거 시 설정 파일 재작성 필요
2. **API 제한**: FRP API로는 제한적인 동적 관리만 가능
3. **상태 동기화**: 여러 frpc 인스턴스 간 설정 동기화 복잡

### 우회 방안

#### 방안 1: 설정 자동 생성 및 리로드

```python
class DynamicConfigManager:
    """K8s 이벤트 기반 FRP 설정 자동 관리"""

    def __init__(self, k8s_client, frp_manager):
        self.k8s = k8s_client
        self.frp = frp_manager
        self.watch_services()

    def on_service_change(self, event):
        """K8s 서비스 변경 시 FRP 설정 재생성"""
        new_config = self.generate_frp_config()
        self.frp.update_config(new_config)
        self.frp.graceful_reload()  # 무중단 리로드
```

#### 방안 2: FRP API 확장 활용

```python
class FRPAPIClient:
    """FRP Admin API를 활용한 동적 관리"""

    def __init__(self, api_url: str, auth_token: str):
        self.api_url = api_url
        self.auth_token = auth_token

    def add_proxy(self, proxy_config: dict):
        """런타임에 프록시 추가"""
        # POST /api/proxy

    def remove_proxy(self, proxy_name: str):
        """런타임에 프록시 제거"""
        # DELETE /api/proxy/{name}
```

## 3. 서비스 디스커버리 부재

### 문제 정의

1. **수동 등록**: 각 백엔드를 수동으로 설정해야 함
2. **동적 발견 불가**: 새로운 서비스 자동 발견 메커니즘 없음
3. **헬스체크 통합**: K8s 헬스체크와 FRP 헬스체크 분리

### 우회 방안

#### 방안 1: K8s 서비스 디스커버리 브릿지

```python
class K8sServiceDiscoveryBridge:
    """K8s 서비스를 FRP 백엔드로 자동 등록"""

    def __init__(self):
        self.k8s = client.CoreV1Api()
        self.discovered_services = {}

    def watch_services(self, label_selector: str):
        """레이블 기반 서비스 감시"""
        w = watch.Watch()
        for event in w.stream(
            self.k8s.list_service_for_all_namespaces,
            label_selector=label_selector
        ):
            self.handle_service_event(event)

    def handle_service_event(self, event):
        """서비스 이벤트를 FRP 설정으로 변환"""
        if event['type'] == 'ADDED':
            self.register_to_frp(event['object'])
        elif event['type'] == 'DELETED':
            self.unregister_from_frp(event['object'])
```

#### 방안 2: Headless Service 활용

```yaml
# 개별 Pod IP를 직접 FRP 백엔드로 등록
apiVersion: v1
kind: Service
metadata:
  name: backend-headless
spec:
  clusterIP: None  # Headless service
  selector:
    app: backend
  ports:
  - port: 80
```

## 4. mTLS 구현 복잡성

### 문제 정의

1. **인증서 관리**: 수백 개 클라이언트의 인증서 발급/갱신
2. **자동 회전**: 인증서 만료 전 자동 갱신 필요
3. **무중단 갱신**: 서비스 중단 없이 인증서 교체

### 우회 방안

#### 방안 1: cert-manager 통합

```yaml
# cert-manager로 자동 인증서 관리
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: frp-client-cert
spec:
  secretName: frp-client-tls
  issuerRef:
    name: frp-ca-issuer
    kind: ClusterIssuer
  commonName: frpc-{{ .PodName }}
  duration: 720h  # 30일
  renewBefore: 168h  # 7일 전 갱신
```

#### 방안 2: 자체 CA 관리 시스템

```python
class FRPCertificateManager:
    """FRP 전용 인증서 생명주기 관리"""

    def __init__(self):
        self.ca = self.load_or_create_ca()
        self.cert_store = CertificateStore()

    def issue_client_cert(self, client_id: str) -> Tuple[str, str]:
        """클라이언트 인증서 발급"""
        cert, key = self.ca.issue_certificate(
            cn=f"frpc-{client_id}",
            validity_days=30
        )
        self.cert_store.save(client_id, cert, key)
        return cert, key

    def auto_renew(self):
        """만료 임박 인증서 자동 갱신"""
        for cert in self.cert_store.get_expiring(days=7):
            new_cert, new_key = self.issue_client_cert(cert.client_id)
            self.rolling_update(cert.client_id, new_cert, new_key)
```

## 5. 모니터링과 메트릭 수집

### 문제 정의

1. **제한적 메트릭**: FRP가 제공하는 메트릭 종류 제한
2. **통합 어려움**: Prometheus와의 네이티브 통합 부재
3. **분산 추적**: 요청 추적을 위한 트레이싱 미지원

### 우회 방안

#### 방안 1: 커스텀 메트릭 익스포터

```python
class FRPMetricsExporter:
    """FRP 메트릭을 Prometheus 형식으로 변환"""

    def __init__(self, frp_api_url: str):
        self.frp_api = frp_api_url
        self.registry = CollectorRegistry()
        self.setup_metrics()

    def collect_metrics(self):
        """FRP API에서 메트릭 수집"""
        stats = self.get_frp_stats()

        # Prometheus 메트릭으로 변환
        self.active_connections.set(stats['connections'])
        self.bandwidth_bytes.inc(stats['bandwidth'])
        self.proxy_latency.observe(stats['latency'])
```

#### 방안 2: 사이드카 패턴으로 메트릭 수집

```yaml
# FRP Pod에 메트릭 수집 사이드카 추가
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: frpc
    image: frp-wrapper:client
  - name: metrics-collector
    image: frp-metrics-exporter:latest
    ports:
    - containerPort: 9090  # Prometheus metrics
```

## 6. 네트워크 정책과 보안

### 문제 정의

1. **세밀한 제어 부족**: FRP 레벨에서의 네트워크 정책 제한
2. **트래픽 검사**: 터널링된 트래픽의 내용 검사 어려움
3. **감사 로그**: 상세한 접근 로그 부족

### 우회 방안

#### 방안 1: K8s NetworkPolicy 활용

```yaml
# FRP 트래픽을 K8s NetworkPolicy로 제어
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frp-traffic-control
spec:
  podSelector:
    matchLabels:
      app: frp-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          frp-client: "true"
    ports:
    - port: 7000  # FRP control port
```

#### 방안 2: 프록시 체인으로 트래픽 검사

```python
class SecurityProxy:
    """FRP 앞단에서 트래픽 검사 및 필터링"""

    def __init__(self):
        self.waf = WebApplicationFirewall()
        self.rate_limiter = RateLimiter()

    def process_request(self, request):
        # WAF 검사
        if self.waf.is_malicious(request):
            return self.block_request(request)

        # Rate limiting
        if not self.rate_limiter.allow(request.client_ip):
            return self.rate_limit_response()

        # FRP로 전달
        return self.forward_to_frp(request)
```

## 7. 고가용성(HA) 구성

### 문제 정의

1. **단일 장애점**: frps 서버가 단일 장애점이 될 수 있음
2. **상태 동기화**: 여러 frps 인스턴스 간 상태 공유 어려움
3. **페일오버**: 자동 페일오버 메커니즘 부재

### 우회 방안

#### 방안 1: Active-Passive HA 구성

```python
class FRPHighAvailability:
    """Active-Passive 방식의 HA 구현"""

    def __init__(self):
        self.primary = FRPServer("primary")
        self.standby = FRPServer("standby")
        self.health_monitor = HealthMonitor()

    def monitor_and_failover(self):
        """주 서버 모니터링 및 자동 페일오버"""
        while True:
            if not self.health_monitor.is_healthy(self.primary):
                self.promote_standby()
                self.notify_clients()
```

#### 방안 2: 로드 밸런서를 통한 다중 frps

```yaml
# 여러 frps 인스턴스를 로드 밸런서로 분산
apiVersion: v1
kind: Service
metadata:
  name: frps-lb
spec:
  type: LoadBalancer
  selector:
    app: frps
  ports:
  - name: control
    port: 7000
  sessionAffinity: ClientIP  # 클라이언트 고정
```

## 구현 우선순위 권장사항

1. **즉시 구현 필요**
   - TCP 래핑을 통한 HTTP 로드 밸런싱
   - K8s 서비스 디스커버리 브릿지
   - 기본 메트릭 익스포터

2. **단기 구현 (1-2주)**
   - 동적 설정 관리자
   - cert-manager 통합
   - 기본 HA 구성

3. **중기 구현 (1개월)**
   - 고급 로드 밸런싱 알고리즘
   - 보안 프록시 체인
   - 분산 추적 통합

4. **장기 구현**
   - 커스텀 FRP 포크 개발
   - 네이티브 K8s 통합 기능 추가

## 결론

FRP의 제약사항들은 대부분 상위 레이어에서의 추가 구현으로 해결 가능합니다. 핵심은 FRP를 순수 터널링 레이어로 활용하고, K8s와 Python 래퍼에서 부족한 기능을 보완하는 것입니다. 이러한 접근을 통해 FRP의 안정성과 성능을 유지하면서도 엔터프라이즈급 기능을 제공할 수 있습니다.
