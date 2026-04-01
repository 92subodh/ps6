"""
Anomaly Impact Analyzer

Simulates synthetic attacks in the Digital Twin and calculates impact severity.

Author: GenTwin Team
Date: February 2026
"""

import os
import sys
import numpy as np
import pickle
import json
from typing import Dict, List
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from digital_twin.swat_process import SWaTDigitalTwin
from attack_generator import load_synthetic_attacks


class ImpactAnalyzer:
    """
    Analyze impact of synthetic attacks using Digital Twin simulation.
    
    For each attack:
    1. Feed into DT
    2. Simulate 300 seconds (5 minutes)
    3. Track safety violations
    4. Calculate severity score (0-100)
    """
    
    def __init__(self, dt: float = 1.0):
        """
        Initialize impact analyzer.
        
        Args:
            dt: Simulation timestep (seconds)
        """
        self.dt = dt
        self.digital_twin = SWaTDigitalTwin(dt=dt)
        
        # Severity weights for different violation types
        self.severity_weights = {
            'tank_overflow': 10.0,
            'tank_underflow': 10.0,
            'pump_deadheading': 8.0,
            'chlorine_high': 7.0,
            'chlorine_low': 5.0,
            'ph_violation': 6.0,
        }
    
    def calculate_severity_score(self, 
                                 violations_history: List[Dict],
                                 duration: int) -> float:
        """
        Calculate severity score (0-100) based on violations.
        
        Args:
            violations_history: List of violation events
            duration: Simulation duration
            
        Returns:
            Severity score
        """
        if not violations_history:
            return 0.0
        
        total_score = 0.0
        
        # Count violations by type
        violation_counts = {}
        for event in violations_history:
            for violation in event['violations']:
                v_type = violation['type']
                violation_counts[v_type] = violation_counts.get(v_type, 0) + 1
        
        # Calculate weighted score
        for v_type, count in violation_counts.items():
            weight = self.severity_weights.get(v_type, 5.0)
            # More violations = higher score, but with diminishing returns
            type_score = weight * np.log1p(count)
            total_score += type_score
        
        # Normalize to 0-100 scale
        # Max realistic score ~200, so divide by 2
        severity = min(100.0, total_score / 2.0)
        
        return severity
    
    def analyze_attack(self, 
                      attack_sensors: np.ndarray,
                      duration: int = 300) -> Dict:
        """
        Analyze single attack scenario.
        
        Args:
            attack_sensors: Sensor values for attack (n_features,)
            duration: Simulation duration in seconds
            
        Returns:
            Analysis results dictionary
        """
        self.digital_twin.reset()
        
        # Create sensor mapping (simplified - assumes order matches)
        # In real implementation, would map to specific sensor names
        sensor_names = list(self.digital_twin.state.keys())
        n_sensors = min(len(attack_sensors), len(sensor_names))
        
        violations_per_step = []
        states = []
        
        for t in range(duration):
            # Create sensor dictionary
            sensor_dict = {
                sensor_names[i]: float(attack_sensors[i])
                for i in range(n_sensors)
            }
            
            # Step simulation
            state = self.digital_twin.step(sensor_dict)
            states.append(state.copy())
            
            # Record violations
            violations = self.digital_twin.check_safety_constraints()
            violations_per_step.append(len(violations))
        
        # Calculate metrics
        total_violations = sum(violations_per_step)
        max_violations = max(violations_per_step) if violations_per_step else 0
        violation_duration = sum(1 for v in violations_per_step if v > 0)
        
        severity = self.calculate_severity_score(
            self.digital_twin.violation_history,
            duration
        )
        
        # Categorize most common violation type
        violation_types = []
        for event in self.digital_twin.violation_history:
            for v in event['violations']:
                violation_types.append(v['type'])
        
        primary_violation = max(set(violation_types), key=violation_types.count) if violation_types else None
        
        # Identify affected stages
        affected_stages = set()
        for event in self.digital_twin.violation_history:
            for v in event['violations']:
                sensor = v.get('sensor', '')
                # Determine stage from sensor name
                if 'LIT101' in sensor or 'P101' in sensor or 'MV101' in sensor:
                    affected_stages.add('P1')
                elif 'AIT2' in sensor or 'P201' in sensor:
                    affected_stages.add('P2')
                elif 'LIT301' in sensor or 'MV30' in sensor:
                    affected_stages.add('P3')
                elif 'AIT4' in sensor:
                    affected_stages.add('P4')
                elif 'AIT5' in sensor or 'P501' in sensor:
                    affected_stages.add('P5')
                elif 'LIT601' in sensor or 'P60' in sensor:
                    affected_stages.add('P6')
        
        return {
            'severity': severity,
            'total_violations': total_violations,
            'max_violations_per_step': max_violations,
            'violation_duration': violation_duration,
            'violation_percentage': (violation_duration / duration) * 100,
            'primary_violation_type': primary_violation,
            'affected_stages': list(affected_stages),
            'violations_per_step': violations_per_step,
            'violation_history': self.digital_twin.violation_history
        }
    
    def analyze_all_attacks(self, 
                           attacks_data: Dict,
                           output_path: str = 'data/synthetic/impact_analysis.pkl') -> Dict:
        """
        Analyze all synthetic attacks.
        
        Args:
            attacks_data: Dictionary from attack generator
            output_path: Path to save results
            
        Returns:
            Analysis results for all attacks
        """
        print("="*60)
        print("ANALYZING ATTACK IMPACTS WITH DIGITAL TWIN")
        print("="*60)
        
        attacks = attacks_data['attacks']
        labels = attacks_data['labels']
        metadata = attacks_data['metadata']
        
        print(f"\nAnalyzing {len(attacks)} attacks...")
        print("This may take a few minutes...\n")
        
        results = []
        
        for i, (attack, label, meta) in enumerate(tqdm(
            zip(attacks, labels, metadata),
            total=len(attacks),
            desc="Analyzing attacks"
        )):
            # Analyze attack
            impact = self.analyze_attack(attack, duration=300)
            
            # Combine with metadata
            result = {
                'attack_id': meta['attack_id'],
                'severity_level': label,
                'sigma': meta['sigma'],
                'impact_score': impact['severity'],
                'total_violations': impact['total_violations'],
                'violation_percentage': impact['violation_percentage'],
                'primary_violation': impact['primary_violation_type'],
                'affected_stages': impact['affected_stages'],
                'violation_details': impact['violation_history']
            }
            
            results.append(result)
        
        # Create summary statistics
        print("\n" + "="*60)
        print("IMPACT ANALYSIS SUMMARY")
        print("="*60)
        
        results_array = np.array([r['impact_score'] for r in results])
        
        print(f"\nOverall Statistics:")
        print(f"  Mean impact score: {np.mean(results_array):.2f}")
        print(f"  Median impact score: {np.median(results_array):.2f}")
        print(f"  Std impact score: {np.std(results_array):.2f}")
        print(f"  Max impact score: {np.max(results_array):.2f}")
        print(f"  Min impact score: {np.min(results_array):.2f}")
        
        print(f"\nBy Severity Level:")
        for severity in ['mild', 'moderate', 'severe']:
            severity_results = [r['impact_score'] for r in results if r['severity_level'] == severity]
            if severity_results:
                print(f"  {severity.capitalize()}:")
                print(f"    Mean: {np.mean(severity_results):.2f}")
                print(f"    Max: {np.max(severity_results):.2f}")
        
        # High-impact attacks
        high_impact = [r for r in results if r['impact_score'] > 70]
        print(f"\nHigh-Impact Attacks (score > 70): {len(high_impact)}")
        
        # Save results
        output_data = {
            'results': results,
            'summary': {
                'total_attacks': len(attacks),
                'mean_impact': float(np.mean(results_array)),
                'median_impact': float(np.median(results_array)),
                'high_impact_count': len(high_impact),
                'severity_distribution': {
                    severity: len([r for r in results if r['severity_level'] == severity])
                    for severity in ['mild', 'moderate', 'severe']
                }
            }
        }
        
        print(f"\nSaving results to {output_path}...")
        with open(output_path, 'wb') as f:
            pickle.dump(output_data, f)
        
        # Also save summary as JSON
        summary_path = output_path.replace('.pkl', '_summary.json')
        with open(summary_path, 'w') as f:
            # Exclude detailed violation history for JSON
            json_results = [{k: v for k, v in r.items() if k != 'violation_details'} 
                           for r in results]
            json.dump({
                'summary': output_data['summary'],
                'top_attacks': json_results[:20]
            }, f, indent=2)
        
        print(f"Summary saved to {summary_path}")
        
        return output_data


def load_impact_analysis(filepath: str = 'data/synthetic/impact_analysis.pkl') -> Dict:
    """Load previously computed impact analysis."""
    with open(filepath, 'rb') as f:
        return pickle.load(f)


if __name__ == "__main__":
    print("Loading synthetic attacks...")
    
    try:
        attacks_data = load_synthetic_attacks('data/synthetic/synthetic_attacks.pkl')
        
        print("Initializing impact analyzer...")
        analyzer = ImpactAnalyzer(dt=1.0)
        
        print("Analyzing attacks...")
        results = analyzer.analyze_all_attacks(attacks_data)
        
        print("\n" + "="*60)
        print("IMPACT ANALYSIS COMPLETE!")
        print("="*60)
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nPlease run attack_generator.py first to generate synthetic attacks.")
