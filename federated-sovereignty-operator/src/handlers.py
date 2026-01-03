"""
Kopf handlers for SovereignPolicy resource lifecycle management
"""

import kopf
import logging
from typing import Dict, Any
from datetime import datetime
from utils import (
    KubernetesClient,
    format_region_label,
    create_gatekeeper_constraint,
    update_sovereign_policy_status,
    is_policy_expired,
    get_excluded_namespaces
)

logger = logging.getLogger(__name__)

# Configure Kopf logging
kopf.configure(defaults={"logging": {"level": "info"}})


@kopf.on.event(
    "compliance.federated.io",
    "v1alpha1",
    "sovereignpolicies",
    labels={"managed-by": "federated-sovereignty"},
    annotations={"description": "Geopolitical Data Residency Policy"}
)
def log_policy_event(event, **kwargs):
    """Log events for debugging purposes"""
    logger.debug(f"Policy event: {event}")


@kopf.on.create(
    "compliance.federated.io",
    "v1alpha1",
    "sovereignpolicies"
)
def on_sovereign_policy_create(spec, name, namespace, **kwargs):
    """
    Handler for SovereignPolicy creation
    
    Actions:
    1. Validate the policy
    2. Patch target namespace with compliance labels
    3. Create OPA Gatekeeper Constraint
    4. Update policy status
    """
    
    logger.info(f"Creating SovereignPolicy '{name}' in namespace '{namespace}'")
    
    try:
        # Extract spec
        target_namespace = spec.get("targetNamespace")
        allowed_regions = spec.get("allowedRegions", [])
        enforcement_action = spec.get("enforcementAction", "deny")
        description = spec.get("description", "")
        
        # Validate required fields
        if not target_namespace or not allowed_regions:
            msg = "SovereignPolicy must have targetNamespace and allowedRegions"
            logger.error(msg)
            update_sovereign_policy_status(namespace, name, "Failed", msg)
            return
        
        # Check if policy is already expired
        if is_policy_expired(kwargs.get("body", {})):
            msg = "Policy has expired"
            logger.warning(msg)
            update_sovereign_policy_status(namespace, name, "Expired", msg)
            return
        
        # Initialize Kubernetes client
        k8s = KubernetesClient()
        
        # Step 1: Verify target namespace exists
        target_ns = k8s.get_namespace(target_namespace)
        if not target_ns:
            msg = f"Target namespace '{target_namespace}' does not exist"
            logger.error(msg)
            update_sovereign_policy_status(namespace, name, "Failed", msg)
            return
        
        # Step 2: Patch namespace with compliance labels
        labels = {
            "compliance.gov/allowed-regions": format_region_label(allowed_regions),
            "compliance.gov/policy-name": name,
            "compliance.gov/policy-namespace": namespace,
            "compliance.gov/enforcement-action": enforcement_action
        }
        
        if not k8s.patch_namespace(target_namespace, labels):
            msg = f"Failed to patch namespace '{target_namespace}'"
            logger.error(msg)
            update_sovereign_policy_status(namespace, name, "Failed", msg)
            return
        
        logger.info(f"Successfully patched namespace '{target_namespace}' with compliance labels")
        
        # Step 3: Create Gatekeeper Constraint
        constraint = create_gatekeeper_constraint(
            name=name,
            namespace=target_namespace,
            regions=allowed_regions,
            enforcement_action=enforcement_action
        )
        
        constraint_created = k8s.create_cluster_custom_resource(
            group="constraints.gatekeeper.sh",
            version="v1beta1",
            plural="k8sgeoresidencies",
            body=constraint
        )
        
        if not constraint_created:
            msg = f"Warning: Failed to create Gatekeeper constraint for '{target_namespace}'"
            logger.warning(msg)
            # Don't fail the policy creation, continue with partial success
            update_sovereign_policy_status(
                namespace, name, "Active", 
                f"{msg} but namespace patched successfully",
                constraint_created=False
            )
        else:
            logger.info(f"Successfully created Gatekeeper constraint for '{target_namespace}'")
            update_sovereign_policy_status(
                namespace, name, "Active",
                f"Sovereignty enforcement active for namespace '{target_namespace}' restricted to regions {allowed_regions}",
                constraint_created=True
            )
        
        logger.info(f"✓ SovereignPolicy '{name}' created successfully")
        
    except Exception as e:
        logger.error(f"Error creating SovereignPolicy: {e}", exc_info=True)
        update_sovereign_policy_status(namespace, name, "Failed", str(e))
        raise


