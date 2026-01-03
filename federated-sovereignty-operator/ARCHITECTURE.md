# Federated Sovereignty Operator - Architecture Deep Dive

## System Design

### High-Level Architecture Principles

1. **Separation of Concerns**
   - **Policy Definition Layer**: Kubernetes CRDs for policy intent
   - **Enforcement Layer**: OPA Gatekeeper for API-level enforcement
   - **Orchestration Layer**: Python Kopf operator for coordination
   - **Visualization Layer**: Streamlit dashboard for compliance visibility

2. **Event-Driven Design**
   - Operator reacts to policy creation, update, and deletion events
   - Cascade effects automatically enforce constraints
   - Timer handlers for periodic checks (expiry, compliance)

3. **Declarative Configuration**
   - All policies expressed as Kubernetes YAML
   - GitOps-ready for version control and auditing
   - Immutable audit trail via Kubernetes API

## Data Model

### SovereignPolicy CRD

```
SovereignPolicy
├── metadata
│   ├── name: policy identifier
│   ├── namespace: operator's namespace
│   └── labels: for discovery
├── spec
│   ├── targetNamespace: string (required)
│   ├── allowedRegions: string[] (required)
│   ├── enforcementAction: "deny" | "dryrun"
│   ├── description: string
│   ├── expiryDate: ISO 8601 datetime
│   └── excludedNamespaces: string[]
└── status
    ├── phase: "Pending" | "Active" | "Failed" | "Expired"
    ├── lastUpdated: timestamp
    ├── message: string
    └── constraintCreated: boolean
```

### Namespace Compliance Labels

When a policy is applied, the target namespace gets:

```yaml
metadata:
  labels:
    compliance.gov/allowed-regions: "eu-central-1,eu-west-1"
    compliance.gov/policy-name: "finance-eu-policy"
    compliance.gov/policy-namespace: "default"
    compliance.gov/enforcement-action: "deny"
    compliance.gov/updated-at: "2026-01-03T10:30:00Z"
```

## Operator Logic Flow

### Creation Handler Flow

```
User applies SovereignPolicy
    ↓
[on.create event triggered]
    ↓
Validate spec (required fields, syntax)
    ↓
Check policy expiry
    ↓
Verify target namespace exists
    ↓
Patch namespace with compliance labels
    ↓
Create OPA Constraint (K8sGeoResidency)
    ↓
Update policy status to "Active"
    ↓
Log "Sovereignty enforcement active"
```

### Update Handler Flow

```
User patches SovereignPolicy
    ↓
[on.update event triggered]
    ↓
Compare old spec vs new spec
    ↓
Detect region changes
    ↓
If no significant changes → exit
    ↓
Update namespace labels
    ↓
Delete old constraint
    ↓
Create new constraint with updated regions
    ↓
Update policy status
```

### Deletion Handler Flow

```
User deletes SovereignPolicy
    ↓
[on.delete event triggered]
    ↓
Retrieve target namespace
    ↓
Delete OPA Constraint
    ↓
Preserve namespace labels (audit trail)
    ↓
Log deletion
```

## OPA Gatekeeper Integration

### Constraint Flow

```
Pod Creation Request
    ↓
[OPA Gatekeeper Webhook]
    ↓
Load ConstraintTemplate (K8sGeoResidency)
    ↓
Execute Rego policy logic
    ↓
Check Pod namespace compliance labels
    ↓
Validate Pod affinity rules
    ↓
If violation → Reject request with message
    ↓
If valid → Allow request
```

### Rego Policy Logic

```rego
# 1. Check if Pod exists with allowed regions
allowed_regions[region] ← 
    namespace labels have "compliance.gov/allowed-regions"
    parse as comma-separated list

# 2. Check Pod affinity
container_affinity_match() ←
    Pod has nodeAffinity
    With requiredDuringScheduling rules
    With matchExpression key = "topology.kubernetes.io/region"
    With values in allowed_regions

# 3. Determine violation
violation[msg] ←
    Pod found
    no affinity match
    generate error message
```

## Kubernetes API Interactions

### RBAC Permissions

The operator's ServiceAccount requires:

```
CompliancePolicy CRD (compliance.federated.io):
  - get, list, watch, create, update, patch, delete, status

Namespaces (core):
  - get, list, watch, patch

OPA Constraints (constraints.gatekeeper.sh):
  - get, list, watch, create, update, patch, delete

Pods (core):
  - get, list, watch (monitoring only)

Events (core):
  - create, patch (logging)

ConfigMaps (core):
  - get, list, watch, create, update, patch (Kopf state management)
```

