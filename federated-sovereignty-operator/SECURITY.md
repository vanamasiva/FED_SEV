# Federated Sovereignty Operator - Security & Compliance

## Security Architecture

### Threat Model

| Threat | Mitigation |
|--------|-----------|
| Unauthorized policy modification | RBAC, audit logs, webhook validation |
| Bypassing residency enforcement | OPA Gatekeeper webhooks, immutable constraints |
| Operator compromise | Non-root user, minimal RBAC, pod security policies |
| Data exfiltration | Network policies, egress controls, encryption |
| Denial of service | Resource limits, rate limiting, health checks |

## Access Control (RBAC)

### ServiceAccount Permissions

```yaml
# Minimal required permissions
- SovereignPolicy CRD: get, list, watch, create, update, patch, delete, status
- Namespaces: get, list, watch, patch
- OPA Constraints: get, list, watch, create, update, patch, delete
- Pods: get, list, watch (read-only)
- Events: create, patch
```

### User Roles

```yaml
# Policy Creator Role
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: sovereign-policy-creator
rules:
- apiGroups: ["compliance.federated.io"]
  resources: ["sovereignpolicies"]
  verbs: ["create", "update", "patch", "delete"]

# Policy Viewer Role
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: sovereign-policy-viewer
rules:
- apiGroups: ["compliance.federated.io"]
  resources: ["sovereignpolicies"]
  verbs: ["get", "list", "watch"]
```

## Data Protection

### Encryption

```yaml
# Enable etcd encryption
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
    - sovereignpolicies
    providers:
    - aescbc:
        keys:
        - name: key1
          secret: <base64-encoded-32-byte-key>
```

### Secrets Management

- API tokens: Managed via ServiceAccount
- No secrets stored in configmaps or environment variables
- All credentials passed via Kubernetes secrets

### Audit Logging

```yaml
# Enable Kubernetes audit
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: RequestResponse
  omitStages:
  - RequestReceived
  resources:
  - group: compliance.federated.io
    resources: ["sovereignpolicies"]
  namespaces:
  - federated-sovereignty-system
```

## Network Security

### Network Policies

```yaml
# Restrict operator networking
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: federated-sovereignty-operator
spec:
  podSelector:
    matchLabels:
      app: federated-sovereignty-operator
  policyTypes:
  - Ingress
  - Egress
  
  # Ingress: Allow health checks only
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: federated-sovereignty-system
    ports:
    - protocol: TCP
      port: 8080
  
  # Egress: Allow Kubernetes API and DNS only
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443  # Kubernetes API
    - protocol: UDP
      port: 53   # DNS
```

### TLS Configuration

```yaml
# Secure operator communication
apiVersion: v1
kind: Secret
metadata:
  name: operator-tls
  namespace: federated-sovereignty-system
type: kubernetes.io/tls
data:
  tls.crt: <base64-cert>
  tls.key: <base64-key>
```

## Pod Security

### Pod Security Policy

```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: federated-sovereignty-restricted
spec:
  privileged: false
  allowPrivilegeEscalation: false
  
  requiredDropCapabilities:
    - ALL
  
  allowedCapabilities: []
  
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
  
  hostNetwork: false
  hostIPC: false
  hostPID: false
  
  runAsUser:
    rule: 'MustRunAsNonRoot'
  
  runAsGroup:
    rule: 'MustRunAs'
    ranges:
      - min: 1000
        max: 65535
  
  seLinux:
    rule: 'MustRunAs'
    seLinuxOptions:
      level: "s0:c123,c456"
  
  fsGroup:
    rule: 'MustRunAs'
    ranges:
      - min: 1000
        max: 65535
  
  readOnlyRootFilesystem: true
```

## Vulnerability Management

### Regular Updates

```bash
# Check for dependency vulnerabilities
pip install safety
safety check requirements.txt

# Scan Docker image
docker scan federated-sovereignty-operator:0.1.0

# Use Snyk for continuous monitoring
snyk monitor --file=requirements.txt
```

### Supply Chain Security

```yaml
# Signed container images
apiVersion: v1
kind: Pod
metadata:
  name: operator
spec:
  containers:
  - name: operator
    image: registry.example.com/federated-sovereignty-operator@sha256:abc123...
    # Use digest instead of tag for immutability
```

## Compliance Frameworks

### GDPR Compliance

