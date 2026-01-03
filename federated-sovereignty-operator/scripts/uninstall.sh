#!/bin/bash
# Uninstall script for Federated Sovereignty Operator

set -e

echo "🗑️  Uninstalling Federated Sovereignty Operator..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Delete operator deployment
echo -e "${YELLOW}Deleting operator deployment...${NC}"
kubectl delete deployment federated-sovereignty-operator -n federated-sovereignty-system --ignore-not-found
kubectl delete service federated-sovereignty-operator -n federated-sovereignty-system --ignore-not-found

# Delete RBAC
echo -e "${YELLOW}Deleting RBAC...${NC}"
kubectl delete clusterrolebinding federated-sovereignty-operator --ignore-not-found
kubectl delete clusterrole federated-sovereignty-operator --ignore-not-found
kubectl delete serviceaccount federated-sovereignty-operator -n federated-sovereignty-system --ignore-not-found

# Delete constraints
echo -e "${YELLOW}Deleting constraints...${NC}"
kubectl delete constraints k8sgeoresidencies --all --ignore-not-found

# Delete CRD
echo -e "${YELLOW}Deleting CRD...${NC}"
kubectl delete crd sovereignpolicies.compliance.federated.io --ignore-not-found

# Delete namespace
echo -e "${YELLOW}Deleting namespace...${NC}"
kubectl delete namespace federated-sovereignty-system --ignore-not-found

echo -e "${GREEN}✅ Federated Sovereignty Operator uninstalled successfully${NC}"
