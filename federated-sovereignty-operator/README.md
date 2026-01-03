# Federated Sovereignty Operator

A **Policy-As-Code Framework for Enforcing Geopolitical Data Residency in Hybrid OpenShift Clusters**

## 🎯 Overview

The Federated Sovereignty Operator is a sophisticated Kubernetes operator that automatically enforces geopolitical data residency policies across hybrid cloud environments. It combines:

- **Custom Kubernetes Resources (CRD)** for policy definition
- **Python Kopf Framework** for operator logic
- **OPA Gatekeeper** for policy enforcement
- **Streamlit Dashboard** for real-time visualization

## 🏗️ Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐          ┌──────────────────────┐        │
│  │  Compliance      │          │  OPA Gatekeeper      │        │
│  │  Officer         │          │  (Enforcement)       │        │
│  │  (User)          │          │                      │        │
│  └────────┬─────────┘          └──────────┬───────────┘        │
│           │                               │                     │
│           │ creates                       │ validates           │
│           │ SovereignPolicy               │                     │
│           │                               │                     │
│  ┌────────▼────────────────────────────────────────┐           │
│  │  Federated Sovereignty Operator (Kopf)         │           │
│  │  - Watches SovereignPolicy CRD                 │           │
│  │  - Patches namespaces with compliance labels   │           │
│  │  - Creates/Updates OPA Constraints             │           │
│  │  - Manages policy lifecycle                    │           │
│  └────────┬─────────────────────────────────────────┘          │
│           │                                                     │
│           │ patches                                             │
│           │                                                     │
│  ┌────────▼──────────────┐        ┌──────────────────┐        │
│  │ Protected Namespace   │        │ Dashboard        │        │
│  │ (e.g., finance-eu)    │        │ (Streamlit)      │        │
│  │                       │        │ - Monitor        │        │
│  │ Pods with affinity ✓  │        │ - Visualize      │        │
│  │ Data residency locked │        │ - Report         │        │
│  └───────────────────────┘        └──────────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Compliance Officer** creates a `SovereignPolicy` resource
2. **Federated Sovereignty Operator** detects the resource
3. Operator **patches the target namespace** with compliance labels
4. Operator **creates OPA Gatekeeper Constraint** for enforcement
5. **OPA Gatekeeper** intercepts all Pod creation requests
6. **Developer** submits Pod YAML without region constraints
7. **OPA enforces** region constraints automatically
8. **Dashboard** visualizes policy compliance in real-time

## 📋 Features

### Core Features
- ✅ Custom SovereignPolicy CRD with full lifecycle support
- ✅ Automatic namespace labeling and enforcement
- ✅ OPA Gatekeeper integration for policy enforcement
- ✅ Support for multiple geopolitical regions
- ✅ Audit trail and compliance reporting
- ✅ Policy expiry date management

### Advanced Features
- ✅ Dry-run mode for policy testing
- ✅ Namespace exemption support
- ✅ Policy update detection and reconciliation
- ✅ Health checks and liveness probes
- ✅ High availability with pod anti-affinity
- ✅ RBAC with least-privilege design
- ✅ Comprehensive error logging

### Dashboard Features
- 🗺️ Geographical region visualization with Folium
- 📊 Real-time compliance metrics
- 📝 Policy management interface
- 🚀 Workload monitoring
- ✅ Compliance status dashboard
- 📜 Audit log viewer

## 🚀 Quick Start

### Prerequisites

- Kubernetes 1.19+
- OpenShift 4.x+ (or any Kubernetes distribution)
- kubectl CLI
- Docker (for building images)
- OPA Gatekeeper 3.10+
- Python 3.11+ (for development)

### Installation

1. **Clone and navigate to the repository**
```bash
cd federated-sovereignty-operator
```

2. **Install CRD**
```bash
kubectl apply -f deploy/crds/sovereignty_policy_crd.yaml
```

3. **Install OPA Gatekeeper** (if not already installed)
```bash
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm install gatekeeper/gatekeeper --name-template=gatekeeper \
  --namespace gatekeeper-system --create-namespace
```

