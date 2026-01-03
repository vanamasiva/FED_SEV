#!/bin/bash
# Deployment script for Federated Sovereignty Operator

set -e

echo "🚀 Deploying Federated Sovereignty Operator..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    command -v kubectl &> /dev/null || { echo -e "${RED}kubectl not found${NC}"; exit 1; }
    command -v helm &> /dev/null || { echo -e "${RED}helm not found${NC}"; exit 1; }
    
    echo -e "${GREEN}✓ Prerequisites met${NC}"
}

# Create namespace
create_namespace() {
    echo -e "${YELLOW}Creating namespace...${NC}"
    kubectl create namespace federated-sovereignty-system --dry-run=client -o yaml | kubectl apply -f -
    echo -e "${GREEN}✓ Namespace created${NC}"
}

# Install CRD
install_crd() {
    echo -e "${YELLOW}Installing CRD...${NC}"
    kubectl apply -f ../deploy/crds/sovereignty_policy_crd.yaml
    echo -e "${GREEN}✓ CRD installed${NC}"
}

# Build and push Docker image
build_image() {
    echo -e "${YELLOW}Building Docker image...${NC}"
    
    REGISTRY=${1:-localhost:5000}
    IMAGE_NAME="federated-sovereignty-operator"
    IMAGE_TAG="0.1.0"
    IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    
    docker build -t ${IMAGE} ../src/
    
    if [ "${REGISTRY}" != "localhost:5000" ]; then
        docker push ${IMAGE}
    fi
    
    echo -e "${GREEN}✓ Image built: ${IMAGE}${NC}"
}

# Install Gatekeeper (if not present)
install_gatekeeper() {
    echo -e "${YELLOW}Installing OPA Gatekeeper...${NC}"
    
    if kubectl get namespace gatekeeper-system &> /dev/null; then
        echo -e "${GREEN}✓ Gatekeeper already installed${NC}"
    else
        helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
        helm install gatekeeper/gatekeeper --name-template=gatekeeper --namespace gatekeeper-system --create-namespace
        echo -e "${GREEN}✓ Gatekeeper installed${NC}"
    fi
}

# Deploy operator
deploy_operator() {
    echo -e "${YELLOW}Deploying operator...${NC}"
    
    kubectl apply -f ../deploy/operator/rbac.yaml
    kubectl apply -f ../deploy/operator/deployment.yaml
    
    # Wait for deployment
    echo -e "${YELLOW}Waiting for operator to be ready...${NC}"
    kubectl rollout status deployment/federated-sovereignty-operator -n federated-sovereignty-system --timeout=300s
    
    echo -e "${GREEN}✓ Operator deployed${NC}"
}

# Deploy Gatekeeper constraint
deploy_constraint() {
    echo -e "${YELLOW}Deploying Gatekeeper constraint...${NC}"
    
    kubectl apply -f ../deploy/gatekeeper/template_residency.yaml
    kubectl apply -f ../deploy/gatekeeper/sync.yaml
    
    echo -e "${GREEN}✓ Constraint deployed${NC}"
}

# Test deployment
test_deployment() {
    echo -e "${YELLOW}Testing deployment...${NC}"
    
    # Check if operator pod is running
    OPERATOR_POD=$(kubectl get pods -n federated-sovereignty-system -l app=federated-sovereignty-operator -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -z "$OPERATOR_POD" ]; then
        echo -e "${RED}✗ Operator pod not found${NC}"
        return 1
    fi
    
    # Check logs
    echo -e "${YELLOW}Operator logs:${NC}"
    kubectl logs -n federated-sovereignty-system $OPERATOR_POD --tail=20
    
    echo -e "${GREEN}✓ Deployment test passed${NC}"
}

# Main execution
main() {
    check_prerequisites
    create_namespace
    install_crd
    
    # Ask for Docker registry
    read -p "Enter Docker registry (default: localhost:5000): " REGISTRY
    REGISTRY=${REGISTRY:-localhost:5000}
    
    build_image $REGISTRY
    install_gatekeeper
    deploy_operator
    deploy_constraint
    test_deployment
    
    echo -e "${GREEN}✅ Federated Sovereignty Operator deployed successfully!${NC}"
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Create a SovereignPolicy:"
    echo "   kubectl apply -f ../examples/example-policy.yaml"
    echo ""
    echo "2. Start the dashboard:"
    echo "   streamlit run ../dashboard/app.py"
    echo ""
    echo "3. Monitor the operator:"
    echo "   kubectl logs -f -n federated-sovereignty-system -l app=federated-sovereignty-operator"
}

main