## Error Handling & Resilience

### Failure Scenarios

| Scenario | Handling |
|----------|----------|
| Target namespace doesn't exist | Update status to "Failed" with error message |
| OPA constraint creation fails | Continue with "Active" status, partial success logged |
| Kubernetes API timeout | Kopf retry with exponential backoff |
| Policy validation error | Update status to "Failed", operator continues |
| Expired policy detected | Update status to "Expired" via timer handler |

### Retry Strategy

```
Initial attempt
    ↓
If ApiException: retry after 5s
    ↓
If still failing: retry after 30s
    ↓
If still failing: update status, alert
```

## Performance Considerations

### Scalability

- **Single Operator Instance**: Can manage 1000+ policies
- **Recommended Replicas**: 2-3 for HA (pod anti-affinity)
- **Resource Allocation**:
  - CPU Request: 100m, Limit: 500m
  - Memory Request: 256Mi, Limit: 512Mi

### Event Processing

- Kopf framework handles async event processing
- Multiple policies can be processed concurrently
- Namespace patching is atomic operation

## Security Hardening

### Network Security

```yaml
# Operator pod runs with:
- Non-root user (UID 1000)
- Read-only root filesystem
- Network policies (restrict egress/ingress)
- No privileged escalation
```

### Secret Management

- Kubernetes API tokens managed by ServiceAccount
- No hardcoded credentials
- All interactions via RBAC

### Audit Trail

- Kubernetes audit logs capture all API changes
- Policy changes create new SovereignPolicy versions
- Namespace label changes logged
- OPA audit logs track denied requests

## Dashboard Architecture

### Streamlit Components

```
Dashboard (app.py)
├── Overview Page
│   ├── Metrics (total, active, failed policies)
│   ├── Recent policies preview
│   └── Policy count by region
├── Policies Page
│   ├── Policy table view
│   ├── Detail view with region map
│   └── Compliance labels display
├── Compliance Page
│   ├── Violation detection
│   ├── Pod affinity validation
│   └── Issue reporting
└── Audit Log Page
    └── Event history (future)

Data Source: Kubernetes API
  └── Custom Resources
  └── Namespaces
  └── Pods
```

### Visualization Features

- **Folium Maps**: Geographic distribution of allowed regions
- **Pandas DataFrames**: Tabular policy and workload data
- **Plotly Charts**: Compliance metrics and trends
- **Real-time Updates**: Live Kubernetes API queries

## Extension Points

### Adding New Policy Types

1. Create new CRD with different spec fields
2. Add handler for new resource type
3. Extend OPA constraint logic
4. Update dashboard to display new metrics

### Adding Alerting

```python
# In handlers.py
def alert_on_failure(...)
    send_to_prometheus()
    send_to_pagerduty()
    send_slack_message()
```

### Custom Enforcement Actions

```python
# Beyond "deny" and "dryrun"
enforcement_actions = {
    "deny": block_request,
    "dryrun": log_only,
    "warn": log_and_allow,  # New
    "custom": custom_handler  # New
}
```

## Testing Strategy

### Unit Tests (Python)

- Test utility functions (region parsing, constraint generation)
- Mock Kubernetes API interactions
- Test handler logic with fixtures
- Parametrized tests for multiple scenarios

### Integration Tests

- Deploy to test cluster
- Create actual SovereignPolicy resources
- Verify namespace patching
- Verify constraint creation
- Test pod creation with valid/invalid affinity

### Policy Tests (OPA)

- Test Rego syntax and logic
- Test allowed regions parsing
- Test affinity validation rules
- Test exemption logic

### Load Testing

- Create 100+ policies
- Monitor operator memory/CPU
- Measure policy reconciliation time

## Deployment Topology

### Single-Region Deployment

```
Single Kubernetes Cluster
├── federated-sovereignty-system namespace
│   ├── Operator pod (2 replicas)
│   ├── Service
│   └── ConfigMap
├── gatekeeper-system namespace
│   ├── Gatekeeper pods
│   └── Constraints
└── Protected namespaces
    └── Pods with affinity rules
```

### Multi-Cluster Deployment

```
Control Cluster (Admin)
├── Central operator instance
└── Policy management

Workload Cluster 1 (US)
├── Operator instance
└── Synced policies

Workload Cluster 2 (EU)
├── Operator instance
└── Synced policies

Workload Cluster 3 (APAC)
├── Operator instance
└── Synced policies
```

Policy sync via GitOps or federation APIs.

---

**Architecture Version**: 1.0  
**Last Updated**: January 2026
