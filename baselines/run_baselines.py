"""
Run Baseline Anomaly Detectors

Trains and evaluates baseline detectors on synthetic attacks:
- Threshold (3σ)
- Isolation Forest
- One-Class SVM
- LSTM Autoencoder

Author: GenTwin Team
Date: February 2026
"""

import os
import sys
import numpy as np
import pickle
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from baselines.detectors import create_baseline_detectors, BaselineEvaluator
from data_pipeline import load_processed_data
from attack_generator import load_synthetic_attacks


def run_baseline_evaluation(
    normal_data_path: str = 'data/processed/swat_normal.h5',
    attacks_path: str = 'data/synthetic/synthetic_attacks.pkl',
    output_dir: str = 'data/synthetic',
    quick_test: bool = False
):
    """
    Run baseline detector evaluation.
    
    Args:
        normal_data_path: Path to normal training data
        attacks_path: Path to synthetic attacks
        output_dir: Where to save results
        quick_test: Use fewer samples for quick testing
    """
    print("="*60)
    print("BASELINE DETECTOR EVALUATION")
    print("="*60)
    
    # Load normal data for training
    print("\n1. Loading normal training data...")
    train_data, _, metadata = load_processed_data(normal_data_path)
    
    # Flatten sequences
    train_flat = train_data.reshape(-1, metadata['n_features'])
    
    if quick_test:
        train_flat = train_flat[:5000]
    
    print(f"   Training samples: {train_flat.shape}")
    
    # Load synthetic attacks
    print("\n2. Loading synthetic attacks...")
    attacks_data = load_synthetic_attacks(attacks_path)
    attacks = attacks_data['attacks']
    attack_labels = attacks_data['labels']
    
    print(f"   Attack samples: {attacks.shape}")
    
    # Create test set: normal + attacks
    print("\n3. Preparing test set...")
    
    # Sample some normal data for test set
    n_normal_test = min(len(attacks), 1000)
    normal_test_idx = np.random.choice(len(train_flat), n_normal_test, replace=False)
    normal_test = train_flat[normal_test_idx]
    
    # Combine
    X_test = np.vstack([normal_test, attacks])
    y_test = np.array([0] * n_normal_test + [1] * len(attacks))
    
    print(f"   Test set: {X_test.shape}")
    print(f"   Normal samples: {n_normal_test}")
    print(f"   Attack samples: {len(attacks)}")
    
    # Create and train detectors
    print("\n4. Creating baseline detectors...")
    detectors = create_baseline_detectors(
        input_dim=metadata['n_features'],
        svm_max_samples=10000  # Limit SVM training samples for speed
    )
    evaluator = BaselineEvaluator(detectors)
    
    print("\n5. Training detectors on normal data...")
    evaluator.train_all(train_flat)
    
    # Evaluate
    print("\n6. Evaluating detectors...")
    results = evaluator.evaluate_all(X_test, y_test)
    
    # Print results
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    for name, metrics in results.items():
        print(f"\n{name}:")
        print(f"  Precision:    {metrics['precision']:.3f}")
        print(f"  Recall:       {metrics['recall']:.3f}")
        print(f"  F1-Score:     {metrics['f1_score']:.3f}")
        print(f"  Detection Rate: {metrics['detection_rate']:.1f}%")
        print(f"  False Positive Rate: {metrics['false_positive_rate']:.1f}%")
    
    # Analyze detection by severity
    print("\n" + "="*60)
    print("DETECTION BY SEVERITY")
    print("="*60)
    
    severity_results = {}
    for severity in ['mild', 'moderate', 'severe']:
        severity_mask = attack_labels == severity
        if np.sum(severity_mask) > 0:
            severity_results[severity] = {}
            print(f"\n{severity.capitalize()}:")
            
            for name in results.keys():
                # Get predictions for this severity
                attack_predictions = results[name]['predictions'][n_normal_test:]
                severity_predictions = attack_predictions[severity_mask]
                detection_rate = np.mean(severity_predictions) * 100
                
                severity_results[severity][name] = {
                    'detection_rate': float(detection_rate),
                    'n_samples': int(np.sum(severity_mask))
                }
                
                print(f"  {name}: {detection_rate:.1f}%")
    
    # Save results
    print("\n7. Saving results...")
    
    # Save full results with predictions
    output_path = os.path.join(output_dir, 'baseline_results.pkl')
    output_data = {
        'results': results,
        'severity_results': severity_results,
        'test_labels': y_test,
        'attack_labels': attack_labels,
        'n_normal_test': n_normal_test,
        'metadata': metadata
    }
    
    with open(output_path, 'wb') as f:
        pickle.dump(output_data, f)
    
    print(f"   Results saved to {output_path}")
    
    # Save summary as JSON
    summary_path = os.path.join(output_dir, 'baseline_results_summary.json')
    summary = {
        'overall_results': {
            name: {
                'precision': float(metrics['precision']),
                'recall': float(metrics['recall']),
                'f1_score': float(metrics['f1_score']),
                'detection_rate': float(metrics['detection_rate']),
                'false_positive_rate': float(metrics['false_positive_rate'])
            }
            for name, metrics in results.items()
        },
        'by_severity': severity_results,
        'test_set': {
            'n_normal': int(n_normal_test),
            'n_attacks': int(len(attacks))
        }
    }
    
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"   Summary saved to {summary_path}")
    
    # Save trained detectors
    evaluator_path = os.path.join(output_dir, 'baseline_detectors.pkl')
    evaluator.save(evaluator_path)
    print(f"   Trained detectors saved to {evaluator_path}")
    
    print("\n" + "="*60)
    print("BASELINE EVALUATION COMPLETE!")
    print("="*60)
    
    return output_data


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run baseline detector evaluation')
    parser.add_argument('--quick-test', action='store_true',
                       help='Quick test mode (fewer samples)')
    args = parser.parse_args()
    
    try:
        results = run_baseline_evaluation(quick_test=args.quick_test)
        print("\n✅ Baseline evaluation completed successfully!")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure to run the pipeline in order:")
        print("  1. python data_pipeline.py")
        print("  2. python models/train_vae.py")
        print("  3. python attack_generator.py")
        print("  4. python digital_twin/impact_analyzer.py")
        print("  5. python baselines/run_baselines.py  <- You are here")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
