# Federated Sovereignty Operator - API Reference

## SovereignPolicy CRD API

### Group Version Kind

```
Group: compliance.federated.io
Version: v1alpha1
Kind: SovereignPolicy
```

### API Endpoint

```
GET    /apis/compliance.federated.io/v1alpha1/sovereignpolicies
POST   /apis/compliance.federated.io/v1alpha1/sovereignpolicies
GET    /apis/compliance.federated.io/v1alpha1/sovereignpolicies/{name}
PUT    /apis/compliance.federated.io/v1alpha1/sovereignpolicies/{name}
PATCH  /apis/compliance.federated.io/v1alpha1/sovereignpolicies/{name}
DELETE /apis/compliance.federated.io/v1alpha1/sovereignpolicies/{name}
```

### Full Specification

```yaml
apiVersion: compliance.federated.io/v1alpha1
kind: SovereignPolicy
metadata:
  # Standard Kubernetes metadata
  name: my-policy                        # String, required, DNS-1123
  namespace: default                     # String, optional (cluster-scoped resource)
  labels:
    app: my-policy
  annotations:
    description: "Policy description"

spec:
  # Required Fields
  targetNamespace: finance              # String, required
                                        # Namespace to apply policy to
                                        # Must exist when policy is created
                                        # Pattern: ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$
  
  allowedRegions:                       # Array of strings, required
    - eu-central-1                      # At least one region must be specified
    - eu-west-1
  
  # Optional Fields
  enforcementAction: deny                # String, optional (default: deny)
                                        # Enum: ["deny", "dryrun"]
                                        # deny: Block violating pods
                                        # dryrun: Log violations only
  
  description: |                        # String, optional
    "EU data residency requirement"     # Max 256 characters
    "for GDPR compliance"
  
  expiryDate: "2026-12-31T23:59:59Z"   # RFC3339 date, optional
                                        # Policy auto-expires at this date
  
  excludedNamespaces:                   # Array of strings, optional
    - kube-system                       # Namespaces exempt from enforcement
    - kube-public                       # (merged with system namespaces)

status:
  # Set by operator, read-only
  phase: Active                         # Enum: [Pending, Active, Failed, Expired]
  lastUpdated: "2026-01-03T10:30:00Z"  # RFC3339 timestamp
  message: "Sovereignty enforcement..." # String, informational message
  constraintCreated: true               # Boolean, indicates OPA constraint status
```

### Usage Examples

#### Create Policy

```bash
kubectl apply -f - <<EOF
apiVersion: compliance.federated.io/v1alpha1
kind: SovereignPolicy
metadata:
  name: finance-eu-policy
spec:
  targetNamespace: finance
  allowedRegions:
    - eu-central-1
    - eu-west-1
  enforcementAction: deny
EOF
```

#### Get Policy

```bash
kubectl get sovereignpolicies                           # List all
kubectl get sovereignpolicies finance-eu-policy         # Get specific
kubectl get sovereignpolicies -o wide                   # Extended info
kubectl get sovereignpolicies -o yaml                   # Full YAML
kubectl describe sovereignpolicies finance-eu-policy    # Detailed view
```

#### Update Policy

```bash
# Patch specific fields
kubectl patch sovereignpolicies finance-eu-policy \
  --type merge -p '{"spec":{"allowedRegions":["us-east-1"]}}'

# Edit in place
kubectl edit sovereignpolicies finance-eu-policy

# Apply new version
kubectl apply -f updated-policy.yaml
```

#### Delete Policy

```bash
kubectl delete sovereignpolicies finance-eu-policy
kubectl delete sovereignpolicies --all                   # Delete all
```

### Status Subresource

The SovereignPolicy status is updated by the operator:

```yaml
status:
  phase: Active                    # Current state
  lastUpdated: "2026-01-03T..."   # Last status update
  message: "Policy active"        # Informational message
  constraintCreated: true         # OPA constraint status
```

Query status:

```bash
kubectl get sovereignpolicies finance-eu-policy -o jsonpath='{.status.phase}'
kubectl describe sovereignpolicies finance-eu-policy | grep -A 10 "Status:"
```

## Kubernetes Namespace Labels

When a policy is created, the target namespace is labeled:

```yaml
metadata:
  labels:
    compliance.gov/allowed-regions: "eu-central-1,eu-west-1"
    compliance.gov/policy-name: "finance-eu-policy"
    compliance.gov/policy-namespace: "default"
    compliance.gov/enforcement-action: "deny"
    compliance.gov/updated-at: "2026-01-03T10:30:00Z"
```

Query labels:

```bash
kubectl get ns finance -o jsonpath='{.metadata.labels}'
kubectl label ns finance -L compliance.gov/allowed-regions
```

## OPA Gatekeeper Constraints

When a policy is created, a K8sGeoResidency constraint is created:

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sGeoResidency
metadata:
  name: geo-residency-finance