4. **Build and deploy the operator**
```bash
cd scripts
bash deploy.sh
```

5. **Verify installation**
```bash
kubectl get pods -n federated-sovereignty-system
kubectl get sovereignpolicies
```

### Create Your First Policy

```bash
kubectl apply -f scripts/example-policy.yaml
```

This creates a `finance-eu-policy` that restricts the `finance` namespace to EU regions only.

### Deploy a Compliant Pod

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: finance-app
  namespace: finance
spec:
  containers:
  - name: app
    image: myapp:latest
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: topology.kubernetes.io/region
            operator: In
            values:
            - eu-central-1
```

### Launch Dashboard

```bash
cd dashboard
streamlit run app.py
```

Access at `http://localhost:8501`

## 📚 Usage Guide

### Creating a SovereignPolicy

```yaml
apiVersion: compliance.federated.io/v1alpha1
kind: SovereignPolicy
metadata:
  name: my-policy
spec:
  targetNamespace: my-app          # Namespace to protect
  allowedRegions:                  # Allowed regions
    - eu-central-1
    - eu-west-1
  enforcementAction: deny          # deny or dryrun
  description: "EU compliance"     # Optional
  expiryDate: "2026-12-31T23:59:59Z"  # Optional
```

### Policy Lifecycle

#### Creation
```bash
kubectl apply -f policy.yaml
# Operator:
# 1. Validates policy spec
# 2. Labels target namespace
# 3. Creates OPA constraint
# 4. Updates status to Active
```

#### Monitoring
```bash
kubectl get sovereignpolicies
kubectl describe sovereignpolicy my-policy
kubectl logs -f -n federated-sovereignty-system \
  -l app=federated-sovereignty-operator
```

#### Updating
```bash
kubectl patch sovereignpolicy my-policy \
  --type merge -p '{"spec":{"allowedRegions":["us-east-1"]}}'
# Operator automatically reconciles constraints
```

#### Deletion
```bash
kubectl delete sovereignpolicy my-policy
# Operator cleans up constraints (namespace labels preserved)
```

## 🔐 Security

### RBAC Permissions

The operator uses minimal required permissions:
- Read/write SovereignPolicy CRDs
- Patch namespaces
- Create/manage OPA constraints
- Read pods (monitoring)
- Write events (logging)

### Pod Security

- Non-root user (UID 1000)
- Read-only root filesystem (recommended)
- Resource limits and requests
- Health checks
- Pod disruption budgets

### Policy Enforcement

- OPA Gatekeeper intercepts all API requests
- Violations logged and audited
- Dry-run mode for testing
- Namespace exemptions for system resources

## 🧪 Testing

### Run Unit Tests

```bash
cd tests
pytest test_handlers.py -v
```

### Run Policy Tests

```bash
cd tests
opa test test_rego.rego ../policies/residency.rego -v
```

### Manual Testing

```bash
# Create test policy
kubectl apply -f scripts/example-policy.yaml

# Verify namespace is labeled
kubectl get ns finance -o jsonpath='{.metadata.labels}'

# Try creating non-compliant pod (should be rejected)
kubectl run test-pod --image=nginx -n finance
# Error: Pod denied - missing nodeAffinity

# Try creating compliant pod
kubectl apply -f scripts/example-policy.yaml
# Success!
```

## 📊 Monitoring & Observability

### Operator Logs

```bash
kubectl logs -n federated-sovereignty-system \
  -l app=federated-sovereignty-operator -f
```

### Policy Status

```bash
kubectl get sovereignpolicies -o wide
kubectl describe sovereignpolicy finance-eu-policy
```

### OPA Gatekeeper Audit

```bash
kubectl get constraints -n gatekeeper-system
kubectl logs -n gatekeeper-system -l app=gatekeeper -f
```

### Dashboard

