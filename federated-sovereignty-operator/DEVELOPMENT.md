# Federated Sovereignty Operator - Development Guide

## Setting Up Development Environment

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- kubectl configured to access a Kubernetes cluster
- Git

### Local Setup

```bash
# Clone the repository
git clone https://github.com/yourorg/federated-sovereignty-operator.git
cd federated-sovereignty-operator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-mock flake8 black mypy

# Install pre-commit hooks (optional)
pre-commit install
```

### Running Tests Locally

```bash
# Unit tests
pytest tests/test_handlers.py -v --cov=src

# OPA policy tests (requires OPA CLI)
curl https://openpolicyagent.org/downloads/latest/opa_linux_amd64 -o opa
chmod +x opa
./opa test tests/test_rego.rego policies/residency.rego -v
```

## Code Structure

### handlers.py

Main operator logic with Kopf decorators:

```python
@kopf.on.create("compliance.federated.io", "v1alpha1", "sovereignpolicies")
def on_sovereign_policy_create(spec, name, namespace, **kwargs):
    """Handle SovereignPolicy creation"""
    # 1. Validate spec
    # 2. Patch namespace
    # 3. Create constraint
    # 4. Update status

@kopf.on.update("compliance.federated.io", "v1alpha1", "sovereignpolicies")
def on_sovereign_policy_update(spec, name, namespace, old, new, **kwargs):
    """Handle SovereignPolicy updates"""
    # 1. Detect changes
    # 2. Update resources
    # 3. Reconcile constraints

@kopf.on.delete("compliance.federated.io", "v1alpha1", "sovereignpolicies")
def on_sovereign_policy_delete(spec, name, namespace, **kwargs):
    """Handle SovereignPolicy deletion"""
    # 1. Delete constraints
    # 2. Preserve audit trail
    # 3. Log deletion

@kopf.timer("compliance.federated.io", "v1alpha1", "sovereignpolicies", interval=3600)
def check_policy_expiry(spec, name, namespace, body, **kwargs):
    """Periodic expiry checks"""
    # Check if policy has expired
    # Update status if needed
```

### utils.py

Kubernetes client wrapper and helper functions:

```python
class KubernetesClient:
    """Kubernetes API client wrapper"""
    - patch_namespace()
    - create_custom_resource()
    - delete_custom_resource()
    - get_namespace()
    - list_custom_resources()

def format_region_label(regions: List[str]) -> str:
    """Format regions as comma-separated label"""

def create_gatekeeper_constraint() -> Dict:
    """Generate constraint resource"""

def update_sovereign_policy_status():
    """Update policy status subresource"""
```

## Adding New Features

### Adding a New Handler

```python
@kopf.on.event("compliance.federated.io", "v1alpha1", "sovereignpolicies")
def on_policy_event(event, **kwargs):
    """Handle policy events"""
    event_type = event.get("type")
    resource = event.get("object")
    
    logger.info(f"Policy event: {event_type}")
    # Add your logic here
```

### Adding Dashboard Features

Edit `dashboard/app.py`:

```python
# In main() function, add new page option
if page == "New Feature":
    st.header("New Feature")
    
    # Get data from Kubernetes
    policies = get_sovereign_policies()
    
    # Display in UI
    st.dataframe(df)
    
    # Add interactions
    selected = st.selectbox("Select policy", [p["metadata"]["name"] for p in policies])
```

### Adding OPA Policy Rules

Edit `policies/residency.rego`:

```rego
# Add new rule
violation[msg] {
    # Your condition
    msg := "Your violation message"
}

# Add helper function
my_helper_function {
    # Logic here
}
```

## Testing Best Practices

### Unit Test Template

```python
@patch('handlers.KubernetesClient')
def test_scenario(mock_k8s_class):
    """Test a specific scenario"""
    # Setup
    mock_k8s = MagicMock()
    mock_k8s_class.return_value = mock_k8s
    
    # Execute
    on_sovereign_policy_create(spec, name, namespace)
    
    # Assert
    mock_k8s.patch_namespace.assert_called_with(...)
```

### Integration Test Checklist

- [ ] Create actual policy resource
- [ ] Verify namespace is labeled
- [ ] Verify constraint is created
- [ ] Create compliant pod (should succeed)
- [ ] Create non-compliant pod (should fail)
- [ ] Update policy (regions change)
- [ ] Verify constraint is updated
- [ ] Delete policy
- [ ] Verify constraint is deleted

