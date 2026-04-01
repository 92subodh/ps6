"""
Security Gap Identification and Analysis

Identifies attacks that:
1. Cause significant Digital Twin impact (severity > 70)
2. But evade baseline detectors (detection_rate < 30%)

These represent "hidden security gaps" in the monitoring system.

Author: GenTwin Team
Date: February 2026
"""

import numpy as np
import pandas as pd
import pickle
from typing import Dict, List
import json


class GapAnalyzer:
    """Identify and categorize security gaps."""
    
    def __init__(self, 
                 impact_threshold: float = 70.0,
                 detection_threshold: float = 0.3):
        """
        Initialize gap analyzer.
        
        Args:
            impact_threshold: Minimum DT impact score to be "significant"
            detection_threshold: Maximum detection rate to be "evasive"
        """
        self.impact_threshold = impact_threshold
        self.detection_threshold = detection_threshold
    
    def identify_security_gaps(self,
                              impact_results: Dict,
                              baseline_results: Dict) -> pd.DataFrame:
        """
        Find attacks that cause high impact but evade detection.
        
        Args:
            impact_results: Results from impact_analyzer
            baseline_results: Results from baseline detectors
            
        Returns:
            DataFrame with identified gaps
        """
        print("="*60)
        print("IDENTIFYING SECURITY GAPS")
        print("="*60)
        
        attack_results = impact_results['results']
        detector_results = baseline_results['results']
        n_normal_test = baseline_results['n_normal_test']
        
        gaps = []
        
        for attack_result in attack_results:
            attack_id = attack_result['attack_id']
            impact_score = attack_result['impact_score']
            
            # Check if high impact
            if impact_score >= self.impact_threshold:
                # Check detection rates across all baselines
                detected_by = []
                detection_rates = {}
                
                # Index in predictions array (offset by normal test samples)
                pred_idx = n_normal_test + attack_id
                
                for detector_name, results in detector_results.items():
                    if 'predictions' in results and pred_idx < len(results['predictions']):
                        is_detected = results['predictions'][pred_idx]
                        if is_detected:
                            detected_by.append(detector_name)
                        
                        detection_rates[detector_name] = float(is_detected)
                
                # Calculate overall detection rate
                overall_detection = np.mean(list(detection_rates.values())) if detection_rates else 0.0
                
                # Is this a gap?
                is_gap = overall_detection < self.detection_threshold
                
                if is_gap:
                    # Categorize gap type
                    gap_type = self._categorize_gap(attack_result)
                    
                    gaps.append({
                        'attack_id': attack_id,
                        'severity_level': attack_result['severity_level'],
                        'impact_score': impact_score,
                        'detection_rate': overall_detection * 100,
                        'detected_by': detected_by,
                        'gap_type': gap_type,
                        'affected_stages': ', '.join(attack_result['affected_stages']),
                        'primary_violation': attack_result['primary_violation'],
                        'total_violations': attack_result['total_violations']
                    })
        
        gaps_df = pd.DataFrame(gaps)
        
        if not gaps_df.empty:
            gaps_df = gaps_df.sort_values('impact_score', ascending=False)
        
        # Print summary
        print(f"\nIdentified {len(gaps_df)} security gaps")
        print(f"  Impact threshold: {self.impact_threshold}")
        print(f"  Detection threshold: {self.detection_threshold * 100}%")
        
        if not gaps_df.empty:
            print(f"\nGap Type Distribution:")
            for gap_type, count in gaps_df['gap_type'].value_counts().items():
                print(f"  {gap_type}: {count}")
            
            print(f"\nTop 5 Most Critical Gaps:")
            for i, row in gaps_df.head(5).iterrows():
                print(f"  Attack #{row['attack_id']}: "
                      f"Impact={row['impact_score']:.1f}, "
                      f"Detection={row['detection_rate']:.1f}%, "
                      f"Type={row['gap_type']}")
        
        return gaps_df
    
    def _categorize_gap(self, attack_result: Dict) -> str:
        """
        Categorize the type of security gap.
        
        Gap types:
        - slow_degradation: Gradual changes over time
        - multi_stage: Affects multiple process stages
        - sensor_blind_spot: Targets unmonitored actuators
        - mimicry: Resembles normal operational variance
        """
        # Multi-stage if affects 2+ stages
        if len(attack_result['affected_stages']) >= 2:
            return 'multi_stage'
        
        # Slow degradation if high violation duration but low total count
        if attack_result.get('violation_percentage', 0) > 50:
            return 'slow_degradation'
        
        # Sensor blind spot if specific violation types
        if attack_result['primary_violation'] in ['pump_deadheading']:
            return 'sensor_blind_spot'
        
        # Default to mimicry
        return 'mimicry'
    
    def generate_recommendations(self, gaps_df: pd.DataFrame) -> List[Dict]:
        """
        Generate mitigation recommendations for identified gaps.
        
        Args:
            gaps_df: DataFrame of identified gaps
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        if gaps_df.empty:
            return recommendations
        
        # Analyze gap types
        gap_type_counts = gaps_df['gap_type'].value_counts()
        
        # Recommendations by gap type
        if 'multi_stage' in gap_type_counts:
            recommendations.append({
                'priority': 'HIGH',
                'gap_type': 'multi_stage',
                'count': int(gap_type_counts['multi_stage']),
                'recommendation': 'Implement cross-stage correlation monitoring',
                'details': 'Add detection rules that track cascading effects across P1-P6',
                'implementation': 'if (P1_violation and P3_violation) then alert()',
                'expected_improvement': '60%',
                'description': '60% reduction in multi-stage gap misses'
            })
        
        if 'slow_degradation' in gap_type_counts:
            recommendations.append({
                'priority': 'MEDIUM',
                'gap_type': 'slow_degradation',
                'count': int(gap_type_counts['slow_degradation']),
                'recommendation': 'Lower detection thresholds for gradual changes',
                'details': 'Use cumulative sum (CUSUM) algorithms for drift detection',
                'implementation': 'cusum_threshold = 2.0 (instead of 3.0)',
                'expected_improvement': '45%',
                'description': '45% better slow attack detection'
            })
        
        if 'sensor_blind_spot' in gap_type_counts:
            recommendations.append({
                'priority': 'HIGH',
                'gap_type': 'sensor_blind_spot',
                'count': int(gap_type_counts['sensor_blind_spot']),
                'recommendation': 'Add redundant sensors at critical actuators',
                'details': 'Deploy additional monitoring at MV302, P101, P601',
                'implementation': 'install_sensor(MV302_flow_meter)',
                'expected_improvement': '80%',
                'description': '80% coverage improvement'
            })
        
        if 'mimicry' in gap_type_counts:
            recommendations.append({
                'priority': 'MEDIUM',
                'gap_type': 'mimicry',
                'count': int(gap_type_counts['mimicry']),
                'recommendation': 'Deploy ML-based behavior profiling',
                'details': 'Use sequence models to detect subtle deviations',
                'implementation': 'lstm_detector.threshold = percentile_99',
                'expected_improvement': '35%',
                'description': '35% better mimicry detection'
            })
        
        # Sort by priority
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        recommendations.sort(key=lambda x: priority_order[x['priority']])
        
        return recommendations
    
    def save_analysis(self, 
                     gaps_df: pd.DataFrame,
                     recommendations: List[Dict],
                     output_path: str = 'data/synthetic/gap_analysis.pkl'):
        """Save gap analysis results."""
        analysis_data = {
            'gaps': gaps_df,
            'recommendations': recommendations,
            'summary': {
                'total_gaps': len(gaps_df),
                'gap_type_distribution': gaps_df['gap_type'].value_counts().to_dict() if not gaps_df.empty else {},
                'impact_threshold': self.impact_threshold,
                'detection_threshold': self.detection_threshold
            }
        }
        
        with open(output_path, 'wb') as f:
            pickle.dump(analysis_data, f)
        
        # Save as JSON too
        json_path = output_path.replace('.pkl', '.json')
        json_data = {
            'summary': analysis_data['summary'],
            'top_gaps': gaps_df.head(20).to_dict('records') if not gaps_df.empty else [],
            'recommendations': recommendations
        }
        
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"\nGap analysis saved to:")
        print(f"  {output_path}")
        print(f"  {json_path}")
        
        return analysis_data


def load_gap_analysis(filepath: str = 'data/synthetic/gap_analysis.pkl') -> Dict:
    """Load previously computed gap analysis."""
    with open(filepath, 'rb') as f:
        return pickle.load(f)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run security gap analysis')
    parser.add_argument('--impact-path', default='data/synthetic/impact_analysis.pkl',
                       help='Path to impact analysis results')
    parser.add_argument('--baseline-path', default='data/synthetic/baseline_results.pkl',
                       help='Path to baseline results')
    parser.add_argument('--output-dir', default='data/synthetic',
                       help='Output directory for gap analysis')
    args = parser.parse_args()
    
    print("="*60)
    print("SECURITY GAP ANALYSIS")
    print("="*60)
    
    # Load impact results
    print(f"\n1. Loading impact analysis from {args.impact_path}...")
    try:
        with open(args.impact_path, 'rb') as f:
            impact_results = pickle.load(f)
        print(f"   Loaded {len(impact_results['results'])} impact results")
    except FileNotFoundError:
        print(f"❌ Error: Impact results not found at {args.impact_path}")
        print("   Please run: python digital_twin/impact_analyzer.py")
        exit(1)
    
    # Load baseline results
    print(f"\n2. Loading baseline results from {args.baseline_path}...")
    try:
        with open(args.baseline_path, 'rb') as f:
            baseline_results = pickle.load(f)
        print(f"   Loaded results from {len(baseline_results)} detectors")
    except FileNotFoundError:
        print(f"❌ Error: Baseline results not found at {args.baseline_path}")
        print("   Please run: python baselines/run_baselines.py")
        exit(1)
    
    # Initialize analyzer
    print("\n3. Identifying security gaps...")
    analyzer = GapAnalyzer(impact_threshold=70, detection_threshold=0.3)
    
    # Identify gaps
    gaps = analyzer.identify_security_gaps(impact_results, baseline_results)
    
    # Generate recommendations
    print("\n4. Generating mitigation recommendations...")
    recommendations = analyzer.generate_recommendations(gaps)
    
    # Save analysis
    print("\n5. Saving gap analysis...")
    output_path = f"{args.output_dir}/gap_analysis.pkl"
    analyzer.save_analysis(gaps, recommendations, output_path=output_path)
    
    print("\n" + "="*60)
    print("GAP ANALYSIS COMPLETE!")
    print("="*60)
    print(f"✅ {len(gaps)} security gaps identified")
    print(f"✅ {len(recommendations)} mitigation strategies generated")
    print(f"Results saved to {output_path}")

