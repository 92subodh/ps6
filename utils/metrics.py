"""
Metrics and Evaluation Utilities

Helper functions for calculating evaluation metrics.

Author: GenTwin Team
Date: February 2026
"""

import numpy as np
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    accuracy_score, roc_auc_score, confusion_matrix
)
from typing import Dict, Tuple


def calculate_detection_metrics(y_true: np.ndarray,
                                y_pred: np.ndarray,
                                y_scores: np.ndarray = None) -> Dict:
    """
    Calculate comprehensive detection metrics.
    
    Args:
        y_true: True labels (0=normal, 1=anomaly)
        y_pred: Predicted labels
        y_scores: Prediction scores (optional, for AUC)
        
    Returns:
        Dictionary of metrics
    """
    metrics = {
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, zero_division=0),
        'recall': recall_score(y_true, y_pred, zero_division=0),
        'f1_score': f1_score(y_true, y_pred, zero_division=0),
    }
    
    # Calculate confusion matrix components
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    
    metrics.update({
        'true_positives': int(tp),
        'false_positives': int(fp),
        'true_negatives': int(tn),
        'false_negatives': int(fn),
        'false_positive_rate': fp / (fp + tn) if (fp + tn) > 0 else 0,
        'true_positive_rate': tp / (tp + fn) if (tp + fn) > 0 else 0,
    })
    
    # AUC if scores provided
    if y_scores is not None and len(np.unique(y_true)) > 1:
        try:
            metrics['auc_roc'] = roc_auc_score(y_true, y_scores)
        except:
            metrics['auc_roc'] = None
    
    return metrics


def calculate_severity_metrics(y_true: np.ndarray,
                              y_pred: np.ndarray,
                              severity_labels: np.ndarray) -> Dict:
    """
    Calculate metrics broken down by attack severity.
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        severity_labels: Severity level for each sample
        
    Returns:
        Dictionary of metrics per severity level
    """
    severity_metrics = {}
    
    for severity in np.unique(severity_labels):
        mask = severity_labels == severity
        
        if np.sum(mask) > 0:
            severity_metrics[severity] = calculate_detection_metrics(
                y_true[mask],
                y_pred[mask]
            )
    
    return severity_metrics


def calculate_gap_statistics(gaps_df) -> Dict:
    """
    Calculate statistics about identified security gaps.
    
    Args:
        gaps_df: DataFrame of identified gaps
        
    Returns:
        Dictionary of statistics
    """
    if gaps_df.empty:
        return {
            'total_gaps': 0,
            'mean_impact': 0.0,
            'mean_detection_rate': 0.0
        }
    
    stats = {
        'total_gaps': len(gaps_df),
        'mean_impact': float(gaps_df['impact_score'].mean()),
        'median_impact': float(gaps_df['impact_score'].median()),
        'max_impact': float(gaps_df['impact_score'].max()),
        'mean_detection_rate': float(gaps_df['detection_rate'].mean()),
        'gap_types': gaps_df['gap_type'].value_counts().to_dict(),
        'severity_distribution': gaps_df['severity_level'].value_counts().to_dict(),
    }
    
    # Critical gaps (impact > 85, detection < 10%)
    critical = gaps_df[
        (gaps_df['impact_score'] > 85) &
        (gaps_df['detection_rate'] < 10)
    ]
    stats['critical_gaps'] = len(critical)
    
    return stats


def estimate_risk_reduction(gaps_df,
                           recommendations: list,
                           baseline_coverage: float = 0.60) -> Dict:
    """
    Estimate risk reduction from implementing recommendations.
    
    Args:
        gaps_df: DataFrame of identified gaps
        recommendations: List of recommendations
        baseline_coverage: Current detection coverage (0-1)
        
    Returns:
        Dictionary with risk estimates
    """
    total_gaps = len(gaps_df)
    
    if total_gaps == 0:
        return {
            'current_coverage': baseline_coverage * 100,
            'estimated_new_coverage': baseline_coverage * 100,
            'risk_reduction': 0.0,
            'gaps_closed': 0
        }
    
    # Estimate gaps closed per recommendation
    estimated_closed = 0
    for rec in recommendations:
        # Extract numeric percentage from expected_improvement
        improvement_str = rec.get('expected_improvement', '0%')
        # Extract first number from string (handles "60%" or "60% reduction...")
        import re
        match = re.search(r'(\d+\.?\d*)%?', improvement_str)
        improvement_pct = float(match.group(1)) if match else 0.0
        improvement = improvement_pct / 100
        gaps_for_type = rec.get('count', 0)
        estimated_closed += gaps_for_type * improvement
    
    new_coverage = baseline_coverage + (estimated_closed / total_gaps) * (1 - baseline_coverage)
    risk_reduction = ((new_coverage - baseline_coverage) / (1 - baseline_coverage)) * 100
    
    return {
        'current_coverage': baseline_coverage * 100,
        'estimated_new_coverage': new_coverage * 100,
        'risk_reduction': risk_reduction,
        'gaps_closed': int(estimated_closed),
        'gaps_remaining': total_gaps - int(estimated_closed)
    }


def summarize_results(impact_results: Dict,
                     baseline_results: Dict,
                     gap_analysis: Dict) -> str:
    """
    Generate text summary of all results.
    
    Args:
        impact_results: Impact analysis results
        baseline_results: Baseline detector results
        gap_analysis: Gap analysis results
        
    Returns:
        Formatted summary string
    """
    summary = "="*60 + "\n"
    summary += "GENTWIN ANALYSIS SUMMARY\n"
    summary += "="*60 + "\n\n"
    
    # Impact analysis
    summary += "Attack Impact Analysis:\n"
    summary += f"  Total attacks analyzed: {impact_results['summary']['total_attacks']}\n"
    summary += f"  Mean impact score: {impact_results['summary']['mean_impact']:.2f}\n"
    summary += f"  High-impact attacks: {impact_results['summary']['high_impact_count']}\n\n"
    
    # Baseline performance
    summary += "Baseline Detector Performance:\n"
    for detector, metrics in baseline_results.items():
        summary += f"  {detector}:\n"
        summary += f"    Precision: {metrics['precision']:.3f}\n"
        summary += f"    Recall: {metrics['recall']:.3f}\n"
        summary += f"    F1-Score: {metrics['f1_score']:.3f}\n"
    summary += "\n"
    
    # Gap analysis
    if gap_analysis and 'summary' in gap_analysis:
        summary += "Security Gaps Identified:\n"
        summary += f"  Total gaps: {gap_analysis['summary']['total_gaps']}\n"
        if gap_analysis['summary']['total_gaps'] > 0:
            summary += f"  Gap types: {gap_analysis['summary']['gap_type_distribution']}\n"
            summary += f"  Recommendations: {len(gap_analysis.get('recommendations', []))}\n"
    
    summary += "\n" + "="*60
    
    return summary
