# DistributedService CRD 설계 문서

## 개요

DistributedService는 FRP 기반 분산 서비스 프록시를 Kubernetes에서 선언적으로 관리하기 위한 Custom Resource Definition입니다. 이 문서는 CRD의 상세 설계, API 스펙, 그리고 실제 사용 예제를 제공합니다.

## 설계 원칙

1. **선언적 API**: 원하는 상태를 선언하면 Operator가 실제 상태를 맞춤
2. **유연성**: 다양한 서비스 타입과 설정 지원
3. **K8s 네이티브**: 기존 K8s 리소스와 자연스럽게 통합
4. **확장 가능성**: 향후 기능 추가를 위한 여유 있는 설계

## API 그룹과 버전

```yaml
apiVersion: frp.io/v1beta1
kind: DistributedService
```

- **그룹**: `frp.io`
- **버전**: `v1beta1` (베타, 하위 호환성 보장하지 않음)
- **종류**: `DistributedService`

## CRD 스키마 상세

### 전체 스키마 정의

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: distributedservices.frp.io
spec:
  group: frp.io
  names:
    plural: distributedservices
    singular: distributedservice
    kind: DistributedService
    shortNames:
    - ds
    - dsvc
  scope: Namespaced
  versions:
  - name: v1beta1
    served: true
    storage: true
    additionalPrinterColumns:
    - name: Type
      type: string
      jsonPath: .spec.serviceType
    - name: Backends
      type: integer
      jsonPath: .status.activeBackends
    - name: State
      type: string
      jsonPath: .status.state
    - name: Age
      type: date
      jsonPath: .metadata.creationTimestamp
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            required: ["serviceType", "backends"]
            properties:
              serviceType:
                type: string
                enum: ["http", "tcp", "udp", "grpc"]
                description: "프록시할 서비스의 프로토콜 타입"

              backends:
                type: object
                oneOf:
                - required: ["discovery"]
                - required: ["endpoints"]
                properties:
                  discovery:
                    type: object
                    properties:
                      mode:
                        type: string
                        enum: ["auto", "selector", "dns"]
                        default: "auto"
                      selector:
                        type: object
                        description: "K8s 레이블 셀렉터"
                      namespace:
                        type: string
                        description: "백엔드 검색 네임스페이스"
                      port:
                        type: integer
                        minimum: 1
                        maximum: 65535

                  endpoints:
                    type: array
                    description: "수동으로 지정된 백엔드 목록"
                    items:
                      type: object
                      required: ["host", "port"]
                      properties:
                        host:
                          type: string
                        port:
                          type: integer
                          minimum: 1
                          maximum: 65535
                        weight:
                          type: integer
                          minimum: 1
                          default: 1
                        metadata:
                          type: object
                          additionalProperties:
                            type: string

              expose:
                type: object
                description: "서비스 노출 설정"
                properties:
                  type:
                    type: string
                    enum: ["domain", "subdomain", "path", "port"]
                    default: "domain"
                  domain:
                    type: string
                    description: "커스텀 도메인"
                  subdomain:
                    type: string
                    description: "서브도메인 (base domain에 추가)"
                  path:
                    type: string
                    pattern: "^/[a-zA-Z0-9\\-_/]*$"
                    description: "URL 경로"
                  port:
                    type: integer
                    minimum: 1
                    maximum: 65535
                    description: "외부 노출 포트"

              loadBalancing:
                type: object
                properties:
                  algorithm:
                    type: string
                    enum: ["random", "round-robin", "least-conn", "weighted", "ip-hash"]
                    default: "random"
                  sessionAffinity:
                    type: object
                    properties:
                      enabled:
                        type: boolean
                        default: false
                      timeout:
                        type: string
                        pattern: "^[0-9]+(s|m|h)$"
                        default: "1h"
                      cookieName:
                        type: string
                        default: "frp-session"
                  healthCheck:
                    type: object
                    properties:
                      enabled:
                        type: boolean
                        default: true
                      type:
                        type: string
                        enum: ["tcp", "http", "https", "grpc"]
                        default: "tcp"
                      path:
                        type: string
                        default: "/health"
                      interval:
                        type: string
                        pattern: "^[0-9]+(s|m)$"
                        default: "10s"
                      timeout:
                        type: string
                        pattern: "^[0-9]+(s|m)$"
                        default: "3s"
                      successThreshold:
                        type: integer
                        minimum: 1
                        default: 1
                      failureThreshold:
                        type: integer
                        minimum: 1
                        default: 3

              security:
                type: object
                properties:
                  mtls:
                    type: object
                    properties:
                      enabled:
                        type: boolean
                        default: false
                      mode:
                        type: string
                        enum: ["auto", "manual", "external"]
                        default: "auto"
                        description: "인증서 관리 모드"
                      caSecret:
                        type: string
                        description: "CA 인증서가 포함된 Secret 이름"
                      certSecret:
                        type: string
                        description: "클라이언트 인증서가 포함된 Secret 이름"
                      certRotation:
                        type: object
                        properties:
                          enabled:
                            type: boolean
                            default: true
                          beforeExpiry:
                            type: string
                            pattern: "^[0-9]+(d|h)$"
                            default: "7d"

                  authentication:
                    type: object
                    properties:
                      type:
                        type: string
                        enum: ["none", "token", "oauth2", "apikey"]
                        default: "none"
                      tokenSecret:
                        type: string
                        description: "인증 토큰이 포함된 Secret"

                  authorization:
                    type: object
                    properties:
                      enabled:
                        type: boolean
                        default: false
                      rules:
                        type: array
                        items:
                          type: object
                          properties:
                            path:
                              type: string
                            methods:
                              type: array
                              items:
                                type: string
                                enum: ["GET", "POST", "PUT", "DELETE", "PATCH"]
                            roles:
                              type: array
                              items:
                                type: string

              advanced:
                type: object
                properties:
                  connectionPool:
                    type: object
                    properties:
                      enabled:
                        type: boolean
                        default: true
                      size:
                        type: integer
                        minimum: 1
                        maximum: 100
                        default: 5
                      idleTimeout:
                        type: string
                        pattern: "^[0-9]+(s|m)$"
                        default: "90s"

                  bandwidth:
                    type: object
                    properties:
                      limit:
                        type: string
                        pattern: "^[0-9]+(MB|KB|GB)$"
                        description: "대역폭 제한"
                      mode:
                        type: string
                        enum: ["client", "server"]
                        default: "client"

                  timeout:
                    type: object
                    properties:
                      dial:
                        type: string
                        pattern: "^[0-9]+(s|m)$"
                        default: "10s"
                      keepAlive:
                        type: string
                        pattern: "^[0-9]+(s|m)$"
                        default: "30s"

                  retry:
                    type: object
                    properties:
                      enabled:
                        type: boolean
                        default: true
                      maxAttempts:
                        type: integer
                        minimum: 1
                        default: 3
                      backoff:
                        type: string
                        enum: ["constant", "exponential", "linear"]
                        default: "exponential"

          status:
            type: object
            properties:
              state:
                type: string
                enum: ["Pending", "Provisioning", "Running", "Updating", "Degraded", "Failed", "Terminating"]

              conditions:
                type: array
                items:
                  type: object
                  required: ["type", "status"]
                  properties:
                    type:
                      type: string
                      enum: ["Ready", "BackendsAvailable", "ConfigurationValid", "CertificatesReady", "NetworkReady"]
                    status:
                      type: string
                      enum: ["True", "False", "Unknown"]
                    lastTransitionTime:
                      type: string
                      format: date-time
                    reason:
                      type: string
                    message:
                      type: string

              activeBackends:
                type: integer
                description: "현재 활성 백엔드 수"

              totalBackends:
                type: integer
                description: "전체 백엔드 수"

              endpoints:
                type: array
                description: "현재 활성 엔드포인트 목록"
                items:
                  type: object
                  properties:
                    address:
                      type: string
                    port:
                      type: integer
                    healthy:
                      type: boolean
                    lastCheck:
                      type: string
                      format: date-time

              externalEndpoint:
                type: string
                description: "외부 접근 엔드포인트"

              observedGeneration:
                type: integer
                description: "마지막으로 관찰된 generation"

              lastUpdateTime:
                type: string
                format: date-time

    subresources:
      status: {}
      scale:
        specReplicasPath: .spec.backends.replicas
        statusReplicasPath: .status.activeBackends
        labelSelectorPath: .status.selector
