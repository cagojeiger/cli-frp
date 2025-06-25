# Checkpoint 12: K8s 기반 분산 서비스 프록시 시스템

## Status: 🚧 In Progress
Currently working on K8s distributed system architecture.
See docs/research/ and docs/k8s/ for detailed technical research.

## Overview

Kubernetes 환경에서 운영되는 범용 분산 서비스 프록시 시스템을 구축합니다. FRP의 기본 터널링과 로드 밸런싱 기능을 활용하면서, K8s 네이티브 패턴으로 확장하여 다양한 서비스를 지원합니다.

**핵심 원칙**:
- FRP는 순수 터널링 인프라로만 활용
- K8s가 오케스트레이션과 서비스 관리 담당
- Python Wrapper는 두 시스템을 연결하는 브릿지 역할
- Ollama는 하나의 사용 사례, 범용적 설계 추구

## Architecture

### 1. 계층별 역할 분담

```
┌─────────────────────────────────────────────────────────┐
│                   사용자 / 클라이언트                      │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                  K8s Ingress / Service                   │
│                  (외부 트래픽 진입점)                      │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                    FRP Server (frps)                     │
│                   K8s Deployment/Pod                     │
│              - TCP/HTTP 프록시                            │
│              - 그룹 기반 로드 밸런싱                        │
│              - mTLS 터널링                               │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                 FRP Clients (frpc)                       │
│                K8s DaemonSet/Pods                        │
│         - 각 노드/서비스별 frpc 인스턴스                    │
│         - 동일 그룹으로 로드 밸런싱 참여                     │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                   백엔드 서비스들                          │
│      - Ollama (LLM)                                     │
│      - HTTP APIs                                        │
│      - 데이터베이스                                       │
│      - 기타 TCP/UDP 서비스                               │
└─────────────────────────────────────────────────────────┘
```

### 2. FRP 기본 기능 활용 범위

**FRP가 제공하는 것** (그대로 활용):
- ✅ TCP/UDP/HTTP/HTTPS 프록시
- ✅ 그룹 기반 TCP 로드 밸런싱
- ✅ mTLS 암호화 터널
- ✅ 헬스체크와 자동 장애 감지
- ✅ 연결 풀링과 멀티플렉싱
- ✅ 대역폭 제한
- ✅ Prometheus 메트릭

**추가 구현이 필요한 것**:
- ❌ 서비스 자동 발견 → K8s Service Discovery 활용
- ❌ 동적 설정 관리 → K8s ConfigMap/Operator
- ❌ 고급 로드 밸런싱 → 별도 프록시 계층 추가
- ❌ API 게이트웨이 기능 → Istio/Kong 등 활용

### 3. K8s 리소스 매핑

```yaml
# FRP Server (frps)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frp-server
spec:
  replicas: 1  # HA를 위해 추후 확장 가능
  template:
    spec:
      containers:
      - name: frps
        image: frp-wrapper:server
        volumeMounts:
        - name: config
          mountPath: /etc/frp
        - name: certs
          mountPath: /etc/frp/certs
---
# FRP Clients (frpc) - DaemonSet으로 각 노드에 배포
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: frp-client
spec:
  template:
    spec:
      containers:
      - name: frpc
        image: frp-wrapper:client
        env:
        - name: FRP_GROUP
          value: "{{ service_group }}"
        - name: LOCAL_SERVICE_PORT
          value: "{{ local_port }}"
---
# 서비스별 ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: frp-service-config
data:
  ollama.yaml: |
    service_type: http
    local_port: 11434
    group: ollama-pool
    health_check:
      type: http
      url: /api/health
```

### 4. Python Wrapper의 역할 확장

```python
# src/frp_wrapper/k8s/operator.py
class FRPServiceOperator:
    """K8s Operator 패턴으로 FRP 서비스 관리"""

    def __init__(self, k8s_client):
        self.k8s = k8s_client
        self.frp_manager = FRPManager()

    def reconcile(self, service_spec: ServiceSpec):
        """선언적 상태 관리"""
        # 1. 현재 상태 확인
        current = self.get_current_state(service_spec.name)

        # 2. 원하는 상태와 비교
        desired = self.compute_desired_state(service_spec)

        # 3. 차이가 있으면 조정
        if current != desired:
            self.apply_changes(current, desired)

    def create_frp_service(self, spec: ServiceSpec):
        """새 FRP 서비스 생성"""
        # ConfigMap 생성
        config = self.generate_frp_config(spec)
        self.k8s.create_configmap(config)

        # Secret 생성 (mTLS 인증서)
        certs = self.generate_mtls_certs(spec)
        self.k8s.create_secret(certs)

        # DaemonSet/Deployment 생성
        self.k8s.create_workload(spec)
```

## Use Cases

### 1. Ollama 분산 LLM 서빙

