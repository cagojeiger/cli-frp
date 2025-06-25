# Kubernetes Operator 설계 패턴 연구

## 개요

Kubernetes Operator는 K8s의 확장 패턴으로, 도메인별 지식을 코드화하여 복잡한 애플리케이션을 자동으로 관리합니다. FRP 분산 서비스 프록시 시스템을 위한 Operator를 설계하기 위해 다양한 패턴을 비교 분석하고 최적의 접근법을 도출합니다.

## Operator 패턴 비교

### 1. Reconciliation Loop 패턴

**개념**: 현재 상태와 원하는 상태를 지속적으로 비교하여 차이를 조정

```python
class FRPOperator:
    """기본 Reconciliation Loop 구현"""

    def reconcile(self, request: ReconcileRequest) -> ReconcileResult:
        # 1. 현재 상태 조회
        current = self.get_current_state(request.name, request.namespace)

        # 2. 원하는 상태 정의
        desired = self.compute_desired_state(request.spec)

        # 3. 차이 계산
        diff = self.calculate_diff(current, desired)

        # 4. 차이 적용
        if diff:
            self.apply_changes(diff)
            return ReconcileResult(requeue_after=30)  # 30초 후 재확인

        return ReconcileResult()  # 동기화 완료
```

**장점**:
- K8s 네이티브 패턴
- 자가 치유 능력
- 선언적 구성

**단점**:
- 복잡한 상태 관리
- 성능 오버헤드

### 2. State Machine 패턴

**개념**: 리소스 생명주기를 명확한 상태로 관리

```python
from enum import Enum
from typing import Dict, Callable

class ServiceState(Enum):
    PENDING = "pending"
    PROVISIONING = "provisioning"
    RUNNING = "running"
    UPDATING = "updating"
    TERMINATING = "terminating"
    FAILED = "failed"

class StateMachineOperator:
    """상태 기계 기반 Operator"""

    def __init__(self):
        self.transitions: Dict[ServiceState, Dict[ServiceState, Callable]] = {
            ServiceState.PENDING: {
                ServiceState.PROVISIONING: self.provision_resources
            },
            ServiceState.PROVISIONING: {
                ServiceState.RUNNING: self.start_services,
                ServiceState.FAILED: self.handle_provision_failure
            },
            ServiceState.RUNNING: {
                ServiceState.UPDATING: self.update_resources,
                ServiceState.TERMINATING: self.cleanup_resources
            }
        }

    def reconcile(self, service: DistributedService):
        current_state = service.status.state
        desired_state = self.compute_desired_state(service)

        if current_state != desired_state:
            transition = self.transitions[current_state].get(desired_state)
            if transition:
                transition(service)
```

**장점**:
- 명확한 상태 전이
- 디버깅 용이
- 복잡한 워크플로우 관리

**단점**:
- 상태 폭발 가능성
- 유연성 부족

### 3. Event-Driven 패턴

**개념**: K8s 이벤트에 반응하여 동작

```python
class EventDrivenOperator:
    """이벤트 기반 Operator"""

    def __init__(self):
        self.event_handlers = {
            'Pod.Added': self.handle_pod_added,
            'Pod.Deleted': self.handle_pod_deleted,
            'Service.Modified': self.handle_service_modified,
            'ConfigMap.Updated': self.handle_config_updated
        }

    def watch_events(self):
        """K8s 이벤트 스트림 감시"""
        for event in self.k8s_watch.stream():
            event_type = f"{event['object'].kind}.{event['type']}"
            handler = self.event_handlers.get(event_type)
            if handler:
                handler(event['object'])

    def handle_pod_added(self, pod):
        """새 Pod 추가 시 FRP 클라이언트 설정"""
        if self.is_frp_backend(pod):
            self.register_backend(pod)
            self.update_frp_config()
```

**장점**:
- 실시간 반응
- 확장 가능
- 낮은 지연시간

**단점**:
- 이벤트 순서 보장 어려움
- 이벤트 유실 가능성

### 4. Finalizer 패턴

**개념**: 리소스 삭제 시 정리 작업 보장

