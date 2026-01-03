"""
Utility functions for Kubernetes API interactions and policy management
"""

import kopf
import logging
from kubernetes import client, config
from typing import Dict, List, Optional, Any
from datetime import datetime
import yaml

logger = logging.getLogger(__name__)


class KubernetesClient:
    """Wrapper for Kubernetes API client operations"""
    
    def __init__(self):
        try:
            config.load_incluster_config()
        except config.config_exception.ConfigException:
            config.load_kube_config()
        
        self.v1 = client.CoreV1Api()
        self.custom_api = client.CustomObjectsApi()
        self.rbac_api = client.RbacAuthorizationV1Api()
    
    def patch_namespace(self, namespace: str, labels: Dict[str, str]) -> bool:
        """Patch a namespace with labels"""
        try:
            body = {
                "metadata": {
                    "labels": labels
                }
            }
            self.v1.patch_namespace(namespace, body)
            logger.info(f"Successfully patched namespace '{namespace}' with labels: {labels}")
            return True
        except client.exceptions.ApiException as e:
            logger.error(f"Failed to patch namespace '{namespace}': {e}")
            return False
    
    def create_custom_resource(self, group: str, version: str, plural: str, 
                              namespace: str, body: Dict[str, Any]) -> Optional[Dict]:
        """Create a custom resource"""
        try:
            response = self.custom_api.create_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                body=body
            )
            logger.info(f"Created custom resource {kind} in namespace {namespace}")
            return response
        except client.exceptions.ApiException as e:
            logger.error(f"Failed to create custom resource: {e}")
            return None
    
    def create_cluster_custom_resource(self, group: str, version: str, plural: str,
                                      body: Dict[str, Any]) -> Optional[Dict]:
        """Create a cluster-scoped custom resource"""
        try:
            response = self.custom_api.create_cluster_custom_object(
                group=group,
                version=version,
                plural=plural,
                body=body
            )
            logger.info(f"Created cluster custom resource {body.get('kind')}")
            return response
        except client.exceptions.ApiException as e:
            logger.error(f"Failed to create cluster custom resource: {e}")
            return None
    
    def delete_custom_resource(self, group: str, version: str, plural: str,
                              namespace: str, name: str) -> bool:
        """Delete a namespaced custom resource"""
        try:
            self.custom_api.delete_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                name=name
            )
            logger.info(f"Deleted custom resource '{name}' from namespace '{namespace}'")
            return True
        except client.exceptions.ApiException as e:
            logger.error(f"Failed to delete custom resource: {e}")
            return False
    
    def delete_cluster_custom_resource(self, group: str, version: str, plural: str,
                                      name: str) -> bool:
        """Delete a cluster-scoped custom resource"""
        try:
            self.custom_api.delete_cluster_custom_object(
                group=group,
                version=version,
                plural=plural,
                name=name
            )
            logger.info(f"Deleted cluster custom resource '{name}'")
            return True
        except client.exceptions.ApiException as e:
            logger.error(f"Failed to delete cluster custom resource: {e}")
            return False
    
    def get_namespace(self, namespace: str) -> Optional[Dict]:
        """Get namespace details"""
        try:
            return self.v1.read_namespace(namespace)
        except client.exceptions.ApiException as e:
            logger.error(f"Failed to read namespace '{namespace}': {e}")
            return None
    
    def list_custom_resources(self, group: str, version: str, plural: str,
                             namespace: str = None) -> List[Dict]:
        """List custom resources"""
        try:
            if namespace:
                response = self.custom_api.list_namespaced_custom_object(
                    group=group,
                    version=version,
                    namespace=namespace,
                    plural=plural
                )
            else:
                response = self.custom_api.list_cluster_custom_object(
                    group=group,
                    version=version,
                    plural=plural
                )
            return response.get('items', [])
        except client.exceptions.ApiException as e:
            logger.error(f"Failed to list custom resources: {e}")
            return []


def format_region_label(regions: List[str]) -> str:
    """Format regions list as comma-separated label value"""
    return ",".join(regions)


def parse_region_label(label_value: str) -> List[str]:
    """Parse regions from comma-separated label value"""
    return [r.strip() for r in label_value.split(",") if r.strip()]


def create_gatekeeper_constraint(name: str, namespace: str, regions: List[str],
                                 enforcement_action: str = "deny") -> Dict[str, Any]:
    """Generate OPA Gatekeeper Constraint resource"""
    
    return {
        "apiVersion": "constraints.gatekeeper.sh/v1beta1",
        "kind": "K8sGeoResidency",
        "metadata": {
            "name": f"geo-residency-{namespace}",
            "namespace": "gatekeeper-system"
        },
        "spec": {
            "match": {
                "namespaceSelector": {
                    "matchLabels": {
                        "compliance.gov/allowed-regions": format_region_label(regions)
                    }
                },
                "excludedNamespaces": ["kube-system", "kube-public", "gatekeeper-system"],
                "kinds": [
                    {
                        "apiGroups": [""],
                        "kinds": ["Pod"]
                    }
                ]
            },
            "parameters": {
                "allowedRegions": regions,
                "enforcement": enforcement_action
            }
        }
    }


def update_sovereign_policy_status(namespace: str, name: str, phase: str,
                                   message: str = "", constraint_created: bool = False):
    """Update the status of a SovereignPolicy resource"""
    
    client_inst = KubernetesClient()
    
    status = {
        "phase": phase,
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
        "message": message,
        "constraintCreated": constraint_created
    }
    
    try:
        client_inst.custom_api.patch_namespaced_custom_object_status(
            group="compliance.federated.io",
            version="v1alpha1",
            namespace=namespace,
            plural="sovereignpolicies",
            name=name,
            body={"status": status}
        )
        logger.info(f"Updated SovereignPolicy '{name}' status to '{phase}'")
    except client.exceptions.ApiException as e:
        logger.error(f"Failed to update SovereignPolicy status: {e}")


def is_policy_expired(policy: Dict[str, Any]) -> bool:
    """Check if a SovereignPolicy has expired"""
    expiry_str = policy.get("spec", {}).get("expiryDate")
    if not expiry_str:
        return False
    
    try:
        expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
        return datetime.utcnow() > expiry
    except (ValueError, TypeError):
        return False


def get_excluded_namespaces(policy: Dict[str, Any]) -> List[str]:
    """Get list of excluded namespaces from policy"""
    excluded = policy.get("spec", {}).get("excludedNamespaces", [])
    # Always exclude system namespaces
    system_namespaces = ["kube-system", "kube-public", "kube-node-lease", 
                        "gatekeeper-system", "federated-sovereignty-system"]
    return list(set(excluded + system_namespaces))