```yaml
# ollama-service.yaml
apiVersion: frp.io/v1
kind: DistributedService
metadata:
  name: ollama-cluster
spec:
  serviceType: http
  backends:
    discovery: auto  # K8s 서비스 디스커버리 사용
    selector:
      app: ollama
  loadBalancing:
    strategy: round-robin
    healthCheck:
      path: /api/health
      interval: 10s
  security:
    mtls:
      enabled: true
      autoGenerate: true
  expose:
    type: http
    domain: llm.example.com
    path: /v1
```

실제 동작:
1. 여러 노드의 Ollama 인스턴스가 frpc로 연결
2. 모두 `ollama-pool` 그룹에 참여
3. frps가 요청을 자동 분산
4. K8s가 헬스체크와 재시작 관리

### 2. 일반 HTTP API 서비스

```yaml
apiVersion: frp.io/v1
kind: DistributedService
metadata:
  name: api-gateway
spec:
  serviceType: http
  backends:
    - name: auth-service
      port: 8080
      weight: 30
    - name: user-service
      port: 8081
      weight: 70
  routing:
    - path: /auth/*
      backend: auth-service
    - path: /users/*
      backend: user-service
```

### 3. 데이터베이스 프록시

```yaml
apiVersion: frp.io/v1
kind: DistributedService
metadata:
  name: postgres-proxy
spec:
  serviceType: tcp
  port: 5432
  backends:
    - primary: true
      host: postgres-primary
    - replica: true
      host: postgres-replica-1
    - replica: true
      host: postgres-replica-2
  loadBalancing:
    readWriteSplit: true  # 읽기는 replica로 분산
```

## Implementation Phases

### Phase 1: 기본 K8s 통합 (Week 1-2)

**목표**: FRP를 K8s에서 실행하는 기본 구조

1. **Docker 이미지 생성**
   ```dockerfile
   # Dockerfile.server
   FROM python:3.11-slim
   RUN apt-get update && apt-get install -y wget
   RUN wget https://github.com/fatedier/frp/releases/download/v0.51.0/frp_0.51.0_linux_amd64.tar.gz
   COPY frp-wrapper /app
   CMD ["python", "-m", "frp_wrapper.k8s.server"]
   ```

2. **기본 K8s 매니페스트**
   - frps Deployment + Service
   - frpc DaemonSet
   - ConfigMap으로 설정 관리

3. **Python 래퍼 확장**
   ```python
   # src/frp_wrapper/k8s/__init__.py
   class K8sConfigGenerator:
       """K8s 환경에 맞는 FRP 설정 생성"""

       def from_service_spec(self, spec: dict) -> str:
           """K8s 서비스 스펙을 FRP 설정으로 변환"""
   ```

### Phase 2: CRD와 Operator 패턴 (Week 3-4)

**목표**: 선언적 API로 FRP 서비스 관리

1. **Custom Resource Definition**
   ```yaml
   apiVersion: apiextensions.k8s.io/v1
   kind: CustomResourceDefinition
   metadata:
     name: distributedservices.frp.io
   spec:
     group: frp.io
     versions:
     - name: v1
       served: true
       storage: true
       schema:
         openAPIV3Schema:
           type: object
           properties:
             spec:
               type: object
               properties:
                 serviceType:
                   type: string
                   enum: [http, tcp, udp]
                 backends:
                   type: array
                 loadBalancing:
                   type: object
   ```

2. **Operator 구현**
   ```python
   # src/frp_wrapper/k8s/operator.py
   @kopf.on.create('frp.io', 'v1', 'distributedservices')
   def create_fn(spec, name, namespace, **kwargs):
       """새 DistributedService 생성시 호출"""
       # FRP 설정 생성
       # K8s 리소스 생성
       # 상태 업데이트
   ```

### Phase 3: 서비스 디스커버리와 자동화 (Week 5-6)

**목표**: 백엔드 자동 발견과 동적 업데이트

1. **K8s Watch API 활용**
   ```python
   class ServiceDiscovery:
       """K8s 서비스 변경 감지 및 FRP 설정 업데이트"""

       def watch_services(self, selector: dict):
           """레이블 셀렉터로 서비스 감시"""

       def on_service_added(self, service):
           """새 백엔드 추가시 FRP 그룹에 등록"""

       def on_service_removed(self, service):
           """백엔드 제거시 FRP 그룹에서 제외"""
   ```

2. **동적 설정 업데이트**
   - FRP API 활용한 런타임 설정 변경
   - ConfigMap 변경시 자동 리로드

### Phase 4: 보안과 모니터링 (Week 7-8)

**목표**: Production-ready 보안과 관측성

1. **mTLS 자동화**
   ```python
   class CertificateManager:
       """mTLS 인증서 자동 관리"""

       def generate_ca(self):
           """Root CA 생성"""

       def issue_client_cert(self, service_name: str):
           """서비스별 클라이언트 인증서 발급"""

       def rotate_certificates(self):
           """인증서 자동 갱신"""
   ```

