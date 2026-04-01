"""
Visualization Utilities for GenTwin

Helper functions for creating plots and visualizations.

Author: GenTwin Team
Date: February 2026
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List


def plot_latent_space_3d(normal_z: np.ndarray,
                         attack_z: np.ndarray,
                         attack_labels: np.ndarray,
                         title: str = "VAE Latent Space"):
    """
    Create 3D scatter plot of VAE latent space.
    
    Args:
        normal_z: Normal data latent vectors
        attack_z: Attack data latent vectors
        attack_labels: Attack severity labels
        title: Plot title
        
    Returns:
        Plotly figure
    """
    # Use first 3 dimensions for visualization
    fig = go.Figure()
    
    # Plot normal data
    fig.add_trace(go.Scatter3d(
        x=normal_z[:1000, 0],
        y=normal_z[:1000, 1],
        z=normal_z[:1000, 2],
        mode='markers',
        marker=dict(size=2, color='blue', opacity=0.5),
        name='Normal'
    ))
    
    # Plot attacks by severity
    severity_colors = {'mild': 'orange', 'moderate': 'red', 'severe': 'darkred'}
    
    for severity, color in severity_colors.items():
        mask = attack_labels == severity
        if np.any(mask):
            fig.add_trace(go.Scatter3d(
                x=attack_z[mask, 0],
                y=attack_z[mask, 1],
                z=attack_z[mask, 2],
                mode='markers',
                marker=dict(size=3, color=color, opacity=0.7),
                name=f'Attack ({severity})'
            ))
    
    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title='Latent Dim 1',
            yaxis_title='Latent Dim 2',
            zaxis_title='Latent Dim 3'
        ),
        height=600
    )
    
    return fig


def plot_sensor_timeseries(sensor_data: np.ndarray,
                           sensor_names: List[str],
                           title: str = "Sensor Readings Over Time",
                           selected_sensors: List[str] = None):
    """
    Plot sensor readings over time.
    
    Args:
        sensor_data: Array of sensor values (timesteps, n_sensors)
        sensor_names: List of sensor names
        title: Plot title
        selected_sensors: Subset of sensors to plot
        
    Returns:
        Plotly figure
    """
    if selected_sensors is None:
        # Plot first 10 sensors by default
        selected_sensors = sensor_names[:10]
    
    fig = go.Figure()
    
    for sensor in selected_sensors:
        if sensor in sensor_names:
            idx = sensor_names.index(sensor)
            fig.add_trace(go.Scatter(
                y=sensor_data[:, idx],
                mode='lines',
                name=sensor,
                line=dict(width=1)
            ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Time (seconds)',
        yaxis_title='Sensor Value (normalized)',
        height=400,
        hovermode='x unified'
    )
    
    return fig


def plot_dt_state(states: List[Dict],
                 variables: List[str] = None):
    """
    Plot Digital Twin state variables over time.
    
    Args:
        states: List of state dictionaries from DT simulation
        variables: Which state variables to plot
        
    Returns:
        Plotly figure
    """
    if variables is None:
        variables = ['LIT101', 'LIT301', 'LIT601', 'AIT201']
    
    fig = make_subplots(
        rows=len(variables), cols=1,
        subplot_titles=variables,
        vertical_spacing=0.05
    )
    
    for i, var in enumerate(variables, 1):
        values = [state.get(var, 0) for state in states]
        
        fig.add_trace(
            go.Scatter(y=values, mode='lines', name=var, showlegend=False),
            row=i, col=1
        )
        
        # Add constraint lines if applicable
        if var.startswith('LIT'):
            fig.add_hline(y=800, line_dash="dash", line_color="red", 
                         row=i, col=1, annotation_text="Min")
            fig.add_hline(y=1200, line_dash="dash", line_color="red",
                         row=i, col=1, annotation_text="Max")
    
    fig.update_layout(height=200*len(variables), title="Digital Twin State")
    fig.update_xaxes(title_text="Time (s)")
    
    return fig


def plot_sankey_diagram(gaps_df: pd.DataFrame):
    """
    Create Sankey diagram: Attack Type → Detection Status → Impact Level.
    
    Args:
        gaps_df: DataFrame of identified gaps
        
    Returns:
        Plotly figure
    """
    if gaps_df.empty:
        return go.Figure()
    
    # Define nodes
    severity_levels = ['mild', 'moderate', 'severe']
    detection_statuses = ['Detected', 'Missed']
    impact_levels = ['Low', 'Medium', 'High']
    
    all_nodes = severity_levels + detection_statuses + impact_levels
    
    # Create flows
    sources = []
    targets = []
    values = []
    
    for severity in severity_levels:
        severity_idx = all_nodes.index(severity)
        severity_data = gaps_df[gaps_df['severity_level'] == severity]
        
        for detection in detection_statuses:
            detection_idx = all_nodes.index(detection)
            
            if detection == 'Detected':
                count = len(severity_data[severity_data['detection_rate'] >= 30])
            else:
                count = len(severity_data[severity_data['detection_rate'] < 30])
            
            if count > 0:
                sources.append(severity_idx)
                targets.append(detection_idx)
                values.append(count)
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            label=all_nodes,
            color=['lightblue', 'orange', 'red', 'green', 'darkred', 'yellow', 'orange', 'red']
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values
        )
    )])
    
    fig.update_layout(
        title="Attack Flow: Severity → Detection → Impact",
        height=400
    )
    
    return fig


def plot_reconstruction_error_histogram(normal_errors: np.ndarray,
                                       attack_errors: np.ndarray):
    """
    Plot histogram of VAE reconstruction errors.
    
    Args:
        normal_errors: Reconstruction errors for normal data
        attack_errors: Reconstruction errors for attacks
        
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=normal_errors,
        name='Normal',
        opacity=0.7,
        marker_color='blue',
        nbinsx=50
    ))
    
    fig.add_trace(go.Histogram(
        x=attack_errors,
        name='Attacks',
        opacity=0.7,
        marker_color='red',
        nbinsx=50
    ))
    
    fig.update_layout(
        title='VAE Reconstruction Error Distribution',
        xaxis_title='Reconstruction Error (MSE)',
        yaxis_title='Count',
        barmode='overlay',
        height=400
    )
    
    return fig


def plot_confusion_matrix(y_true: np.ndarray,
                         y_pred: np.ndarray,
                         title: str = "Confusion Matrix"):
    """
    Plot confusion matrix.
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        title: Plot title
        
    Returns:
        Matplotlib figure
    """
    from sklearn.metrics import confusion_matrix
    
    cm = confusion_matrix(y_true, y_pred)
    
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,
                xticklabels=['Normal', 'Attack'],
                yticklabels=['Normal', 'Attack'])
    ax.set_title(title)
    ax.set_ylabel('True Label')
    ax.set_xlabel('Predicted Label')
    
    return fig


def plot_detection_comparison(baseline_results: Dict):
    """
    Bar chart comparing detector performance.
    
    Args:
        baseline_results: Results from baseline evaluator
        
    Returns:
        Plotly figure
    """
    detectors = list(baseline_results.keys())
    metrics = ['precision', 'recall', 'f1_score']
    
    fig = go.Figure()
    
    for metric in metrics:
        values = [baseline_results[d][metric] for d in detectors]
        fig.add_trace(go.Bar(
            name=metric.capitalize().replace('_', ' '),
            x=detectors,
            y=values
        ))
    
    fig.update_layout(
        title='Baseline Detector Performance Comparison',
        xaxis_title='Detector',
        yaxis_title='Score',
        barmode='group',
        height=400
    )
    
    return fig