```

## 사용 예제

### 1. Ollama LLM 분산 서빙

```yaml
apiVersion: frp.io/v1beta1
kind: DistributedService
metadata:
  name: ollama-cluster
  namespace: ai-services
spec:
  serviceType: http

  backends:
    discovery:
      mode: selector
      selector:
        matchLabels:
          app: ollama
          tier: inference
      port: 11434

  expose:
    type: domain
    domain: llm.example.com
    path: /v1

  loadBalancing:
    algorithm: least-conn  # LLM은 연결 기반 부하 분산이 효율적
    healthCheck:
      enabled: true
      type: http
      path: /api/health
      interval: 30s
      timeout: 10s

  security:
    mtls:
      enabled: true
      mode: auto
    authentication:
      type: apikey
      tokenSecret: ollama-api-keys

  advanced:
    connectionPool:
      enabled: true
      size: 10  # LLM 요청은 오래 걸리므로 더 많은 연결 풀
    timeout:
      keepAlive: 300s  # 긴 추론 시간 고려
```

### 2. 마이크로서비스 간 통신

```yaml
apiVersion: frp.io/v1beta1
kind: DistributedService
metadata:
  name: user-service
  namespace: microservices
spec:
  serviceType: grpc

  backends:
    endpoints:
    - host: user-service-1.internal
      port: 9090
      weight: 2  # 더 강력한 서버에 더 많은 트래픽
    - host: user-service-2.internal
      port: 9090
      weight: 1

  expose:
    type: port
    port: 9090

  loadBalancing:
    algorithm: weighted
    sessionAffinity:
      enabled: true
      timeout: 5m

  security:
    mtls:
      enabled: true
      mode: manual
      caSecret: internal-ca
      certSecret: user-service-cert