```python
class FinalizerOperator:
    """Finalizer를 활용한 안전한 리소스 정리"""

    FINALIZER_NAME = "frp.io/cleanup"

    def reconcile(self, service: DistributedService):
        # 삭제 마크 확인
        if service.metadata.deletion_timestamp:
            if self.FINALIZER_NAME in service.metadata.finalizers:
                # 정리 작업 수행
                self.cleanup_resources(service)
                # Finalizer 제거
                self.remove_finalizer(service)
        else:
            # Finalizer 추가
            if self.FINALIZER_NAME not in service.metadata.finalizers:
                self.add_finalizer(service)
            # 일반 reconciliation
            self.manage_resources(service)

    def cleanup_resources(self, service):
        """리소스 정리 로직"""
        # FRP 설정에서 제거
        self.remove_from_frp_config(service)
        # 인증서 폐기
        self.revoke_certificates(service)
        # 메트릭 정리
        self.cleanup_metrics(service)
```

**장점**:
- 안전한 리소스 정리
- 데이터 일관성 보장
- K8s 표준 패턴

**단점**:
- 복잡성 증가
- 삭제 지연 가능

## FRP Operator를 위한 하이브리드 설계

### 권장 아키텍처

```python
class FRPServiceOperator:
    """FRP 분산 서비스를 위한 하이브리드 Operator"""

    def __init__(self):
        # 상태 기계 for 생명주기 관리
        self.state_machine = ServiceStateMachine()

        # 이벤트 핸들러 for 실시간 반응
        self.event_processor = EventProcessor()

        # Finalizer for 안전한 정리
        self.finalizer = FinalizerManager()

        # 메트릭과 상태 추적
        self.metrics = MetricsCollector()

    def reconcile(self, request: ReconcileRequest):
        """메인 reconciliation 로직"""
        service = self.get_service(request)

        # Finalizer 처리
        if service.is_being_deleted():
            return self.finalizer.handle_deletion(service)

        # 상태 기계 실행
        current_state = service.status.state
        actions = self.state_machine.get_actions(current_state, service.spec)

        for action in actions:
            try:
                action.execute(service)
                self.metrics.record_action(action)
            except Exception as e:
                self.handle_error(service, action, e)
                return ReconcileResult(requeue_after=5)

        # 상태 업데이트
        self.update_status(service)

        return ReconcileResult(requeue_after=60)
```

### CRD 설계

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: distributedservices.frp.io
spec:
  group: frp.io
  versions:
  - name: v1beta1
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
                enum: ["http", "tcp", "udp"]
              backends:
                type: object
                properties:
                  discovery:
                    type: string
                    enum: ["manual", "auto", "selector"]
                  selector:
                    type: object
                  endpoints:
                    type: array
              loadBalancing:
                type: object
                properties:
                  algorithm:
                    type: string
                    enum: ["random", "round-robin", "least-conn"]
                  healthCheck:
                    type: object
              security:
                type: object
                properties:
                  mtls:
                    type: object
                    properties:
                      enabled:
                        type: boolean
                      autoGenerate:
                        type: boolean
          status:
            type: object
            properties:
              state:
                type: string
              conditions:
                type: array
              observedGeneration:
                type: integer
              endpoints:
                type: array
    subresources:
      status: {}
      scale:
        specReplicasPath: .spec.backends.replicas
        statusReplicasPath: .status.activeEndpoints
```

### 상태 관리 전략

```python
class StatusManager:
    """CRD 상태 관리"""

    def update_status(self, service: DistributedService):
        """상태 업데이트 with 조건"""
        status = DistributedServiceStatus()

        # 상태 계산
        status.state = self.calculate_state(service)
        status.observedGeneration = service.metadata.generation

        # 조건 추가
        conditions = []

        # 백엔드 가용성
        backend_condition = Condition(
            type="BackendsAvailable",
            status=self.check_backends_available(service),
            reason="BackendsReady" if status else "NoBackendsFound",
            message=f"{len(service.status.endpoints)} backends available"
        )
        conditions.append(backend_condition)

        # mTLS 상태
        if service.spec.security.mtls.enabled:
            mtls_condition = Condition(
                type="CertificatesReady",
                status=self.check_certificates_ready(service),
                reason="CertificatesProvisioned",
                message="All certificates are valid and not expiring soon"
            )
            conditions.append(mtls_condition)

        status.conditions = conditions

        # 패치 적용
        self.patch_status(service, status)
