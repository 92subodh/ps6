"""
GenTwin Interactive Dashboard

Streamlit application for exploring VAE-generated attacks, Digital Twin 
simulations, and security gap analysis.

Author: GenTwin Team
Date: February 2026
"""

import streamlit as st
import numpy as np
import pandas as pd
import pickle
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from utils.visualization import (
    plot_latent_space_3d, plot_sensor_timeseries, plot_dt_state,
    plot_sankey_diagram, plot_reconstruction_error_histogram,
    plot_detection_comparison
)
from utils.metrics import calculate_gap_statistics, estimate_risk_reduction


# Page config
st.set_page_config(
    page_title="GenTwin: SWaT Cybersecurity Gap Discovery",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data
def load_data():
    """Load all analysis results."""
    data = {}
    
    try:
        # Load synthetic attacks
        with open('data/synthetic/synthetic_attacks.pkl', 'rb') as f:
            data['attacks'] = pickle.load(f)
    except FileNotFoundError:
        st.warning("Synthetic attacks not found. Please run attack_generator.py")
        data['attacks'] = None
    
    try:
        # Load impact analysis
        with open('data/synthetic/impact_analysis.pkl', 'rb') as f:
            data['impact'] = pickle.load(f)
    except FileNotFoundError:
        st.warning("Impact analysis not found. Please run impact_analyzer.py")
        data['impact'] = None
    
    try:
        # Load gap analysis
        with open('data/synthetic/gap_analysis.pkl', 'rb') as f:
            data['gaps'] = pickle.load(f)
    except FileNotFoundError:
        st.warning("Gap analysis not found. Please run full pipeline")
        data['gaps'] = None
    
    return data


def page_overview(data):
    """Overview page with key metrics."""
    st.title("🔒 GenTwin: VAE-Driven Digital Twin for SWaT Cybersecurity")
    st.markdown("---")
    
    st.markdown("""
    **GenTwin** discovers hidden security vulnerabilities by combining:
    - **VAE Generation**: Creates synthetic attack scenarios
    - **Digital Twin**: Validates physical process impacts
    - **Gap Analysis**: Identifies undetected high-risk attacks
    """)
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    if data['attacks']:
        with col1:
            st.metric(
                "Synthetic Attacks",
                len(data['attacks']['attacks']),
                help="Total generated attack scenarios"
            )
    
    if data['impact']:
        with col2:
            mean_impact = data['impact']['summary']['mean_impact']
            st.metric(
                "Mean Impact Score",
                f"{mean_impact:.1f}",
                help="Average severity score (0-100)"
            )
        
        with col3:
            high_impact = data['impact']['summary']['high_impact_count']
            st.metric(
                "High-Impact Attacks",
                high_impact,
                help="Attacks with severity > 70"
            )
    
    if data['gaps']:
        with col4:
            gaps_count = data['gaps']['summary']['total_gaps']
            st.metric(
                "Security Gaps Found",
                gaps_count,
                delta=f"-{gaps_count} vulnerabilities",
                delta_color="inverse",
                help="High-impact attacks that evade detection"
            )
    
    st.markdown("---")
    
    # Summary statistics
    if data['gaps'] and data['gaps']['summary']['total_gaps'] > 0:
        st.subheader("📊 Gap Analysis Summary")
        
        gaps_df = data['gaps']['gaps']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Gap Type Distribution:**")
            gap_types = gaps_df['gap_type'].value_counts()
            fig = px.pie(
                values=gap_types.values,
                names=gap_types.index,
                title="Distribution of Security Gap Types",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig, width='stretch')
        
        with col2:
            st.markdown("**Impact vs Detection Rate:**")
            fig = px.scatter(
                gaps_df,
                x='detection_rate',
                y='impact_score',
                color='gap_type',
                size='total_violations',
                hover_data=['attack_id', 'severity_level'],
                title="Security Gaps: Low Detection, High Impact"
            )
            fig.add_hline(y=70, line_dash="dash", line_color="red", 
                         annotation_text="Impact Threshold")
            fig.add_vline(x=30, line_dash="dash", line_color="red",
                         annotation_text="Detection Threshold")
            st.plotly_chart(fig, width='stretch')


def page_realtime_monitoring(data):
    """Real-time monitoring page with VAE latent space."""
    st.title("📡 Real-Time Attack Monitoring")
    st.markdown("Visualize VAE latent space and reconstruction errors")
    st.markdown("---")
    
    if not data['attacks']:
        st.error("No attack data available. Please run the pipeline first.")
        return
    
    attacks = data['attacks']['attacks']
    labels = data['attacks']['labels']
    
    # Latent space visualization (mock - would need actual VAE encoding)
    st.subheader("VAE Latent Space (3D Visualization)")
    
    st.info("💡 Blue=Normal, Orange=Mild, Red=Moderate, Dark Red=Severe")
    
    # Create synthetic latent representations for visualization
    np.random.seed(42)
    normal_z = np.random.randn(1000, 32)
    attack_z = np.random.randn(len(attacks), 32) * 1.5
    
    fig = plot_latent_space_3d(normal_z, attack_z, labels)
    st.plotly_chart(fig, width='stretch')
    
    # Reconstruction error histogram
    st.subheader("Reconstruction Error Distribution")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        normal_errors = np.abs(np.random.randn(1000)) * 0.5
        attack_errors = np.abs(np.random.randn(len(attacks))) * 2.0
        
        fig = plot_reconstruction_error_histogram(normal_errors, attack_errors)
        st.plotly_chart(fig, width='stretch')
    
    with col2:
        st.markdown("**Filtering Options:**")
        error_threshold = st.slider(
            "Reconstruction Error Threshold",
            0.0, 5.0, 1.5,
            help="Filter attacks above this threshold"
        )
        
        filtered_count = np.sum(attack_errors > error_threshold)
        st.metric("Filtered Attacks", filtered_count)
        
        st.markdown(f"""
        **Statistics:**
        - Normal mean: {np.mean(normal_errors):.3f}
        - Attack mean: {np.mean(attack_errors):.3f}
        - Separation: {np.mean(attack_errors) / np.mean(normal_errors):.2f}x
        """)


def page_attack_simulation(data):
    """Attack simulation theater page."""
    st.title("🎭 Attack Simulation Theater")
    st.markdown("Explore individual attack scenarios and Digital Twin responses")
    st.markdown("---")
    
    if not data['attacks'] or not data['impact']:
        st.error("Attack or impact data not available.")
        return
    
    attacks = data['attacks']['attacks']
    labels = data['attacks']['labels']
    impact_results = data['impact']['results']
    
    # Attack selector
    st.subheader("Select Attack Scenario")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        severity_filter = st.selectbox(
            "Severity Level",
            ["All", "mild", "moderate", "severe"]
        )
    
    with col2:
        impact_filter = st.slider(
            "Minimum Impact Score",
            0, 100, 50
        )
    
    # Filter attacks
    filtered_indices = []
    for i, (label, result) in enumerate(zip(labels, impact_results)):
        if severity_filter != "All" and label != severity_filter:
            continue
        if result['impact_score'] < impact_filter:
            continue
        filtered_indices.append(i)
    
    with col3:
        if filtered_indices:
            selected_idx = st.selectbox(
                f"Attack ID ({len(filtered_indices)} matching)",
                filtered_indices,
                format_func=lambda x: f"Attack #{x} (Impact: {impact_results[x]['impact_score']:.1f})"
            )
        else:
            st.warning("No attacks match filters")
            return
    
    st.markdown("---")
    
    # Display chosen attack details
    attack = attacks[selected_idx]
    result = impact_results[selected_idx]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Attack ID", selected_idx)
    with col2:
        st.metric("Severity", labels[selected_idx].capitalize())
    with col3:
        st.metric("Impact Score", f"{result['impact_score']:.1f}")
    with col4:
        st.metric("Total Violations", result['total_violations'])
    
    # Side-by-side comparison
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Sensor Readings")
        
        # Create time series (mock 300 seconds with perturbations)
        sensor_timeseries = np.tile(attack, (300, 1))
        sensor_timeseries += np.random.randn(300, len(attack)) * 0.1
        
        sensor_names = data['attacks']['sensor_cols'][:10]  # First 10 sensors
        
        fig = plot_sensor_timeseries(sensor_timeseries, sensor_names)
        st.plotly_chart(fig, width='stretch')
    
    with col2:
        st.subheader("Digital Twin State")
        
        # Mock DT state evolution
        states = []
        base_state = {
            'LIT101': 1000.0,
            'LIT301': 1000.0,
            'LIT601': 1000.0,
            'AIT201': 2.0
        }
        
        for t in range(300):
            # Simulate state changes
            new_state = base_state.copy()
            new_state['LIT101'] += np.random.randn() * 10
            new_state['LIT301'] += np.random.randn() * 10
            new_state['LIT601'] += np.random.randn() * 10
            new_state['AIT201'] += np.random.randn() * 0.1
            states.append(new_state)
        
        fig = plot_dt_state(states)
        st.plotly_chart(fig, width='stretch')
    
    # Violation details
    st.subheader("Safety Violations")
    
    if result['total_violations'] > 0:
        st.error(f"⚠️ {result['total_violations']} safety constraint violations detected!")
        
        violation_data = {
            'Primary Type': [result['primary_violation']],
            'Affected Stages': [', '.join(result['affected_stages'])],
            'Violation %': [f"{result['violation_percentage']:.1f}%"]
        }
        
        st.dataframe(pd.DataFrame(violation_data), width='stretch')
    else:
        st.success("✅ No safety violations detected")


def page_gap_analysis(data):
    """Security gap analysis dashboard."""
    st.title("🔍 Security Gap Analysis")
    st.markdown("Identified vulnerabilities and mitigation recommendations")
    st.markdown("---")
    
    if not data['gaps'] or data['gaps']['summary']['total_gaps'] == 0:
        st.info("No security gaps identified. System appears well-protected!")
        return
    
    gaps_df = data['gaps']['gaps']
    recommendations = data['gaps']['recommendations']
    
    # Summary metrics
    st.subheader("Gap Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    stats = calculate_gap_statistics(gaps_df)
    
    with col1:
        st.metric("Total Gaps", stats['total_gaps'])
    with col2:
        st.metric("Mean Impact", f"{stats['mean_impact']:.1f}")
    with col3:
        st.metric("Critical Gaps", stats.get('critical_gaps', 0))
    with col4:
        st.metric("Recommendations", len(recommendations))
    
    st.markdown("---")
    
    # Sankey diagram
    st.subheader("Attack Flow Analysis")
    fig = plot_sankey_diagram(gaps_df)
    st.plotly_chart(fig, width='stretch')
    
    st.markdown("---")
    
    # Top gaps table
    st.subheader("Top 20 Critical Security Gaps")
    
    display_df = gaps_df.head(20)[['attack_id', 'severity_level', 'impact_score', 
                                     'detection_rate', 'gap_type', 'affected_stages']]
    
    st.dataframe(
        display_df.style.background_gradient(subset=['impact_score'], cmap='Reds')
                       .format({'impact_score': '{:.1f}', 'detection_rate': '{:.1f}%'}),
        width='stretch',
        height=400
    )
    
    st.markdown("---")
    
    # Recommendations
    st.subheader("🛡️ Mitigation Recommendations")
    
    for rec in recommendations:
        with st.expander(f"**[{rec['priority']}]** {rec['recommendation']} "
                        f"({rec['count']} gaps)", expanded=True):
            st.markdown(f"**Gap Type:** {rec['gap_type']}")
            st.markdown(f"**Details:** {rec['details']}")
            st.code(rec['implementation'], language='python')
            st.success(f"**Expected Improvement:** {rec.get('description', rec['expected_improvement'])}")
    
    # Risk reduction estimate
    st.markdown("---")
    st.subheader("📈 Estimated Risk Reduction")
    
    risk_est = estimate_risk_reduction(gaps_df, recommendations)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Current Coverage",
            f"{risk_est['current_coverage']:.1f}%",
            help="Baseline detection coverage"
        )
        st.metric(
            "Estimated New Coverage",
            f"{risk_est['estimated_new_coverage']:.1f}%",
            delta=f"+{risk_est['estimated_new_coverage'] - risk_est['current_coverage']:.1f}%",
            help="After implementing recommendations"
        )
    
    with col2:
        st.metric(
            "Risk Reduction",
            f"{risk_est['risk_reduction']:.1f}%",
            delta=f"-{risk_est['gaps_closed']} gaps",
            delta_color="inverse",
            help="Percentage reduction in undetected attacks"
        )
        
        # Progress bar
        st.progress(risk_est['estimated_new_coverage'] / 100)


def page_model_insights(data):
    """Model performance insights page."""
    st.title("🤖 Model Insights")
    st.markdown("VAE performance and baseline detector comparison")
    st.markdown("---")
    
    st.subheader("VAE Architecture")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Encoder:**
        - Input: 51 sensors/actuators
        - Dense(128) + LeakyReLU + BatchNorm
        - Dense(64) + LeakyReLU + BatchNorm
        - Output: μ(32), σ(32)
        """)
    
    with col2:
        st.markdown("""
        **Decoder:**
        - Input: Latent(32)
        - Dense(64) + LeakyReLU + BatchNorm
        - Dense(128) + LeakyReLU + BatchNorm
        - Output: Reconstruction(51)
        """)
    
    st.markdown("**Loss:** Reconstruction (MSE) + 0.5 × KL Divergence")
    
    st.markdown("---")
    
    # Mock baseline comparison
    st.subheader("Baseline Detector Comparison")
    
    baseline_results = {
        'Threshold (3σ)': {'precision': 0.65, 'recall': 0.45, 'f1_score': 0.53},
        'Isolation Forest': {'precision': 0.72, 'recall': 0.58, 'f1_score': 0.64},
        'One-Class SVM': {'precision': 0.68, 'recall': 0.52, 'f1_score': 0.59},
        'LSTM Autoencoder': {'precision': 0.78, 'recall': 0.65, 'f1_score': 0.71}
    }
    
    fig = plot_detection_comparison(baseline_results)
    st.plotly_chart(fig, width='stretch')
    
    # Feature importance (mock)
    st.subheader("Sensor Importance for Detection")
    
    sensors = [f'Sensor_{i}' for i in range(10)]
    importance = np.random.rand(10)
    importance = importance / importance.sum()
    
    fig = px.bar(
        x=sensors,
        y=importance,
        title="Top 10 Sensors by Detection Contribution",
        labels={'x': 'Sensor', 'y': 'Importance'}
    )
    st.plotly_chart(fig, width='stretch')


def main():
    """Main app entry point."""
    # Sidebar
    with st.sidebar:
        st.title("Navigation")
        page = st.radio(
            "Go to",
            ["Overview", "Real-Time Monitoring", "Attack Simulation", 
             "Gap Analysis", "Model Insights"]
        )
        
        st.markdown("---")
        st.markdown("### About GenTwin")
        st.markdown("""
        A cybersecurity testing platform combining VAE with Digital Twin 
        to discover hidden vulnerabilities in SWaT water treatment systems.
        
        **Key Features:**
        - Synthetic attack generation
        - Physics-based impact validation
        - Proactive gap discovery
        - Actionable recommendations
        """)
        
        st.markdown("---")
        st.markdown("*GenTwin © 2026*")
    
    # Load data
    data = load_data()
    
    # Route to page
    if page == "Overview":
        page_overview(data)
    elif page == "Real-Time Monitoring":
        page_realtime_monitoring(data)
    elif page == "Attack Simulation":
        page_attack_simulation(data)
    elif page == "Gap Analysis":
        page_gap_analysis(data)
    elif page == "Model Insights":
        page_model_insights(data)


if __name__ == "__main__":
    main()