spec:
  match:
    namespaceSelector:
      matchLabels:
        compliance.gov/allowed-regions: "eu-central-1,eu-west-1"
    excludedNamespaces:
      - kube-system
      - kube-public
      - gatekeeper-system
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
  parameters:
    allowedRegions:
      - eu-central-1
      - eu-west-1
    enforcement: deny
```

## Webhook Integration

### Validating Webhook

The operator validates SovereignPolicy resources via Kubernetes validation:

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: sovereignpolicy.compliance.federated.io
webhooks:
- name: sovereignpolicy.compliance.federated.io
  clientConfig:
    service:
      name: federated-sovereignty-operator
      namespace: federated-sovereignty-system
      path: /validate
    caBundle: LS0tLS1...
  rules:
  - operations: ["CREATE", "UPDATE"]
    apiGroups: ["compliance.federated.io"]
    apiVersions: ["v1alpha1"]
    resources: ["sovereignpolicies"]
  sideEffects: None
```

### Mutation Webhook

Optional: Automatically add affinity to pods:

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: sovereignpolicy.compliance.federated.io
webhooks:
- name: sovereignpolicy.compliance.federated.io
  clientConfig:
    service:
      name: federated-sovereignty-operator
      namespace: federated-sovereignty-system
      path: /mutate
  rules:
  - operations: ["CREATE"]
    apiGroups: [""]
    apiVersions: ["v1"]
    resources: ["pods"]
  sideEffects: None
```

## Events

The operator creates Kubernetes events for policy lifecycle:

```bash
# View events
kubectl describe sovereignpolicies finance-eu-policy
kubectl get events -n default --field-selector involvedObject.name=finance-eu-policy

# Event types
- Created: Policy created successfully
- Updated: Policy updated successfully
- Failed: Policy failed to apply
- Reconciled: Policy reconciled
```

## Errors and Validation

### Common Validation Errors

```
error validating "policy.yaml": error converting YAML to JSON:
  yaml: line X: mapping values are not allowed in this context
  → Fix: Check YAML indentation

The SovereignPolicy "my-policy" is invalid:
  spec.allowedRegions: Invalid value: []: at least 1 item must be present
  → Fix: At least one region is required

The SovereignPolicy "my-policy" is invalid:
  spec.targetNamespace: Invalid value: "my-namespace": namespace does not exist
  → Fix: Create the namespace first

The SovereignPolicy "my-policy" is invalid:
  spec.enforcementAction: Unsupported value: "ignore": must be one of [deny, dryrun]
  → Fix: Use "deny" or "dryrun"
```

### Runtime Errors

```
Failed to patch namespace:
  error: namespace "finance" does not exist
  → Check targetNamespace exists

Failed to create constraint:
  error: OPA not responding
  → Check OPA Gatekeeper is running

Failed to update status:
  error: permission denied
  → Check operator RBAC permissions
```

## Rate Limiting

The operator respects Kubernetes API rate limits:

- Default: 200 requests/second per client
- Kopf handles exponential backoff automatically
- Monitor with: `kubectl get events | grep -i rate`

## Pagination

For large result sets:

```bash
# List with pagination
kubectl get sovereignpolicies --limit=10

# Offset pagination
kubectl get sovereignpolicies --offset=10 --limit=10

# Continue token
kubectl get sovereignpolicies --continue=<token>
```

## Field Selectors

Query policies by field:

```bash
# By name
kubectl get sovereignpolicies --field-selector metadata.name=finance-eu-policy

# By namespace
kubectl get sovereignpolicies --field-selector metadata.namespace=default

# By status
kubectl get sovereignpolicies --field-selector status.phase=Active
```

## Label Selectors

Query by labels:

```bash
# By label presence
kubectl get sovereignpolicies -l team=finance

# By label value
kubectl get sovereignpolicies -l environment=production

# By multiple labels
kubectl get sovereignpolicies -l team=finance,environment=production
```

## Watch Resources

Watch for policy changes:

```bash
# Watch all policies
kubectl watch sovereignpolicies

# Watch specific policy
kubectl watch sovereignpolicy finance-eu-policy

# Watch with go-template
kubectl get sovereignpolicies -w -o custom-columns=\
NAME:.metadata.name,\
NAMESPACE:.spec.targetNamespace,\
REGIONS:.spec.allowedRegions,\
STATUS:.status.phase
```

## API Versioning

### Current Version
- `compliance.federated.io/v1alpha1` - Current (unstable, breaking changes possible)

### Planned Versions
- `compliance.federated.io/v1beta1` - Beta (more stable)
- `compliance.federated.io/v1` - Stable (API guaranteed)

### Migration

When upgrading API versions:

```bash
# Dry-run first
kubectl apply -f policy.yaml --dry-run=client

# Apply new version
kubectl apply -f policy.yaml

# Check conversion
kubectl get sovereignpolicies finance-eu-policy -o yaml
```

---

**API Reference Version**: 1.0  
**Last Updated**: January 2026  
**API Stability**: Alpha (v1alpha1)
