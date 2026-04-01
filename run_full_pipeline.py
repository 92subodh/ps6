"""
Complete Pipeline Runner

Executes the full GenTwin pipeline from data preprocessing to dashboard.

Usage:
    python run_full_pipeline.py [--skip-training] [--quick-test]

Author: GenTwin Team
Date: February 2026
"""

import os
import sys
import argparse
from pathlib import Path


def check_dependencies():
    """Check if required packages are installed."""
    print("Checking dependencies...")
    # Map pip package names to their import names
    required = {
        'tensorflow': 'tensorflow',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'scikit-learn': 'sklearn',  # pip name: scikit-learn, import name: sklearn
        'scipy': 'scipy',
        'streamlit': 'streamlit',
        'plotly': 'plotly',
        'h5py': 'h5py'
    }
    
    missing = []
    for package, import_name in required.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies installed")
    return True


def check_data():
    """Check if data files exist."""
    print("\nChecking data files...")
    
    data_files = [
        'data/raw/SWaT_Dataset_Normal_v1.csv',
        'data/raw/SWaT_Dataset_Attack_v0.csv'
    ]
    
    missing = []
    for file in data_files:
        if not os.path.exists(file):
            missing.append(file)
    
    if missing:
        print(f"⚠️  Data files not found:")
        for file in missing:
            print(f"    - {file}")
        print("\nThe pipeline will create synthetic data for demonstration.")
        return False
    
    print("✅ Data files found")
    return True


def run_step(name, command, skip=False):
    """Run a pipeline step."""
    print("\n" + "="*70)
    print(f"STEP: {name}")
    print("="*70)
    
    if skip:
        print(f"⏭️  Skipping {name}")
        return True
    
    print(f"Running: {command}")
    result = os.system(command)
    
    if result != 0:
        print(f"❌ {name} failed with exit code {result}")
        return False
    
    print(f"✅ {name} completed successfully")
    return True


def main():
    parser = argparse.ArgumentParser(description='Run GenTwin full pipeline')
    parser.add_argument('--skip-training', action='store_true',
                       help='Skip VAE training (use existing model)')
    parser.add_argument('--quick-test', action='store_true',
                       help='Quick test mode (fewer epochs, attacks)')
    args = parser.parse_args()
    
    print("="*70)
    print("GENTWIN FULL PIPELINE RUNNER")
    print("="*70)
    
    # Check prerequisites
    if not check_dependencies():
        sys.exit(1)
    
    check_data()
    
    # Pipeline steps
    steps = [
        ("Data Preprocessing", "python data_pipeline.py", False),
        ("VAE Training", "python models/train_vae.py", args.skip_training),
        ("Attack Generation", "python attack_generator.py", False),
        ("Impact Analysis", "python digital_twin/impact_analyzer.py", False),
        ("Baseline Detection", "python baselines/run_baselines.py", False),
        ("Gap Analysis", "python gap_analyzer.py", False),
        ("Dashboard Launch", "streamlit run app.py", False),
    ]
    
    # Run pipeline
    for name, command, skip in steps:
        if not run_step(name, command, skip):
            print("\n❌ Pipeline failed. Please check error messages above.")
            sys.exit(1)
    
    print("\n" + "="*70)
    print("✅ GENTWIN PIPELINE COMPLETED SUCCESSFULLY!")
    print("="*70)
    print("\nThe dashboard should now be running at http://localhost:8501")
    print("Press Ctrl+C to stop the dashboard.")


if __name__ == "__main__":
    main()
