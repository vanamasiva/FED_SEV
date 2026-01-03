"""
Interactive Dashboard for Federated Sovereignty Policy Management
Built with Streamlit for real-time visualization and policy management
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from kubernetes import client, config
from datetime import datetime
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Federated Sovereignty Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .status-active { color: green; }
    .status-failed { color: red; }
    .status-pending { color: orange; }
    .status-expired { color: gray; }
    </style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_k8s_client():
    """Get Kubernetes API client"""
    try:
        config.load_incluster_config()
    except config.config_exception.ConfigException:
        config.load_kube_config()
    return client.CustomObjectsApi(), client.CoreV1Api()


def get_sovereign_policies():
    """Fetch all SovereignPolicy resources"""
    try:
        custom_api, _ = get_k8s_client()
        policies = custom_api.list_cluster_custom_object(
            group="compliance.federated.io",
            version="v1alpha1",
            plural="sovereignpolicies"
        )
        return policies.get("items", [])
    except Exception as e:
        logger.error(f"Error fetching policies: {e}")
        st.error(f"Failed to fetch policies: {e}")
        return []


def get_namespace_labels(namespace_name: str):
    """Get compliance labels for a namespace"""
    try:
        _, v1 = get_k8s_client()
        ns = v1.read_namespace(namespace_name)
        labels = ns.metadata.labels or {}
        return {k: v for k, v in labels.items() if k.startswith("compliance.gov")}
    except Exception as e:
        logger.error(f"Error fetching namespace labels: {e}")
        return {}


def get_pods_in_namespace(namespace_name: str):
    """Get pods in a namespace"""
    try:
        _, v1 = get_k8s_client()
        pods = v1.list_namespaced_pod(namespace_name)
        return pods.items
    except Exception as e:
        logger.error(f"Error fetching pods: {e}")
        return []


def create_region_map(regions: list):
    """Create folium map showing allowed regions"""
    
    # Region coordinates (central points)
    region_coords = {
        "us-east-1": [39.0, -98.0],
        "us-east-2": [40.4173, -82.9071],
        "us-west-1": [38.8, -120.0],
        "us-west-2": [45.5951, -121.1786],
        "eu-central-1": [50.1109, 8.6821],
        "eu-west-1": [53.4129, -8.2439],
        "eu-west-2": [51.5074, -0.1278],
        "ap-southeast-1": [1.3521, 103.8198],
        "ap-southeast-2": [-33.8688, 151.2093],
        "ap-northeast-1": [35.6762, 139.6503],
        "ca-central-1": [56.1304, -106.3468],
        "sa-east-1": [-23.5505, -46.6333],
    }
    
    # Create map centered on Europe
    m = folium.Map(
        location=[54.5260, 15.2551],
        zoom_start=3,
        tiles="OpenStreetMap"
    )
    
    # Add markers for allowed regions
    for region in regions:
        if region in region_coords:
            coords = region_coords[region]
            folium.CircleMarker(
                location=coords,
                radius=15,
                popup=region,
                color="green",
                fill=True,
                fillColor="green",
                fillOpacity=0.7,
                weight=2
            ).add_to(m)
    
    return m


def display_policy_detail(policy):
    """Display detailed view of a policy"""
    spec = policy.get("spec", {})
    status = policy.get("status", {})
    metadata = policy.get("metadata", {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Target Namespace",
            spec.get("targetNamespace", "N/A")
        )
    
    with col2:
        st.metric(
            "Status",
            status.get("phase", "Unknown")
        )
    
    with col3:
        st.metric(
            "Enforcement",
            spec.get("enforcementAction", "deny").upper()
        )
    
    # Allowed regions
    st.subheader("📍 Allowed Regions")
    regions = spec.get("allowedRegions", [])
    st.write(", ".join(regions))
    
    # Map visualization
    st.subheader("🗺️ Geographical Coverage")
    m = create_region_map(regions)
    st_folium(m, width=700, height=500)
    
    # Policy details
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Policy Info")
        st.write(f"**Name:** {metadata.get('name')}")
        st.write(f"**Created:** {metadata.get('creationTimestamp', 'N/A')}")
        if spec.get("expiryDate"):
            st.write(f"**Expires:** {spec.get('expiryDate')}")
    
    with col2:
        st.subheader("📊 Status Details")
        st.write(f"**Last Updated:** {status.get('lastUpdated', 'N/A')}")
        st.write(f"**Constraint Created:** {status.get('constraintCreated', False)}")
        if status.get("message"):
            st.write(f"**Message:** {status.get('message')}")
    
    # Namespace compliance
    st.subheader("✅ Namespace Compliance")
    target_ns = spec.get("targetNamespace")
    if target_ns:
        labels = get_namespace_labels(target_ns)
        
        if labels:
            labels_df = pd.DataFrame(list(labels.items()), columns=["Label", "Value"])
            st.dataframe(labels_df, use_container_width=True)
        else:
            st.info("No compliance labels found on namespace")
    
    # Pods in namespace
    st.subheader("🚀 Workloads")
    pods = get_pods_in_namespace(target_ns)
    
    if pods:
        pods_data = []
        for pod in pods:
            has_affinity = bool(pod.spec.affinity)
            pods_data.append({
                "Pod": pod.metadata.name,
                "Status": pod.status.phase,
                "Node Affinity": "✓" if has_affinity else "✗",
                "Created": pod.metadata.creation_timestamp
            })
        
        pods_df = pd.DataFrame(pods_data)
        st.dataframe(pods_df, use_container_width=True)
    else:
        st.info("No pods found in this namespace")


def main():
    """Main application logic"""
    
    st.markdown('<h1 class="main-header">🛡️ Federated Sovereignty Dashboard</h1>', unsafe_allow_html=True)
    st.write("Policy-As-Code Framework for Enforcing Geopolitical Data Residency")
    st.divider()
    
    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Select View",
            ["Overview", "Policies", "Compliance", "Audit Log"]
        )
    
    # Overview page
    if page == "Overview":
        st.header("📊 Overview")
        
        policies = get_sovereign_policies()
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Policies", len(policies))
        
        with col2:
            active = sum(1 for p in policies if p.get("status", {}).get("phase") == "Active")
            st.metric("Active Policies", active)
        
        with col3:
            failed = sum(1 for p in policies if p.get("status", {}).get("phase") == "Failed")
            st.metric("Failed Policies", failed, delta=None)
        
        with col4:
            regions = set()
            for p in policies:
                regions.update(p.get("spec", {}).get("allowedRegions", []))
            st.metric("Protected Regions", len(regions))
        
        st.divider()
        
        # Recent policies
        if policies:
            st.subheader("📝 Recent Policies")
            for policy in policies[:5]:
                with st.expander(f"🔹 {policy['metadata']['name']} - {policy['spec']['targetNamespace']}"):
                    display_policy_detail(policy)
    
    # Policies page
    elif page == "Policies":
        st.header("📋 All Policies")
        
        policies = get_sovereign_policies()
        
        if policies:
            # Create DataFrame for display
            policies_data = []
            for p in policies:
                spec = p.get("spec", {})
                status = p.get("status", {})
                policies_data.append({
                    "Name": p["metadata"]["name"],
                    "Namespace": spec.get("targetNamespace"),
                    "Regions": ", ".join(spec.get("allowedRegions", [])),
                    "Status": status.get("phase", "Unknown"),
                    "Enforcement": spec.get("enforcementAction", "deny"),
                    "Created": p["metadata"].get("creationTimestamp", "N/A")
                })
            
            df = pd.DataFrame(policies_data)
            st.dataframe(df, use_container_width=True)
            
            # Detail view
            st.subheader("Policy Details")
            selected_policy_name = st.selectbox(
                "Select a policy to view details",
                [p["metadata"]["name"] for p in policies]
            )
            
            selected_policy = next(
                (p for p in policies if p["metadata"]["name"] == selected_policy_name),
                None
            )
            
            if selected_policy:
                display_policy_detail(selected_policy)
        else:
            st.info("No SovereignPolicy resources found")
    
    # Compliance page
    elif page == "Compliance":
        st.header("✅ Compliance Status")
        
        policies = get_sovereign_policies()
        
        if policies:
            compliance_issues = []
            
            for policy in policies:
                spec = policy.get("spec", {})
                target_ns = spec.get("targetNamespace")
                allowed_regions = spec.get("allowedRegions", [])
                
                if target_ns:
                    pods = get_pods_in_namespace(target_ns)
                    for pod in pods:
                        has_affinity = bool(pod.spec.affinity)
                        if not has_affinity:
                            compliance_issues.append({
                                "Namespace": target_ns,
                                "Pod": pod.metadata.name,
                                "Issue": "Missing node affinity",
                                "Severity": "High"
                            })
            
            if compliance_issues:
                issues_df = pd.DataFrame(compliance_issues)
                st.warning(f"⚠️ Found {len(compliance_issues)} compliance issues")
                st.dataframe(issues_df, use_container_width=True)
            else:
                st.success("✅ All policies are compliant!")
        else:
            st.info("No policies to check")
    
    # Audit log page
    elif page == "Audit Log":
        st.header("📜 Audit Log")
        st.info("Audit log functionality coming soon")
        st.write("This section will display detailed logs of policy changes and enforcement actions.")
    
    # Footer
    st.divider()
    st.caption("Federated Sovereignty Operator v0.1.0 | Last updated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()