```

### 3. 데이터베이스 프록시

```yaml
apiVersion: frp.io/v1beta1
kind: DistributedService
metadata:
  name: postgres-proxy
  namespace: databases
spec:
  serviceType: tcp

  backends:
    discovery:
      mode: dns
      namespace: databases
      port: 5432

  expose:
    type: port
    port: 5432

  loadBalancing:
    algorithm: ip-hash  # 동일 클라이언트는 동일 DB로
    healthCheck:
      enabled: true
      type: tcp
      interval: 5s
      failureThreshold: 2

  advanced:
    connectionPool:
      enabled: true
      size: 20
      idleTimeout: 300s
```

### 4. 웹 애플리케이션 with 경로 기반 라우팅

```yaml
apiVersion: frp.io/v1beta1
kind: DistributedService
metadata:
  name: webapp-frontend
  namespace: web
spec:
  serviceType: http

  backends:
    discovery:
      mode: auto
      port: 3000

  expose:
    type: path
    domain: app.example.com
    path: /frontend

  loadBalancing:
    algorithm: round-robin
    healthCheck:
      type: http
      path: /health

  security:
    authentication:
      type: oauth2
      tokenSecret: oauth2-config
    authorization:
      enabled: true
      rules:
      - path: /frontend/admin/*
        methods: ["GET", "POST", "PUT", "DELETE"]
        roles: ["admin"]
      - path: /frontend/api/*
        methods: ["GET"]
        roles: ["user", "admin"]
```

## 상태 전이 다이어그램

```
┌─────────┐
│ Pending │ ──────┐
└─────────┘       │
                  ▼
            ┌──────────────┐
            │ Provisioning │
            └──────────────┘
                  │
         ┌────────┴────────┐
         ▼                 ▼
    ┌─────────┐      ┌────────┐
    │ Running │ ◄────│ Failed │
    └─────────┘      └────────┘
         │                 ▲
         ▼                 │
    ┌──────────┐          │
    │ Updating │ ─────────┘
    └──────────┘
         │
         ▼
    ┌──────────┐
    │ Degraded │
    └──────────┘
         │
         ▼
   ┌─────────────┐
   │ Terminating │
   └─────────────┘
```

## Validation Webhooks

### 검증 규칙

```python
class DistributedServiceValidator:
    """CRD 검증 웹훅"""

    def validate_create(self, ds: DistributedService) -> ValidationResult:
        errors = []

        # 서비스 타입별 검증
        if ds.spec.service_type == "http":
            if not ds.spec.expose.domain and not ds.spec.expose.path:
                errors.append("HTTP service must have domain or path")

        # 백엔드 검증
        if ds.spec.backends.discovery and ds.spec.backends.endpoints:
            errors.append("Cannot use both discovery and manual endpoints")

        # 보안 검증
        if ds.spec.security.mtls.enabled:
            if ds.spec.security.mtls.mode == "manual":
                if not ds.spec.security.mtls.ca_secret:
                    errors.append("Manual mTLS requires caSecret")

        return ValidationResult(allowed=len(errors) == 0, errors=errors)
```

### Defaulting Webhook

```python
class DistributedServiceDefaulter:
    """기본값 설정 웹훅"""

    def set_defaults(self, ds: DistributedService):
        # 로드 밸런싱 기본값
        if not ds.spec.load_balancing.algorithm:
            ds.spec.load_balancing.algorithm = "random"

        # 헬스체크 기본값
        if ds.spec.load_balancing.health_check.enabled:
            if not ds.spec.load_balancing.health_check.type:
                ds.spec.load_balancing.health_check.type = (
                    "http" if ds.spec.service_type == "http" else "tcp"
                )

        # 보안 기본값
        if ds.spec.security.mtls.enabled and not ds.spec.security.mtls.mode:
            ds.spec.security.mtls.mode = "auto"
```

## 모니터링과 이벤트

### 이벤트 타입

```yaml
Events:
  Type     Reason                Age   From                    Message
  ----     ------                ----  ----                    -------
  Normal   ServiceCreated        5m    distributed-controller  DistributedService created
  Normal   BackendDiscovered     5m    distributed-controller  Discovered 3 backends
  Normal   CertificateIssued     4m    cert-manager           Issued certificate for mTLS
  Normal   ConfigurationApplied  4m    distributed-controller  FRP configuration applied
  Normal   HealthCheckPassed     3m    health-monitor         All backends healthy
  Warning  BackendUnhealthy      1m    health-monitor         Backend user-service-2 unhealthy
  Normal   BackendRemoved        30s   distributed-controller  Removed unhealthy backend
```

### 메트릭

```prometheus
# 서비스별 백엔드 수
frp_distributed_service_backends{namespace="ai-services",name="ollama-cluster",state="healthy"} 3
frp_distributed_service_backends{namespace="ai-services",name="ollama-cluster",state="unhealthy"} 0

# 요청 처리 메트릭
frp_distributed_service_requests_total{namespace="ai-services",name="ollama-cluster",backend="10.0.1.5:11434"} 1543
frp_distributed_service_request_duration_seconds{namespace="ai-services",name="ollama-cluster",quantile="0.99"} 2.5

# 연결 풀 사용률
frp_distributed_service_connection_pool_usage{namespace="ai-services",name="ollama-cluster"} 0.75
```

## 향후 확장 계획

### v1beta2 예정 기능

1. **고급 라우팅**
   - 헤더 기반 라우팅
   - 가중치 기반 카나리 배포
   - A/B 테스팅 지원

2. **관측성 향상**
   - 분산 추적 통합
   - 커스텀 메트릭 정의
   - SLO/SLA 추적

3. **보안 강화**
   - WAF 통합
   - DDoS 방어
   - 세밀한 접근 제어

4. **성능 최적화**
   - 캐싱 레이어
   - 압축 옵션
   - 연결 멀티플렉싱

## 마이그레이션 가이드

### 기존 FRP 설정에서 마이그레이션

```python
# 변환 스크립트 예제
def convert_frp_to_crd(frp_config: str) -> DistributedService:
    """기존 FRP 설정을 CRD로 변환"""
    config = parse_toml(frp_config)

    ds = DistributedService()
    ds.metadata.name = config.get('common', {}).get('name', 'migrated-service')

    # 프록시 설정 변환
    for proxy in config.get('proxies', []):
        if proxy['type'] == 'http':
            ds.spec.service_type = 'http'
            ds.spec.expose.domain = proxy.get('custom_domains', [])[0]
            ds.spec.expose.path = proxy.get('locations', ['/'])[0]

    return ds
```

## 결론

DistributedService CRD는 FRP의 강력한 터널링 기능을 K8s의 선언적 관리와 결합하여, 복잡한 분산 서비스 프록시를 쉽게 관리할 수 있게 합니다. 이 설계는 현재의 요구사항을 충족하면서도 향후 확장을 위한 유연성을 제공합니다.
