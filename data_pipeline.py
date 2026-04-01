"""
Data Preprocessing Pipeline for SWaT Dataset

This module handles loading, cleaning, normalizing, and preparing the SWaT dataset
for VAE training and attack generation.

Author: GenTwin Team
Date: February 2026
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import h5py
import os
from typing import Tuple, Dict
import warnings
warnings.filterwarnings('ignore')


class SWaTDataPipeline:
    """
    Data preprocessing pipeline for SWaT water treatment dataset.
    
    Handles:
    - Loading CSV data
    - Cleaning and outlier handling
    - Normalization
    - Time-window sequence creation
    - Train/test splitting
    - Export to HDF5 format
    """
    
    def __init__(self, 
                 data_path: str = 'data/raw/SWaT_Dataset_Normal_v1.csv',
                 attack_path: str = 'data/raw/SWaT_Dataset_Attack_v0.csv',
                 window_size: int = 60,
                 output_dir: str = 'data/processed'):
        """
        Initialize the data pipeline.
        
        Args:
            data_path: Path to normal operation dataset
            attack_path: Path to attack dataset
            window_size: Number of timesteps per sequence (60 = 1 minute)
            output_dir: Directory to save processed data
        """
        self.data_path = data_path
        self.attack_path = attack_path
        self.window_size = window_size
        self.output_dir = output_dir
        self.scaler = StandardScaler()
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs('data/raw', exist_ok=True)
        os.makedirs('data/synthetic', exist_ok=True)
        
    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load SWaT normal and attack datasets.
        
        Returns:
            Tuple of (normal_df, attack_df)
        """
        print("Loading SWaT datasets...")
        
        # Check if files exist
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(
                f"Normal dataset not found at {self.data_path}\n"
                "Please place SWaT_Dataset_Normal_v1.csv in data/raw/"
            )
        
        # Load normal operation data (7 days)
        normal_df = pd.read_csv(self.data_path)
        print(f"Loaded normal data: {normal_df.shape}")
        
        # Load attack data (4 days with 41 attacks) if available
        attack_df = None
        if os.path.exists(self.attack_path):
            attack_df = pd.read_csv(self.attack_path)
            print(f"Loaded attack data: {attack_df.shape}")
        else:
            print(f"Warning: Attack dataset not found at {self.attack_path}")
            print("Creating synthetic data for demonstration...")
            # Create dummy attack data for development
            attack_df = normal_df.copy().iloc[:10000]
            attack_df['Normal/Attack'] = 'Attack'
        
        return normal_df, attack_df
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean dataset: handle missing values, outliers, and format issues.
        
        Args:
            df: Raw dataframe
            
        Returns:
            Cleaned dataframe
        """
        print("Cleaning data...")
        df_clean = df.copy()
        
        # Remove timestamp column if it exists
        timestamp_cols = ['Timestamp', 'Datetime', ' Timestamp']
        for col in timestamp_cols:
            if col in df_clean.columns:
                df_clean = df_clean.drop(columns=[col])
        
        # Identify sensor/actuator columns (numeric only)
        # Typically named like: FIT101, LIT101, MV101, P101, etc.
        sensor_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()
        
        # Remove target column if present
        target_cols = ['Normal/Attack', 'Label', 'Attack']
        self.target_col = None
        for col in target_cols:
            if col in df_clean.columns:
                self.target_col = col
                if col in sensor_cols:
                    sensor_cols.remove(col)
        
        print(f"Found {len(sensor_cols)} sensor/actuator columns")
        
        # Handle missing values
        missing_before = df_clean[sensor_cols].isnull().sum().sum()
        if missing_before > 0:
            print(f"Handling {missing_before} missing values...")
            # Forward fill then backward fill
            df_clean[sensor_cols] = df_clean[sensor_cols].fillna(method='ffill').fillna(method='bfill')
            # If still missing, fill with column mean
            df_clean[sensor_cols] = df_clean[sensor_cols].fillna(df_clean[sensor_cols].mean())
        
        # Handle outliers using IQR method
        print("Handling outliers...")
        for col in sensor_cols:
            Q1 = df_clean[col].quantile(0.25)
            Q3 = df_clean[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 3 * IQR  # Use 3*IQR for more tolerance
            upper_bound = Q3 + 3 * IQR
            
            # Clip outliers to bounds instead of removing them
            df_clean[col] = df_clean[col].clip(lower_bound, upper_bound)
        
        self.sensor_cols = sensor_cols
        print(f"Cleaned data shape: {df_clean.shape}")
        print(f"Sensor columns: {len(self.sensor_cols)}")
        
        return df_clean
    
    def normalize_data(self, 
                       train_df: pd.DataFrame, 
                       test_df: pd.DataFrame = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Normalize features using StandardScaler fitted on training data.
        
        Args:
            train_df: Training dataframe
            test_df: Test dataframe (optional)
            
        Returns:
            Tuple of (normalized_train, normalized_test)
        """
        print("Normalizing data...")
        
        # Fit scaler on training data only
        train_normalized = self.scaler.fit_transform(train_df[self.sensor_cols])
        print(f"Training data normalized: {train_normalized.shape}")
        
        test_normalized = None
        if test_df is not None:
            test_normalized = self.scaler.transform(test_df[self.sensor_cols])
            print(f"Test data normalized: {test_normalized.shape}")
        
        return train_normalized, test_normalized
    
    def create_sequences(self, data: np.ndarray, window_size: int = None) -> np.ndarray:
        """
        Create time-window sequences for temporal modeling.
        
        Args:
            data: Normalized data array (n_samples, n_features)
            window_size: Sequence length (default: self.window_size)
            
        Returns:
            Sequences array (n_sequences, window_size, n_features)
        """
        if window_size is None:
            window_size = self.window_size
            
        print(f"Creating sequences with window_size={window_size}...")
        
        n_samples, n_features = data.shape
        n_sequences = n_samples - window_size + 1
        
        sequences = np.zeros((n_sequences, window_size, n_features))
        
        for i in range(n_sequences):
            sequences[i] = data[i:i + window_size]
        
        print(f"Created {n_sequences} sequences of shape ({window_size}, {n_features})")
        
        return sequences
    
    def save_to_hdf5(self, 
                     train_data: np.ndarray,
                     test_data: np.ndarray,
                     train_labels: np.ndarray = None,
                     test_labels: np.ndarray = None,
                     filename: str = 'swat_processed.h5'):
        """
        Save processed data to HDF5 format for fast loading.
        
        Args:
            train_data: Training sequences
            test_data: Test sequences
            train_labels: Training labels (optional)
            test_labels: Test labels (optional)
            filename: Output filename
        """
        output_path = os.path.join(self.output_dir, filename)
        print(f"Saving to HDF5: {output_path}")
        
        with h5py.File(output_path, 'w') as f:
            # Save datasets
            f.create_dataset('train_data', data=train_data, compression='gzip')
            f.create_dataset('test_data', data=test_data, compression='gzip')
            
            if train_labels is not None:
                f.create_dataset('train_labels', data=train_labels, compression='gzip')
            if test_labels is not None:
                f.create_dataset('test_labels', data=test_labels, compression='gzip')
            
            # Save metadata
            f.attrs['window_size'] = self.window_size
            f.attrs['n_features'] = len(self.sensor_cols)
            f.attrs['sensor_cols'] = ','.join(self.sensor_cols)
            f.attrs['scaler_mean'] = self.scaler.mean_
            f.attrs['scaler_scale'] = self.scaler.scale_
        
        print(f"Saved successfully!")
        print(f"  Train data: {train_data.shape}")
        print(f"  Test data: {test_data.shape}")
    
    def run_pipeline(self) -> Dict:
        """
        Execute the complete data processing pipeline.
        
        Returns:
            Dictionary with processing statistics
        """
        print("="*60)
        print("STARTING SWAT DATA PREPROCESSING PIPELINE")
        print("="*60)
        
        # Step 1: Load data
        normal_df, attack_df = self.load_data()
        
        # Step 2: Clean data
        normal_clean = self.clean_data(normal_df)
        attack_clean = self.clean_data(attack_df)
        
        # Step 3: Split normal data (train/validation)
        # Use 80% for training, 20% for validation
        train_df, val_df = train_test_split(normal_clean, test_size=0.2, random_state=42)
        print(f"\nSplit normal data:")
        print(f"  Training: {len(train_df)} samples")
        print(f"  Validation: {len(val_df)} samples")
        
        # Step 4: Normalize data
        train_normalized, val_normalized = self.normalize_data(train_df, val_df)
        _, attack_normalized = self.normalize_data(train_df, attack_clean)
        
        # Step 5: Create sequences
        train_sequences = self.create_sequences(train_normalized)
        val_sequences = self.create_sequences(val_normalized)
        attack_sequences = self.create_sequences(attack_normalized)
        
        # Step 6: Save to HDF5
        self.save_to_hdf5(
            train_sequences, 
            val_sequences,
            filename='swat_normal.h5'
        )
        
        # Save attack data separately
        self.save_to_hdf5(
            train_sequences[:1000],  # Small subset for reference
            attack_sequences,
            filename='swat_attacks.h5'
        )
        
        print("\n" + "="*60)
        print("PIPELINE COMPLETE!")
        print("="*60)
        
        stats = {
            'n_train_sequences': len(train_sequences),
            'n_val_sequences': len(val_sequences),
            'n_attack_sequences': len(attack_sequences),
            'window_size': self.window_size,
            'n_features': len(self.sensor_cols),
            'sensor_cols': self.sensor_cols
        }
        
        return stats


