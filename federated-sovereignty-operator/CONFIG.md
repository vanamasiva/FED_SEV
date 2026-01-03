# Federated Sovereignty Operator - Configuration Guide

## Environment Variables

### Operator Configuration

```bash
# Kopf Framework Settings
KOPF_LIVENESS_PROBE_TIMEOUT=10        # Liveness probe timeout (seconds)
KOPF_DEBUG=false                       # Enable Kopf debug mode
KOPF_LOG_FORMAT=json                   # JSON structured logging

# Application Settings
LOG_LEVEL=INFO                         # Logging level (DEBUG, INFO, WARNING, ERROR)
OPERATOR_NAMESPACE=federated-sovereignty-system
OPERATOR_WATCH_ALL_NAMESPACES=true    # Watch all namespaces (vs specific list)

# Kubernetes API
KUBECONFIG=/var/run/secrets/kubernetes.io/serviceaccount/kubeconfig
KUBERNETES_SERVICE_HOST=kubernetes.default.svc
KUBERNETES_SERVICE_PORT=443

# OPA Gatekeeper
OPA_NAMESPACE=gatekeeper-system
OPA_SYNC_INTERVAL=30                  # Sync interval (seconds)

# Policy Enforcement
DEFAULT_ENFORCEMENT_ACTION=deny        # deny | dryrun
POLICY_EXPIRY_CHECK_INTERVAL=3600     # Check policy expiry every hour
```

## ConfigMap Configuration

Create a ConfigMap for operator configuration:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: federated-sovereignty-config
  namespace: federated-sovereignty-system
data:
  # Policy settings
  max_concurrent_policies: "50"
  policy_timeout_seconds: "300"
  policy_revision_limit: "10"
  
  # OPA settings
  opa_audit_log_level: "info"
  opa_max_constraint_violations: "1000"
  
  # Audit trail
  audit_retention_days: "90"
  audit_log_storage: "kubernetes"  # kubernetes | external
  
  # Reconciliation
  reconciliation_interval_seconds: "300"
  namespace_patch_retry_limit: "3"
  
  # Security
  enable_tls_verification: "true"
  rbac_check_interval_seconds: "600"
```

## Deployment Configuration

### Replicas and HA

```yaml
# High Availability (Recommended for Production)
replicas: 3
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0

# Pod Anti-Affinity
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - federated-sovereignty-operator
        topologyKey: kubernetes.io/hostname
```

### Resource Limits

```yaml
# Development
resources:
  requests:
    cpu: 50m
    memory: 128Mi
  limits:
    cpu: 200m
    memory: 256Mi

# Production
resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

### Health Checks

```yaml
# Liveness probe (restart if unhealthy)
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3

# Readiness probe (remove from service if not ready)
readinessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 3
  failureThreshold: 2
```

## OPA Gatekeeper Configuration

### ConstraintTemplate Settings

```yaml
# K8sGeoResidency Constraint Template
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: k8sgeoresidency
spec:
  crd:
    spec:
      names:
        kind: K8sGeoResidency
      validation:
        openAPIV3Schema:
          properties:
            allowedRegions:
              type: array
              items:
                type: string
            enforcement:
              type: string
              enum: [deny, dryrun]
            exemptedNamespaces:
              type: array
              items:
                type: string
```

### Default Constraint

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sGeoResidency
metadata:
  name: default-geo-residency
spec:
  match:
    excludedNamespaces:
      - kube-system
      - kube-public
      - kube-node-lease
      - gatekeeper-system
      - federated-sovereignty-system
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
  parameters:
    enforcement: deny
    exemptedNamespaces:
      - kube-system
      - kube-public
      - gatekeeper-system
      - federated-sovereignty-system
```

### Gatekeeper Config

```yaml
apiVersion: config.gatekeeper.sh/v1alpha1
kind: Config
metadata:
  name: config
  namespace: gatekeeper-system
spec:
  sync:
    syncOnly:
      - group: ""
        version: "v1"
        kind: "Namespace"
  audit:
    logOnly: false
    maxAuditEventsLogged: 100
