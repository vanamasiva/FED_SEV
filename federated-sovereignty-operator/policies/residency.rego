package k8sgeoresidency

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# Violation message template
violation[msg] {
    container := input_containers[_]
    not container_affinity_match(container)
    msg := sprintf(
        "Pod '%s' in namespace '%s' violates geopolitical residency policy. " +
        "Required regions: %v. Pod must have nodeAffinity rule for topology.kubernetes.io/region",
        [input.review.object.metadata.name, input.review.object.metadata.namespace, allowed_regions]
    )
}

# Get all containers (including init containers)
input_containers[c] {
    containers := object.get(input.review.object.spec, "containers", [])
    c := containers[_]
}

input_containers[c] {
    init_containers := object.get(input.review.object.spec, "initContainers", [])
    c := init_containers[_]
}

# Check if container affinity matches allowed regions
container_affinity_match(container) {
    affinity := object.get(input.review.object.spec, "affinity", {})
    node_affinity := object.get(affinity, "nodeAffinity", {})
    required_terms := object.get(node_affinity, "requiredDuringSchedulingIgnoredDuringExecution", {})
    
    node_selector_terms := object.get(required_terms, "nodeSelectorTerms", [])
    node_selector_terms != []
    
    term := node_selector_terms[_]
    match_expressions := object.get(term, "matchExpressions", [])
    
    region_expr := match_expressions[_]
    region_expr.key == "topology.kubernetes.io/region"
    region_expr.operator == "In"
    
    values := region_expr.values
    values != null
    
    # Check if at least one pod value is in allowed regions
    pod_region := values[_]
    pod_region in allowed_regions
}

# Get allowed regions from namespace label
allowed_regions[region] {
    namespace_name := input.review.object.metadata.namespace
    namespace := data.kubernetes.namespaces[namespace_name]
    labels := object.get(namespace, "metadata.labels", {})
    regions_label := object.get(labels, "compliance.gov/allowed-regions", "")
    regions_label != ""
    
    # Parse comma-separated regions
    regions := split(regions_label, ",")
    region := trim(regions[_], " ")
}

# Namespace is exempt from constraint
exempt_namespace {
    namespace_name := input.review.object.metadata.namespace
    exempt_list := object.get(input, "parameters.exemptedNamespaces", [])
    namespace_name in exempt_list
}

# Skip validation for non-Pod resources
skip_validation {
    input.review.kind.kind != "Pod"
}

# Allow if exempt or skip conditions are met
allow {
    exempt_namespace
}

allow {
    skip_validation
}

# Allow if no residency constraint exists
allow {
    not allowed_regions[_]
}