def load_processed_data(filepath: str = 'data/processed/swat_normal.h5') -> Tuple:
    """
    Load preprocessed data from HDF5.
    
    Args:
        filepath: Path to HDF5 file
        
    Returns:
        Tuple of (train_data, test_data, metadata)
    """
    print(f"Loading processed data from {filepath}")
    
    with h5py.File(filepath, 'r') as f:
        train_data = f['train_data'][:]
        test_data = f['test_data'][:]
        
        metadata = {
            'window_size': f.attrs['window_size'],
            'n_features': f.attrs['n_features'],
            'sensor_cols': f.attrs['sensor_cols'].split(','),
            'scaler_mean': f.attrs['scaler_mean'],
            'scaler_scale': f.attrs['scaler_scale']
        }
    
    print(f"Loaded: train={train_data.shape}, test={test_data.shape}")
    
    return train_data, test_data, metadata


if __name__ == "__main__":
    # Run the complete pipeline
    pipeline = SWaTDataPipeline(
        data_path='data/raw/SWaT_Dataset_Normal_v1.csv',
        attack_path='data/raw/SWaT_Dataset_Attack_v0.csv',
        window_size=60
    )
    
    stats = pipeline.run_pipeline()
    
    print("\nProcessing Statistics:")
    for key, value in stats.items():
        if key != 'sensor_cols':
            print(f"  {key}: {value}")
