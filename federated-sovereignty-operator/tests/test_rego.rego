# OPA Rego Unit Tests for Geo-Residency Policy
# Run with: opa test residency_test.rego residency.rego -v

package k8sgeoresidency

# Test: Allow pod with proper affinity
test_allow_pod_with_proper_affinity {
    pod := {
        "metadata": {
            "name": "test-pod",
            "namespace": "finance"
        },
        "spec": {
            "containers": [{"name": "app"}],
            "affinity": {
                "nodeAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": {
                        "nodeSelectorTerms": [{
                            "matchExpressions": [{
                                "key": "topology.kubernetes.io/region",
                                "operator": "In",
                                "values": ["eu-central-1"]
                            }]
                        }]
                    }
                }
            }
        }
    }
    
    input_obj := {
        "review": {
            "object": pod,
            "kind": {"kind": "Pod"}
        },
        "parameters": {"allowedRegions": ["eu-central-1", "eu-west-1"]}
    }
    
    # Should allow because region matches
    count(violation) == 0
}

# Test: Deny pod without affinity
test_deny_pod_without_affinity {
    pod := {
        "metadata": {
            "name": "test-pod",
            "namespace": "finance"
        },
        "spec": {
            "containers": [{"name": "app"}]
        }
    }
    
    input_obj := {
        "review": {
            "object": pod,
            "kind": {"kind": "Pod"}
        },
        "parameters": {"allowedRegions": ["eu-central-1"]}
    }
    
    # Should deny because no affinity specified
    count(violation) > 0
}

# Test: Allow non-Pod resources
test_allow_non_pod_resources {
    deployment := {
        "metadata": {
            "name": "test-deployment",
            "namespace": "finance"
        },
        "spec": {}
    }
    
    input_obj := {
        "review": {
            "object": deployment,
            "kind": {"kind": "Deployment"}
        }
    }
    
    # Should allow because it's not a Pod
    count(violation) == 0
}

# Test: Allow exempt namespaces
test_allow_exempt_namespaces {
    pod := {
        "metadata": {
            "name": "test-pod",
            "namespace": "kube-system"
        },
        "spec": {
            "containers": [{"name": "app"}]
        }
    }
    
    input_obj := {
        "review": {
            "object": pod,
            "kind": {"kind": "Pod"}
        },
        "parameters": {
            "allowedRegions": ["eu-central-1"],
            "exemptedNamespaces": ["kube-system"]
        }
    }
    
    # Should allow because namespace is exempt
    count(violation) == 0
}
