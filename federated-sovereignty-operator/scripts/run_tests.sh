#!/bin/bash
# Run tests for Federated Sovereignty Operator

set -e

echo "🧪 Running tests..."

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd "$(dirname "$0")/../tests"

# Run Python tests
echo -e "${YELLOW}Running Python unit tests...${NC}"
python -m pytest test_handlers.py -v --tb=short || {
    echo -e "${RED}Python tests failed${NC}"
    exit 1
}

echo -e "${GREEN}✓ Python tests passed${NC}"

# Run Rego tests (if OPA is installed)
if command -v opa &> /dev/null; then
    echo -e "${YELLOW}Running Rego policy tests...${NC}"
    opa test test_rego.rego ../policies/residency.rego -v || {
        echo -e "${RED}Rego tests failed${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Rego tests passed${NC}"
else
    echo -e "${YELLOW}⚠️  OPA not found, skipping Rego tests${NC}"
    echo "Install OPA with: curl https://openpolicyagent.org/downloads/latest/opa_linux_amd64 -o opa && chmod +x opa"
fi

echo -e "${GREEN}✅ All tests passed!${NC}"
