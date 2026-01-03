"""
Pytest unit tests for Federated Sovereignty Operator handlers
"""

import pytest
import kopf
from unittest.mock import MagicMock, patch, call
from handlers import (
    on_sovereign_policy_create,
    on_sovereign_policy_update,
    on_sovereign_policy_delete
)
from utils import (
    format_region_label,
    parse_region_label,
    create_gatekeeper_constraint,
    is_policy_expired
)
from datetime import datetime, timedelta


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_format_region_label(self):
        """Test region label formatting"""
        regions = ["us-east-1", "us-west-2", "eu-central-1"]
        result = format_region_label(regions)
        assert result == "us-east-1,us-west-2,eu-central-1"
    
    def test_parse_region_label(self):
        """Test region label parsing"""
        label = "us-east-1,us-west-2,eu-central-1"
        result = parse_region_label(label)
        assert result == ["us-east-1", "us-west-2", "eu-central-1"]
    
    def test_parse_region_label_with_spaces(self):
        """Test region label parsing with spaces"""
        label = "us-east-1, us-west-2, eu-central-1"
        result = parse_region_label(label)
        assert result == ["us-east-1", "us-west-2", "eu-central-1"]
    
    def test_create_gatekeeper_constraint(self):
        """Test Gatekeeper constraint generation"""
        constraint = create_gatekeeper_constraint(
            name="test-policy",
            namespace="finance",
            regions=["eu-central-1", "eu-west-1"],
            enforcement_action="deny"
        )
        
        assert constraint["apiVersion"] == "constraints.gatekeeper.sh/v1beta1"
        assert constraint["kind"] == "K8sGeoResidency"
        assert constraint["spec"]["parameters"]["allowedRegions"] == ["eu-central-1", "eu-west-1"]
        assert constraint["spec"]["parameters"]["enforcement"] == "deny"
    
    def test_is_policy_expired_not_set(self):
        """Test expiry check when no expiry date is set"""
        policy = {"spec": {}}
        assert not is_policy_expired(policy)
    
    def test_is_policy_expired_future_date(self):
        """Test expiry check with future date"""
        future_date = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"
        policy = {"spec": {"expiryDate": future_date}}
        assert not is_policy_expired(policy)
    
    def test_is_policy_expired_past_date(self):
        """Test expiry check with past date"""
        past_date = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
        policy = {"spec": {"expiryDate": past_date}}
        assert is_policy_expired(policy)


class TestHandlers:
    """Test Kopf handlers"""
    
    @patch('handlers.KubernetesClient')
    @patch('handlers.update_sovereign_policy_status')
    def test_on_sovereign_policy_create_success(self, mock_update_status, mock_k8s_class):
        """Test successful policy creation"""
        # Setup mocks
        mock_k8s = MagicMock()
        mock_k8s_class.return_value = mock_k8s
        mock_k8s.get_namespace.return_value = {"metadata": {"name": "finance"}}
        mock_k8s.patch_namespace.return_value = True
        mock_k8s.create_cluster_custom_resource.return_value = {"kind": "K8sGeoResidency"}
        
        spec = {
            "targetNamespace": "finance",
            "allowedRegions": ["eu-central-1", "eu-west-1"],
            "enforcementAction": "deny"
        }
        
        on_sovereign_policy_create(spec, "test-policy", "default")
        
        # Verify namespace was patched
        mock_k8s.patch_namespace.assert_called()
        
        # Verify constraint was created
        mock_k8s.create_cluster_custom_resource.assert_called()
        
        # Verify status was updated
        mock_update_status.assert_called_with(
            "default", "test-policy", "Active",
            pytest.approx("Sovereignty enforcement active..."),
            constraint_created=True
        )
    
    @patch('handlers.KubernetesClient')
    @patch('handlers.update_sovereign_policy_status')
    def test_on_sovereign_policy_create_missing_namespace(self, mock_update_status, mock_k8s_class):
        """Test policy creation with missing target namespace"""
        mock_k8s = MagicMock()
        mock_k8s_class.return_value = mock_k8s
        mock_k8s.get_namespace.return_value = None  # Namespace doesn't exist
        
        spec = {
            "targetNamespace": "nonexistent",
            "allowedRegions": ["eu-central-1"]
        }
        
        on_sovereign_policy_create(spec, "test-policy", "default")
        
        # Verify status was updated to Failed
        mock_update_status.assert_called()
        call_args = mock_update_status.call_args
        assert call_args[0][2] == "Failed"  # phase = Failed
    
    @patch('handlers.KubernetesClient')
    @patch('handlers.update_sovereign_policy_status')
    def test_on_sovereign_policy_delete_success(self, mock_update_status, mock_k8s_class):
        """Test successful policy deletion"""
        mock_k8s = MagicMock()
        mock_k8s_class.return_value = mock_k8s
        mock_k8s.delete_cluster_custom_resource.return_value = True
        
        spec = {"targetNamespace": "finance"}
        
        on_sovereign_policy_delete(spec, "test-policy", "default")
        
        # Verify constraint was deleted
        mock_k8s.delete_cluster_custom_resource.assert_called()


class TestRegoPolicies:
    """Test Rego policy logic"""
    
    def test_rego_syntax_valid(self):
        """Verify Rego syntax is valid by importing"""
        # This is a placeholder; actual Rego testing requires a Rego interpreter
        # In production, use conftest (OPA's testing tool)
        pass


@pytest.fixture
def sample_sovereign_policy():
    """Fixture for sample SovereignPolicy"""
    return {
        "apiVersion": "compliance.federated.io/v1alpha1",
        "kind": "SovereignPolicy",
        "metadata": {
            "name": "finance-eu-policy",
            "namespace": "default"
        },
        "spec": {
            "targetNamespace": "finance",
            "allowedRegions": ["eu-central-1", "eu-west-1"],
            "enforcementAction": "deny",
            "description": "EU data residency requirement for finance department"
        }
    }


@pytest.fixture
def sample_pod():
    """Fixture for sample Pod with proper affinity"""
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "finance-app",
            "namespace": "finance"
        },
        "spec": {
            "containers": [
                {
                    "name": "app",
                    "image": "myapp:latest"
                }
            ],
            "affinity": {
                "nodeAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": {
                        "nodeSelectorTerms": [
                            {
                                "matchExpressions": [
                                    {
                                        "key": "topology.kubernetes.io/region",
                                        "operator": "In",
                                        "values": ["eu-central-1"]
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        }
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
