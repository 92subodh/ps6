"""
Quick Setup and Test Script

Validates the GenTwin installation and runs a minimal test.

Usage:
    python setup_and_test.py

Author: GenTwin Team
Date: February 2026
"""

import os
import sys
import numpy as np


def create_directories():
    """Create necessary directories."""
    print("Creating directory structure...")
    
    dirs = [
        'data/raw',
        'data/processed',
        'data/synthetic',
        'models/checkpoints',
        'logs',
        'reports'
    ]
    
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"  ✓ {dir_path}")
    
    print("✅ Directories created")


def test_imports():
    """Test that all required packages can be imported."""
    print("\nTesting package imports...")
    
    try:
        import tensorflow as tf
        print(f"  ✓ TensorFlow {tf.__version__}")
        
        import pandas as pd
        print(f"  ✓ Pandas {pd.__version__}")
        
        import numpy as np
        print(f"  ✓ NumPy {np.__version__}")
        
        import sklearn
        print(f"  ✓ scikit-learn {sklearn.__version__}")
        
        import streamlit as st
        print(f"  ✓ Streamlit {st.__version__}")
        
        import plotly
        print(f"  ✓ Plotly {plotly.__version__}")
        
        import h5py
        print(f"  ✓ h5py {h5py.__version__}")
        
        print("✅ All packages imported successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\nInstall missing packages with:")
        print("  pip install -r requirements.txt")
        return False


def test_vae_model():
    """Test VAE model creation."""
    print("\nTesting VAE model...")
    
    try:
        from models.vae_model import create_vae
        
        vae = create_vae(input_dim=51, latent_dim=32, beta=0.5)
        print("  ✓ VAE model created")
        
        # Test with dummy data
        import tensorflow as tf
        dummy_input = tf.random.normal((16, 51))
        output = vae(dummy_input)
        
        print(f"  ✓ Forward pass: {dummy_input.shape} → {output.shape}")
        print("✅ VAE model test passed")
        return True
        
    except Exception as e:
        print(f"❌ VAE test failed: {e}")
        return False


def test_digital_twin():
    """Test Digital Twin simulation."""
    print("\nTesting Digital Twin...")
    
    try:
        from digital_twin.swat_process import SWaTDigitalTwin
        
        dt = SWaTDigitalTwin(dt=1.0)
        print("  ✓ Digital Twin created")
        
        # Simulate 10 seconds
        for i in range(10):
            dt.step({})
        
        state = dt.get_system_state()
        print(f"  ✓ Simulation: {state['time']}s, Safe: {state['is_safe']}")
        print("✅ Digital Twin test passed")
        return True
        
    except Exception as e:
        print(f"❌ Digital Twin test failed: {e}")
        return False


def create_sample_data():
    """Create sample data for testing."""
    print("\nCreating sample dataset...")
    
    try:
        import pandas as pd
        import numpy as np
        
        # Create synthetic SWaT-like data
        n_samples = 10000
        n_features = 51
        
        # Normal data
        normal_data = np.random.randn(n_samples, n_features)
        normal_df = pd.DataFrame(
            normal_data,
            columns=[f'Feature_{i}' for i in range(n_features)]
        )
        normal_df['Normal/Attack'] = 'Normal'
        
        # Save
        normal_df.to_csv('data/raw/SWaT_Dataset_Normal_v1.csv', index=False)
        print(f"  ✓ Created synthetic normal data: {normal_df.shape}")
        
        # Attack data
        attack_data = np.random.randn(2000, n_features) * 1.5
        attack_df = pd.DataFrame(
            attack_data,
            columns=[f'Feature_{i}' for i in range(n_features)]
        )
        attack_df['Normal/Attack'] = 'Attack'
        
        attack_df.to_csv('data/raw/SWaT_Dataset_Attack_v0.csv', index=False)
        print(f"  ✓ Created synthetic attack data: {attack_df.shape}")
        
        print("✅ Sample data created")
        print("⚠️  Note: This is synthetic data for testing only")
        return True
        
    except Exception as e:
        print(f"❌ Data creation failed: {e}")
        return False


def main():
    """Run all setup and tests."""
    print("="*70)
    print("GENTWIN SETUP AND TEST")
    print("="*70)
    
    # Create directories
    create_directories()
    
    # Test imports
    if not test_imports():
        print("\n❌ Setup failed: Missing dependencies")
        sys.exit(1)
    
    # Test components
    test_vae_model()
    test_digital_twin()
    
    # Create sample data
    create_sample_data()
    
    print("\n" + "="*70)
    print("✅ SETUP AND TEST COMPLETE!")
    print("="*70)
    
    print("\nNext steps:")
    print("  1. (Optional) Replace sample data with real SWaT dataset")
    print("  2. Run: python data_pipeline.py")
    print("  3. Run: python models/train_vae.py")
    print("  4. Run: python attack_generator.py")
    print("  5. Run: streamlit run app.py")
    print("\nOr run the full pipeline:")
    print("  python run_full_pipeline.py")


if __name__ == "__main__":
    main()