### Manual Testing

```bash
# Create test policy
kubectl apply -f scripts/example-policy.yaml

# Check if operator processed it
kubectl get sovereignpolicies
kubectl describe sovereignpolicy finance-eu-policy
kubectl get ns finance -o yaml | grep compliance

# Monitor operator
kubectl logs -f -n federated-sovereignty-system \
  -l app=federated-sovereignty-operator

# Test policy enforcement
kubectl run test-pod --image=nginx -n finance
# Should be rejected if no affinity

# Clean up
kubectl delete -f scripts/example-policy.yaml
```

## Code Style

### Python Style Guide

```bash
# Format code with Black
black src/ tests/ dashboard/

# Check linting
flake8 src/ tests/ dashboard/

# Type checking
mypy src/
```

### Commit Message Format

```
feat(handlers): add support for policy versioning
fix(utils): correct region label parsing
docs(readme): add troubleshooting section
test(handlers): add test for policy expiry

Format: <type>(<scope>): <subject>
Types: feat, fix, docs, test, refactor, perf, ci
```

## Performance Optimization

### Profiling

```python
import cProfile
import pstats

# Profile handlers.py
profiler = cProfile.Profile()
profiler.enable()

on_sovereign_policy_create(spec, name, namespace)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

### Memory Analysis

```bash
# Monitor memory usage
kubectl top pod -n federated-sovereignty-system -l app=federated-sovereignty-operator

# Profile memory
pip install memory-profiler
python -m memory_profiler handlers.py
```

## Debugging

### Debug Logging

```python
logger.debug("Variable value: %s", variable)
logger.debug("Policy spec: %s", json.dumps(spec, indent=2))
```

### Remote Debugging

```bash
# Port-forward to operator pod
kubectl port-forward -n federated-sovereignty-system pod/operator-pod 5678:5678

# In your IDE, attach debugger to localhost:5678
```

### Kubernetes Debugging

```bash
# Get operator pod logs
kubectl logs -n federated-sovereignty-system <pod-name>

# Get last 100 lines
kubectl logs -n federated-sovereignty-system <pod-name> --tail=100

# Follow logs
kubectl logs -f -n federated-sovereignty-system <pod-name>

# Get previous logs (if pod restarted)
kubectl logs -p -n federated-sovereignty-system <pod-name>

# Get logs with timestamps
kubectl logs -n federated-sovereignty-system <pod-name> --timestamps=true
```

## Building and Publishing

### Build Docker Image

```bash
# Build locally
docker build -t federated-sovereignty-operator:0.1.0 src/

# Tag for registry
docker tag federated-sovereignty-operator:0.1.0 \
  registry.example.com/federated-sovereignty-operator:0.1.0

# Push to registry
docker push registry.example.com/federated-sovereignty-operator:0.1.0
```

### Helm Chart

Create `helm/Chart.yaml`:

```yaml
apiVersion: v2
name: federated-sovereignty-operator
description: A Kubernetes operator for geopolitical data residency
version: 0.1.0
appVersion: 0.1.0
```

### Release Process

```bash
# Tag release
git tag -a v0.1.0 -m "Release version 0.1.0"

# Push tags
git push origin --tags

# Create GitHub release
gh release create v0.1.0 --generate-notes
```

## Contributing

### Pull Request Process

1. Create feature branch: `git checkout -b feat/my-feature`
2. Make changes and write tests
3. Run tests: `pytest tests/`
4. Format code: `black src/ tests/`
5. Run linter: `flake8 src/ tests/`
6. Commit with conventional message
7. Push and create pull request
8. Address review comments
9. Merge when approved

### Code Review Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Follows code style
- [ ] No breaking changes
- [ ] Performance considered
- [ ] Security implications reviewed
- [ ] RBAC updated if needed

## Troubleshooting Development

### Common Issues

**Issue**: Import errors when running locally
```bash
# Solution: Install in development mode
pip install -e .
```

**Issue**: Tests fail with kubeconfig not found
```bash
# Solution: Mock Kubernetes client
@patch('handlers.KubernetesClient')
def test_with_mock(mock_k8s):
    ...
```

**Issue**: OPA tests fail
```bash
# Solution: Install OPA
curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
chmod +x opa
./opa test policies/ tests/
```

---

**Development Guide Version**: 1.0  
**Last Updated**: January 2026