```

## Operator 개발 도구 선택

### 1. Operator SDK (Go)

**장점**:
- 고성능
- K8s 네이티브
- 풍부한 생태계

**단점**:
- 학습 곡선
- 복잡한 빌드 프로세스

### 2. Kopf (Python)

**장점**:
- Python 친화적
- 빠른 프로토타이핑
- 간단한 구조

**예제**:
```python
import kopf
import kubernetes

@kopf.on.create('frp.io', 'v1', 'distributedservices')
async def create_fn(spec, name, namespace, **kwargs):
    """서비스 생성 핸들러"""
    # ConfigMap 생성
    config = generate_frp_config(spec)
    create_configmap(name, namespace, config)

    # Deployment 생성
    deployment = generate_deployment(spec)
    create_deployment(name, namespace, deployment)

    # Service 생성
    service = generate_service(spec)
    create_service(name, namespace, service)

    return {'message': 'DistributedService created'}

@kopf.on.update('frp.io', 'v1', 'distributedservices')
async def update_fn(spec, status, old, new, diff, **kwargs):
    """서비스 업데이트 핸들러"""
    for change in diff:
        if change[0] == 'change' and change[1] == ['spec', 'backends']:
            update_backends(spec)
        elif change[0] == 'change' and change[1] == ['spec', 'security']:
            update_security(spec)
```

### 3. Kubebuilder

**장점**:
- 표준 K8s 프로젝트 구조
- 코드 생성
- 테스트 프레임워크

**단점**:
- Go 전용
- 보일러플레이트 코드

## 모니터링과 디버깅

### 메트릭 수집

```python
class OperatorMetrics:
    """Operator 성능 메트릭"""

    def __init__(self):
        self.reconcile_duration = Histogram(
            'frp_operator_reconcile_duration_seconds',
            'Time spent in reconcile loop'
        )

        self.reconcile_errors = Counter(
            'frp_operator_reconcile_errors_total',
            'Total reconcile errors',
            ['error_type']
        )

        self.managed_services = Gauge(
            'frp_operator_managed_services',
            'Number of managed services',
            ['state']
        )

    @self.reconcile_duration.time()
    def track_reconcile(self, func):
        """Reconcile 시간 측정 데코레이터"""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.reconcile_errors.labels(
                    error_type=type(e).__name__
                ).inc()
                raise
        return wrapper
```

### 디버깅 전략

```python
class DebugOperator:
    """디버깅 지원 기능"""

    def __init__(self):
        self.debug_mode = os.getenv('DEBUG_MODE', 'false') == 'true'

    def reconcile_with_debug(self, service):
        """디버그 정보를 포함한 reconcile"""
        if self.debug_mode:
            logger.debug(f"Starting reconcile for {service.name}")
            logger.debug(f"Current spec: {service.spec}")
            logger.debug(f"Current status: {service.status}")

        # 각 단계별 상세 로깅
        with self.step_tracker("provision") as step:
            self.provision_resources(service)
            step.log_completion()

        with self.step_tracker("configure") as step:
            self.configure_frp(service)
            step.log_completion()
```

## 권장사항

### 1. 초기 구현 (MVP)
- Kopf 사용 (Python 기반, 빠른 개발)
- 기본 Reconciliation Loop
- 간단한 상태 관리

### 2. 프로덕션 준비
- 상태 기계 패턴 추가
- Finalizer 구현
- 포괄적인 에러 처리

### 3. 확장 단계
- 이벤트 기반 최적화
- 고급 상태 관리
- 성능 튜닝

### 4. 장기 목표
- Go 기반 재작성 고려
- Operator SDK 또는 Kubebuilder
- 고성능 요구사항 충족

## 결론

FRP 분산 서비스 프록시를 위한 Operator는 여러 패턴의 장점을 결합한 하이브리드 접근이 최적입니다. 초기에는 Python 기반 Kopf로 빠르게 구현하고, 프로덕션 요구사항에 따라 점진적으로 고도화하는 전략을 권장합니다. 핵심은 K8s의 선언적 특성을 활용하면서도 FRP의 동적 특성을 효과적으로 관리하는 것입니다.