@kopf.on.update(
    "compliance.federated.io",
    "v1alpha1",
    "sovereignpolicies"
)
def on_sovereign_policy_update(spec, name, namespace, old, new, **kwargs):
    """
    Handler for SovereignPolicy updates
    
    Actions:
    1. Detect changes in allowedRegions or enforcement action
    2. Update namespace labels
    3. Update or recreate Gatekeeper Constraint
    4. Update policy status
    """
    
    logger.info(f"Updating SovereignPolicy '{name}' in namespace '{namespace}'")
    
    try:
        old_spec = old.get("spec", {})
        new_spec = new.get("spec", {})
        
        target_namespace = new_spec.get("targetNamespace")
        old_allowed_regions = old_spec.get("allowedRegions", [])
        new_allowed_regions = new_spec.get("allowedRegions", [])
        enforcement_action = new_spec.get("enforcementAction", "deny")
        
        # Check for significant changes
        regions_changed = set(old_allowed_regions) != set(new_allowed_regions)
        
        if not regions_changed:
            logger.info(f"No significant changes detected in SovereignPolicy '{name}'")
            return
        
        # Initialize Kubernetes client
        k8s = KubernetesClient()
        
        # Update namespace labels
        labels = {
            "compliance.gov/allowed-regions": format_region_label(new_allowed_regions),
            "compliance.gov/policy-name": name,
            "compliance.gov/policy-namespace": namespace,
            "compliance.gov/enforcement-action": enforcement_action,
            "compliance.gov/updated-at": datetime.utcnow().isoformat() + "Z"
        }
        
        if not k8s.patch_namespace(target_namespace, labels):
            msg = f"Failed to update namespace '{target_namespace}'"
            logger.error(msg)
            update_sovereign_policy_status(namespace, name, "Failed", msg)
            return
        
        # Delete old constraint
        k8s.delete_cluster_custom_resource(
            group="constraints.gatekeeper.sh",
            version="v1beta1",
            plural="k8sgeoresidencies",
            name=f"geo-residency-{target_namespace}"
        )
        
        # Create new constraint
        constraint = create_gatekeeper_constraint(
            name=name,
            namespace=target_namespace,
            regions=new_allowed_regions,
            enforcement_action=enforcement_action
        )
        
        k8s.create_cluster_custom_resource(
            group="constraints.gatekeeper.sh",
            version="v1beta1",
            plural="k8sgeoresidencies",
            body=constraint
        )
        
        update_sovereign_policy_status(
            namespace, name, "Active",
            f"Policy updated. Regions changed from {old_allowed_regions} to {new_allowed_regions}",
            constraint_created=True
        )
        
        logger.info(f"✓ SovereignPolicy '{name}' updated successfully")
        
    except Exception as e:
        logger.error(f"Error updating SovereignPolicy: {e}", exc_info=True)
        update_sovereign_policy_status(namespace, name, "Failed", str(e))
        raise


@kopf.on.delete(
    "compliance.federated.io",
    "v1alpha1",
    "sovereignpolicies"
)
def on_sovereign_policy_delete(spec, name, namespace, **kwargs):
    """
    Handler for SovereignPolicy deletion
    
    Actions:
    1. Delete Gatekeeper Constraint
    2. Remove compliance labels from namespace (optional, for clean state)
    3. Log deletion
    """
    
    logger.info(f"Deleting SovereignPolicy '{name}' from namespace '{namespace}'")
    
    try:
        target_namespace = spec.get("targetNamespace")
        
        if not target_namespace:
            logger.warning(f"Could not determine target namespace for SovereignPolicy '{name}'")
            return
        
        # Initialize Kubernetes client
        k8s = KubernetesClient()
        
        # Delete Gatekeeper Constraint
        constraint_deleted = k8s.delete_cluster_custom_resource(
            group="constraints.gatekeeper.sh",
            version="v1beta1",
            plural="k8sgeoresidencies",
            name=f"geo-residency-{target_namespace}"
        )
        
        if constraint_deleted:
            logger.info(f"Deleted associated Gatekeeper constraint")
        else:
            logger.warning(f"Could not delete Gatekeeper constraint (may not exist)")
        
        logger.info(f"✓ SovereignPolicy '{name}' deleted successfully")
        logger.info(f"Note: Namespace '{target_namespace}' labels were preserved for audit trail")
        
    except Exception as e:
        logger.error(f"Error deleting SovereignPolicy: {e}", exc_info=True)
        raise


@kopf.timer(
    "compliance.federated.io",
    "v1alpha1",
    "sovereignpolicies",
    interval=3600  # Run every hour
)
def check_policy_expiry(spec, name, namespace, body, **kwargs):
    """
    Timer handler to check for expired policies
    Updates policy status to Expired when expiry date is reached
    """
    
    if is_policy_expired(body):
        logger.warning(f"SovereignPolicy '{name}' has expired")
        update_sovereign_policy_status(
            namespace, name, "Expired",
            f"Policy expired on {body.get('spec', {}).get('expiryDate', 'unknown')}"
        )


@kopf.on.event(
    "compliance.federated.io",
    "v1alpha1",
    "sovereignpolicies",
    value={"status.phase": "Failed"}
)
def alert_on_failure(spec, name, namespace, body, **kwargs):
    """
    Event handler to alert on policy failures
    In production, this would integrate with alerting systems (Prometheus, PagerDuty, etc.)
    """
    
    logger.error(
        f"SovereignPolicy '{name}' in namespace '{namespace}' is in Failed state. "
        f"Message: {body.get('status', {}).get('message', 'Unknown error')}"
    )
    # TODO: Integrate with alerting system
    # send_alert(f"SovereignPolicy {name} failed", ...)
