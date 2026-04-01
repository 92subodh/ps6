"""
Synthetic Attack Generation Engine

Generates synthetic attack scenarios by sampling from VAE latent space
with controlled deviations from normal operation.

Author: GenTwin Team
Date: February 2026
"""

import os
import sys
import numpy as np
import pickle
import json
import tensorflow as tf
from typing import List, Dict, Tuple
import h5py

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models.vae_model import SWaTVAE
from data_pipeline import load_processed_data


class AttackGenerator:
    """
    Generate synthetic attack scenarios using trained VAE.
    
    Strategy:
    1. Sample normal operation data
    2. Encode to latent space
    3. Add Gaussian noise based on severity
    4. Decode back to sensor space
    5. Classify and save attacks
    """
    
    def __init__(self, 
                 vae_model_path: str = 'models/checkpoints/best_vae.keras',
                 data_path: str = 'data/processed/swat_normal.h5',
                 output_dir: str = 'data/synthetic'):
        """
        Initialize attack generator.
        
        Args:
            vae_model_path: Path to trained VAE model
            data_path: Path to preprocessed normal data
            output_dir: Directory to save generated attacks
        """
        self.vae_model_path = vae_model_path
        self.data_path = data_path
        self.output_dir = output_dir
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Load VAE model
        print(f"Loading VAE model from {vae_model_path}...")
        # Import custom objects for model loading
        from models.vae_model import SWaTVAE, Sampling
        self.vae = tf.keras.models.load_model(
            vae_model_path, 
            custom_objects={'SWaTVAE': SWaTVAE, 'Sampling': Sampling},
            compile=False
        )
        print("VAE model loaded successfully!")
        
        # Load normal data for reference
        print(f"Loading normal data from {data_path}...")
        self.train_data, _, self.metadata = load_processed_data(data_path)
        
        # Flatten for VAE
        self.train_flat = self.train_data.reshape(-1, self.metadata['n_features'])
        print(f"Normal data loaded: {self.train_flat.shape}")
        
        # Encode normal data to get latent distribution
        print("Encoding normal data to latent space...")
        self.normal_z_mean, self.normal_z_log_var, self.normal_z = self.vae.encode(self.train_flat)
        print("Encoding complete!")
        
    def generate_attacks(self, 
                        n_attacks: int = 1000,
                        severity_levels: Dict[str, float] = None) -> Dict:
        """
        Generate synthetic attack scenarios.
        
        Args:
            n_attacks: Total number of attacks to generate
            severity_levels: Dict mapping severity to noise sigma
                           Default: {'mild': 1.0, 'moderate': 2.0, 'severe': 3.0}
        
        Returns:
            Dictionary containing generated attacks and metadata
        """
        if severity_levels is None:
            severity_levels = {
                'mild': 1.0,
                'moderate': 2.0,
                'severe': 3.0
            }
        
        print("="*60)
        print("GENERATING SYNTHETIC ATTACKS")
        print("="*60)
        print(f"Total attacks to generate: {n_attacks}")
        print(f"Severity levels: {severity_levels}")
        
        # Split attacks evenly across severity levels
        n_per_severity = n_attacks // len(severity_levels)
        
        all_attacks = []
        all_labels = []
        all_metadata = []
        
        attack_id = 0
        
        for severity, sigma in severity_levels.items():
            print(f"\nGenerating {n_per_severity} '{severity}' attacks (σ={sigma})...")
            
            for i in range(n_per_severity):
                # Sample a random normal latent vector
                idx = np.random.randint(0, len(self.normal_z_mean))
                base_z_mean = self.normal_z_mean[idx:idx+1]
                
                # Add Gaussian noise based on severity
                noise = np.random.normal(0, sigma, size=base_z_mean.shape)
                perturbed_z = base_z_mean + noise
                
                # Decode to sensor space
                attack_sensors = self.vae.decode(perturbed_z).numpy()
                
                # Calculate deviation from original
                original_sensors = self.train_flat[idx:idx+1]
                deviation = np.mean(np.abs(attack_sensors - original_sensors))
                
                # Store attack
                all_attacks.append(attack_sensors[0])
                all_labels.append(severity)
                all_metadata.append({
                    'attack_id': attack_id,
                    'severity': severity,
                    'sigma': sigma,
                    'base_idx': int(idx),
                    'mean_deviation': float(deviation),
                    'latent_mean': base_z_mean[0].numpy().tolist(),
                    'perturbation': noise[0].tolist()
                })
                
                attack_id += 1
                
                if (i + 1) % 100 == 0:
                    print(f"  Generated {i+1}/{n_per_severity} attacks...")
        
        # Convert to arrays
        attacks_array = np.array(all_attacks)
        labels_array = np.array(all_labels)
        
        print(f"\nGeneration complete!")
        print(f"  Generated attacks shape: {attacks_array.shape}")
        print(f"  Total attacks: {len(attacks_array)}")
        
        # Package results
        results = {
            'attacks': attacks_array,
            'labels': labels_array,
            'metadata': all_metadata,
            'severity_levels': severity_levels,
            'n_features': self.metadata['n_features'],
            'sensor_cols': self.metadata['sensor_cols'],
            'scaler_mean': self.metadata['scaler_mean'],
            'scaler_scale': self.metadata['scaler_scale']
        }
        
        return results
    
    def save_attacks(self, attacks_data: Dict, filename: str = 'synthetic_attacks.pkl'):
        """
        Save generated attacks to file.
        
        Args:
            attacks_data: Dictionary from generate_attacks()
            filename: Output filename
        """
        output_path = os.path.join(self.output_dir, filename)
        
        print(f"\nSaving attacks to {output_path}...")
        
        with open(output_path, 'wb') as f:
            pickle.dump(attacks_data, f)
        
        print(f"Attacks saved successfully!")
        
        # Also save metadata as JSON for easy inspection
        metadata_path = os.path.join(self.output_dir, 'synthetic_attacks_metadata.json')
        
        # Create summary for JSON (don't include full arrays)
        summary = {
            'n_attacks': int(len(attacks_data['attacks'])),
            'n_features': int(attacks_data['n_features']),
            'severity_distribution': {
                severity: int(np.sum(attacks_data['labels'] == severity))
                for severity in attacks_data['severity_levels'].keys()
            },
            'severity_levels': {
                k: float(v) for k, v in attacks_data['severity_levels'].items()
            },
            'sensor_cols': attacks_data['sensor_cols']
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"Metadata saved to {metadata_path}")
        
        return output_path
    
    def analyze_attacks(self, attacks_data: Dict):
        """
        Perform basic analysis on generated attacks.
        
        Args:
            attacks_data: Dictionary from generate_attacks()
        """
        print("\n" + "="*60)
        print("ATTACK ANALYSIS")
        print("="*60)
        
        attacks = attacks_data['attacks']
        labels = attacks_data['labels']
        metadata = attacks_data['metadata']
        
        # Distribution by severity
        print("\nSeverity Distribution:")
        for severity in attacks_data['severity_levels'].keys():
            count = np.sum(labels == severity)
            print(f"  {severity.capitalize()}: {count} attacks")
        
        # Deviation statistics
        print("\nDeviation Statistics (mean absolute difference from normal):")
        for severity in attacks_data['severity_levels'].keys():
            mask = labels == severity
            deviations = [m['mean_deviation'] for m, l in zip(metadata, labels) if l == severity]
            print(f"  {severity.capitalize()}:")
            print(f"    Mean: {np.mean(deviations):.4f}")
            print(f"    Std: {np.std(deviations):.4f}")
            print(f"    Min: {np.min(deviations):.4f}")
            print(f"    Max: {np.max(deviations):.4f}")
        
        # Feature-wise statistics
        print("\nFeature Statistics:")
        print(f"  Mean across all attacks: {np.mean(attacks):.4f}")
        print(f"  Std across all attacks: {np.std(attacks):.4f}")
        print(f"  Min value: {np.min(attacks):.4f}")
        print(f"  Max value: {np.max(attacks):.4f}")
        
        # Compare with normal data
        print("\nComparison with Normal Data:")
        print(f"  Normal mean: {np.mean(self.train_flat):.4f}")
        print(f"  Normal std: {np.std(self.train_flat):.4f}")
        print(f"  Attack mean: {np.mean(attacks):.4f}")
        print(f"  Attack std: {np.std(attacks):.4f}")