Access real-time visualization at `http://localhost:8501` with:
- Policy overview and metrics
- Geographical region coverage maps
- Workload compliance status
- Audit logs and alerts

## 📁 Project Structure

```
federated-sovereignty-operator/
├── deploy/
│   ├── crds/
│   │   └── sovereignty_policy_crd.yaml
│   ├── operator/
│   │   ├── deployment.yaml
│   │   ├── rbac.yaml
│   │   └── service_account.yaml
│   └── gatekeeper/
│       ├── template_residency.yaml
│       └── sync.yaml
├── src/
│   ├── handlers.py              # Kopf event handlers
│   ├── utils.py                 # Kubernetes client utilities
│   ├── Dockerfile               # Container image
│   └── __init__.py
├── policies/
│   └── residency.rego           # OPA Rego policies
├── tests/
│   ├── test_handlers.py         # Python tests
│   └── test_rego.rego           # OPA tests
├── dashboard/
│   └── app.py                   # Streamlit dashboard
├── scripts/
│   ├── deploy.sh                # Deployment script
│   ├── uninstall.sh             # Cleanup script
│   ├── run_tests.sh             # Test runner
│   └── example-policy.yaml      # Example policy
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🔧 Configuration

### Environment Variables

```bash
KOPF_LIVENESS_PROBE_TIMEOUT=10    # Liveness probe timeout
KOPF_DEBUG=false                   # Enable debug logging
LOG_LEVEL=INFO                     # Logging level
```

### ConfigMap

Optional configuration via `federated-sovereignty-config` ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: federated-sovereignty-config
  namespace: federated-sovereignty-system
data:
  max_policies: "100"
  audit_retention_days: "90"
```

## 🐛 Troubleshooting

### Operator not starting

```bash
# Check operator logs
kubectl logs -n federated-sovereignty-system \
  -l app=federated-sovereignty-operator

# Check pod status
kubectl describe pod -n federated-sovereignty-system \
  -l app=federated-sovereignty-operator

# Check RBAC permissions
kubectl auth can-i create sovereignpolicies --as=system:serviceaccount:federated-sovereignty-system:federated-sovereignty-operator
```

### Policy not enforced

```bash
# Verify namespace is labeled
kubectl get ns <namespace> -o yaml | grep compliance.gov

# Check OPA constraint
kubectl get constraints -n gatekeeper-system

# Test OPA directly
kubectl exec -it <gatekeeper-pod> -n gatekeeper-system -- \
  curl http://localhost:8181/v1/compile
```

### Pod creation rejected unexpectedly

```bash
# View OPA violation message
kubectl describe pod <pod-name> -n <namespace>

# Check policy status
kubectl get sovereignpolicy -o yaml

# Test in dry-run mode
kubectl patch sovereignpolicy <name> \
  --type merge -p '{"spec":{"enforcementAction":"dryrun"}}'
```

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📝 License

Apache License 2.0 - See LICENSE file for details

## 🎓 Learning Resources

### Kubernetes Operators
- https://kubernetes.io/docs/concepts/extend-kubernetes/operator/
- https://kopf.readthedocs.io/

### OPA Gatekeeper
- https://open-policy-agent.org/docs/v0.44/
- https://open-policy-agent.github.io/gatekeeper/

### Rego Policy Language
- https://www.openpolicyagent.org/docs/v0.44/policy-language/

## 📞 Support

For issues and questions:
- Open a GitHub issue
- Check existing documentation
- Review logs and error messages
- Test in dry-run mode first

## 🏆 EB1A Relevance

This project demonstrates:
- **Architectural Innovation**: Policy-as-Code framework for multi-region compliance
- **Technical Depth**: Kubernetes operators, Python, Rego, and distributed systems
- **Executive Impact**: Visualizes complex compliance requirements for stakeholders
- **Scalability**: Handles hybrid multi-cloud environments
- **Production Ready**: Security, HA, monitoring, and audit trails

---

**Version**: 0.1.0  
**Author**: Strategic Architect & AI Engineer  
**Last Updated**: January 2026