2. **통합 모니터링**
   - Prometheus ServiceMonitor 자동 생성
   - Grafana 대시보드 템플릿
   - 알림 규칙 설정

## Technical Implementation Details

### 1. FRP 그룹 로드 밸런싱 활용

```ini
# frpc 설정 (각 백엔드)
[[proxies]]
name = "ollama-{{ pod_name }}"
type = tcp
localPort = 11434
remotePort = 80
group = "ollama-pool"
groupKey = "{{ shared_secret }}"
healthCheck.type = "http"
healthCheck.url = "/api/health"
```

모든 Ollama 인스턴스가 동일한 그룹에 참여하여 자동 로드 밸런싱

### 2. K8s Service Mesh 통합 고려사항

**Istio와 함께 사용시**:
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: frp-routing
spec:
  http:
  - match:
    - headers:
        x-service-type:
          exact: ollama
    route:
    - destination:
        host: frp-server
        port:
          number: 80
```

### 3. 성능 최적화

```python
class PerformanceTuner:
    """K8s 환경에 맞는 FRP 성능 튜닝"""

    def calculate_pool_count(self, node_resources: dict) -> int:
        """노드 리소스에 따른 최적 연결 풀 크기"""
        cpu_cores = node_resources['cpu']
        memory_gb = node_resources['memory'] / 1024

        # 경험적 공식
        return min(
            cpu_cores * 2,  # CPU 코어당 2개
            int(memory_gb / 0.5),  # 0.5GB당 1개
            20  # 최대 제한
        )

    def optimize_frp_config(self, service_type: str) -> dict:
        """서비스 타입별 최적화 설정"""
        if service_type == "ollama":
            return {
                "transport.tcpMux": True,
                "transport.poolCount": 5,
                "transport.dialServerTimeout": 30,
                # LLM은 긴 요청이므로 타임아웃 증가
                "transport.heartbeatTimeout": 180
            }
```

### 4. 장애 복구와 고가용성

```python
class FailoverManager:
    """장애 감지 및 자동 복구"""

    def setup_health_monitoring(self):
        """다층 헬스체크 설정"""
        # 1. FRP 자체 헬스체크
        # 2. K8s Liveness/Readiness Probe
        # 3. 애플리케이션 레벨 헬스체크

    def handle_node_failure(self, failed_node: str):
        """노드 장애시 트래픽 재분배"""
        # 1. 실패한 노드의 frpc 제거
        # 2. 다른 노드로 트래픽 재분배
        # 3. 새 노드 추가시 자동 참여
```

## 모니터링과 관측성

### 1. 메트릭 수집

```yaml
# ServiceMonitor for Prometheus
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: frp-metrics
spec:
  selector:
    matchLabels:
      app: frp-server
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

### 2. 주요 모니터링 지표

- **연결 수준**: 활성 연결 수, 연결 풀 사용률
- **성능**: 요청 지연시간, 처리량, 에러율
- **리소스**: CPU/메모리 사용률, 네트워크 대역폭
- **서비스별**: Ollama 모델 로딩 시간, 추론 지연시간

### 3. 대시보드 예시

```python
# Grafana 대시보드 자동 생성
class DashboardGenerator:
    def create_service_dashboard(self, service_name: str) -> dict:
        """서비스별 커스텀 대시보드 생성"""
        return {
            "panels": [
                self.request_rate_panel(service_name),
                self.latency_panel(service_name),
                self.error_rate_panel(service_name),
                self.backend_health_panel(service_name)
            ]
        }
```

## Security Considerations

### 1. Zero Trust 네트워크 모델

- 모든 연결에 mTLS 적용
- 서비스별 인증서와 세밀한 권한 관리
- NetworkPolicy로 트래픽 제어

### 2. Secret 관리

```python
class SecretManager:
    """K8s Secret과 외부 비밀 관리 시스템 통합"""

    def integrate_with_vault(self):
        """HashiCorp Vault 통합"""

    def rotate_frp_tokens(self):
        """FRP 인증 토큰 주기적 갱신"""
```

## Production Readiness Checklist

- [ ] 고가용성 frps 구성 (멀티 레플리카)
- [ ] 자동 장애 복구 메커니즘
- [ ] 포괄적인 모니터링과 알림
- [ ] 보안 스캔과 취약점 관리
- [ ] 백업과 복구 전략
- [ ] 성능 테스트와 용량 계획
- [ ] 운영 문서와 Runbook

## Next Steps

1. **Proof of Concept**: 단일 서비스(Ollama)로 기본 구조 검증
2. **프로토타입**: K8s Operator 기본 구현
3. **파일럿**: 실제 워크로드로 테스트
4. **프로덕션**: 단계적 롤아웃과 모니터링

이 설계를 통해 FRP의 검증된 터널링 기능을 활용하면서도 K8s의 강력한 오케스트레이션 능력을 결합한 엔터프라이즈급 분산 서비스 프록시 시스템을 구축할 수 있습니다.