def load_synthetic_attacks(filepath: str = 'data/synthetic/synthetic_attacks.pkl') -> Dict:
    """
    Load previously generated synthetic attacks.
    
    Args:
        filepath: Path to saved attacks file
        
    Returns:
        Dictionary containing attacks and metadata
    """
    print(f"Loading synthetic attacks from {filepath}...")
    
    with open(filepath, 'rb') as f:
        attacks_data = pickle.load(f)
    
    print(f"Loaded {len(attacks_data['attacks'])} attacks")
    
    return attacks_data


if __name__ == "__main__":
    # Generate synthetic attacks
    print("Initializing attack generator...")
    
    try:
        generator = AttackGenerator(
            vae_model_path='models/checkpoints/best_vae.keras',
            data_path='data/processed/swat_normal.h5'
        )
        
        # Generate attacks
        attacks_data = generator.generate_attacks(
            n_attacks=1000,
            severity_levels={
                'mild': 1.0,
                'moderate': 2.0,
                'severe': 3.0
            }
        )
        
        # Analyze attacks
        generator.analyze_attacks(attacks_data)
        
        # Save attacks
        output_path = generator.save_attacks(attacks_data)
        
        print(f"\n{'='*60}")
        print("ATTACK GENERATION COMPLETE!")
        print("="*60)
        print(f"Attacks saved to: {output_path}")
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nPlease ensure you have:")
        print("  1. Run data_pipeline.py to preprocess data")
        print("  2. Run models/train_vae.py to train the VAE model")