- **Data Residency**: Enforced via geopolitical policies
- **Audit Trail**: Kubernetes audit logs + operator logs
- **Right to Deletion**: Policies can be deleted cleanly
- **Data Minimization**: Operator has minimal required permissions

### SOC 2 Compliance

- **Logging**: Comprehensive audit trails
- **Access Control**: RBAC with least privilege
- **Encryption**: In-transit and at-rest
- **Incident Response**: Automated alerts and monitoring

### HIPAA Compliance

- **Access Controls**: Strict RBAC enforcement
- **Audit Controls**: Complete audit logging
- **Integrity Controls**: API validation and signatures
- **Transmission Security**: TLS 1.2+

## Security Scanning

### Container Image Scanning

```bash
# Trivy vulnerability scanner
trivy image federated-sovereignty-operator:0.1.0

# Grype vulnerability scanner
grype federated-sovereignty-operator:0.1.0

# Build-time scanning
docker build --security-opt seccomp:unconfined \
  -t federated-sovereignty-operator:0.1.0 src/
```

### Code Security Analysis

```bash
# Bandit for Python security
bandit -r src/ -f json > security-report.json

# SAST scanning with Semgrep
semgrep --config=p/security-audit src/

# Dependency check
python -m pip_audit -r requirements.txt
```

### SBOM (Software Bill of Materials)

```bash
# Generate SBOM
syft federated-sovereignty-operator:0.1.0 -o json > sbom.json

# Sign SBOM
cosign sign-blob --key cosign.key sbom.json > sbom.json.sig
```

## Incident Response

### Security Incident Procedures

```bash
# 1. Detect: Monitor for violations
kubectl logs -n federated-sovereignty-system \
  -l app=federated-sovereignty-operator | grep -i "error\|violation"

# 2. Analyze: Examine the policy
kubectl describe sovereignpolicy <name>

# 3. Contain: Set enforcement to dryrun
kubectl patch sovereignpolicy <name> \
  --type merge -p '{"spec":{"enforcementAction":"dryrun"}}'

# 4. Investigate: Review audit logs
kubectl get events -n federated-sovereignty-system

# 5. Remediate: Update or delete policy
kubectl delete sovereignpolicy <name>

# 6. Verify: Confirm enforcement
kubectl get pods -o yaml | grep -i affinity
```

### Security Escalation Contacts

Establish incident response contacts:

```
Security Lead: security@example.com
On-Call: escalation@example.com
Legal: legal@example.com
```

## Secrets Management

### Using Sealed Secrets

```bash
# Encrypt sensitive data
echo -n "my-secret" | \
  kubeseal -o yaml > sealed-secret.yaml

# Apply sealed secret
kubectl apply -f sealed-secret.yaml

# Operator reads decrypted secret at runtime
```

### External Secret Management

```yaml
# Using External Secrets Operator
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: operator-secrets
spec:
  provider:
    vault:
      server: "https://vault.example.com"
      path: "secret"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "federated-sovereignty"
```

## Security Testing

### Penetration Testing

```bash
# Test RBAC restrictions
kubectl auth can-i create pods \
  --as=system:serviceaccount:federated-sovereignty-system:federated-sovereignty-operator
# Should be False

# Test API validation
kubectl apply -f - <<EOF
apiVersion: compliance.federated.io/v1alpha1
kind: SovereignPolicy
metadata:
  name: invalid
spec:
  # Missing required fields
EOF
# Should be rejected
```

### Chaos Engineering

```bash
# Test operator resilience
kubectl delete pod -n federated-sovereignty-system \
  -l app=federated-sovereignty-operator

# Verify self-healing
kubectl get pods -n federated-sovereignty-system

# Test constraint enforcement while OPA is down
# Verify behavior and recovery
```

## Compliance Checklist

- [ ] RBAC configured with least privilege
- [ ] Network policies enabled
- [ ] Pod security policies applied
- [ ] TLS enabled for API communication
- [ ] Audit logging enabled
- [ ] Container images signed
- [ ] Vulnerability scanning in place
- [ ] Secrets properly managed
- [ ] Incident response procedures documented
- [ ] Regular security updates scheduled
- [ ] SBOM generated and maintained
- [ ] Security scanning integrated in CI/CD

---

**Security & Compliance Guide Version**: 1.0  
**Last Updated**: January 2026  
**Classification**: Internal