```

## Logging Configuration

### Log Levels

```
DEBUG   - Detailed troubleshooting information
INFO    - Operational messages (default)
WARNING - Warning messages and deprecations
ERROR   - Error messages and exceptions
```

### Structured Logging

Enable JSON logging for easier parsing:

```python
import logging
import json

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Example structured log entry:
# {
#   "timestamp": "2026-01-03T10:30:00Z",
#   "logger": "handlers",
#   "level": "INFO",
#   "message": "SovereignPolicy created",
#   "policy_name": "finance-eu-policy",
#   "target_namespace": "finance",
#   "allowed_regions": ["eu-central-1", "eu-west-1"]
# }
```

## Monitoring and Observability

### Prometheus Metrics

Configure Prometheus to scrape operator metrics:

```yaml
apiVersion: v1
kind: ServiceMonitor
metadata:
  name: federated-sovereignty-operator
  namespace: federated-sovereignty-system
spec:
  selector:
    matchLabels:
      app: federated-sovereignty-operator
  endpoints:
  - port: metrics
    interval: 30s
```

### Key Metrics to Monitor

```
# Policy metrics
federated_sovereignty_policies_total{status="active"}
federated_sovereignty_policies_total{status="failed"}
federated_sovereignty_policy_creation_duration_seconds
federated_sovereignty_policy_update_duration_seconds

# Constraint metrics
federated_sovereignty_constraints_created
federated_sovereignty_constraints_violations

# Pod metrics
federated_sovereignty_pods_compliant
federated_sovereignty_pods_non_compliant

# Operator health
federated_sovereignty_operator_up
federated_sovereignty_operator_reconciliation_duration_seconds
```

## Backup and Recovery

### Backup Policy Resources

```bash
# Backup all SovereignPolicy resources
kubectl get sovereignpolicies -o yaml > policies-backup.yaml

# Backup specific policy
kubectl get sovereignpolicy finance-eu-policy -o yaml > finance-policy-backup.yaml

# Backup namespace labels
kubectl get namespace finance -o yaml > finance-namespace-backup.yaml
```

### Restore Policies

```bash
# Restore all policies
kubectl apply -f policies-backup.yaml

# Restore specific policy
kubectl apply -f finance-policy-backup.yaml
```

### Disaster Recovery

```bash
# If operator is down, policies remain enforced by OPA
# To re-enable operator:

1. Restore operator deployment
2. Operator will detect existing policies and constraints
3. Operator will update status to "Active"

# If OPA is down:
# 1. Pods can still be created (no enforcement)
# 2. Restore OPA from backup
# 3. Reapply constraints
```

## Troubleshooting Configuration

### Enable Debug Logging

```yaml
# Update operator deployment
kubectl set env deployment/federated-sovereignty-operator \
  -n federated-sovereignty-system \
  LOG_LEVEL=DEBUG \
  KOPF_DEBUG=true
```

### View Configuration

```bash
# Check operator config
kubectl get configmap federated-sovereignty-config \
  -n federated-sovereignty-system -o yaml

# Check environment variables
kubectl describe pod <operator-pod> \
  -n federated-sovereignty-system | grep -A 10 "Environment"

# Check mounted volumes
kubectl describe pod <operator-pod> \
  -n federated-sovereignty-system | grep -A 10 "Mounts"
```

### Common Configuration Issues

| Issue | Solution |
|-------|----------|
| Operator not starting | Check LOG_LEVEL, KOPF_DEBUG in env vars |
| Policies not enforced | Verify OPA Gatekeeper is running, check constraints |
| High memory usage | Increase memory limits, check policy count |
| Slow reconciliation | Increase CPU limits, reduce sync intervals |
| Namespace labels not applied | Check RBAC permissions, check Kubernetes API access |

## Security Configuration

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: federated-sovereignty-operator
  namespace: federated-sovereignty-system
spec:
  podSelector:
    matchLabels:
      app: federated-sovereignty-operator
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: federated-sovereignty-system
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443  # Kubernetes API
    - protocol: TCP
      port: 8080  # Health checks
```

### Pod Security Policy

```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: federated-sovereignty-operator
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'MustRunAs'
    seLinuxOptions:
      level: "s0:c123,c456"
  fsGroup:
    rule: 'MustRunAs'
    ranges:
      - min: 1000
        max: 65535
```

---

**Configuration Guide Version**: 1.0  
**Last Updated**: January 2026
