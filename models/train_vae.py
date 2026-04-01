"""
Training Script for SWaT VAE Model

Trains the Variational Autoencoder on preprocessed SWaT data with:
- Early stopping based on validation loss
- Model checkpointing
- TensorBoard logging
- Learning rate scheduling

Author: GenTwin Team
Date: February 2026
"""

import os
import sys
import numpy as np
import tensorflow as tf
import h5py
from datetime import datetime
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.vae_model import create_vae
from data_pipeline import load_processed_data


def train_vae(
    data_path: str = 'data/processed/swat_normal.h5',
    checkpoint_dir: str = 'models/checkpoints',
    log_dir: str = 'logs',
    epochs: int = 100,
    batch_size: int = 128,
    latent_dim: int = 32,
    beta: float = 0.5,
    learning_rate: float = 0.001,
    patience: int = 15
):
    """
    Train the VAE model on SWaT data.
    
    Args:
        data_path: Path to preprocessed HDF5 data
        checkpoint_dir: Directory to save model checkpoints
        log_dir: Directory for TensorBoard logs
        epochs: Maximum number of training epochs
        batch_size: Batch size for training
        latent_dim: Dimensionality of latent space
        beta: Beta-VAE weight parameter
        learning_rate: Initial learning rate
        patience: Early stopping patience
    """
    print("="*60)
    print("TRAINING SWAT VAE MODEL")
    print("="*60)
    
    # Create directories
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    
    # Load data
    print("\n1. Loading preprocessed data...")
    try:
        train_data, val_data, metadata = load_processed_data(data_path)
    except FileNotFoundError:
        print(f"Error: Preprocessed data not found at {data_path}")
        print("Please run data_pipeline.py first to preprocess the data.")
        return None
    
    # Get dimensions
    window_size = metadata['window_size']
    n_features = metadata['n_features']
    
    print(f"   Training samples: {train_data.shape}")
    print(f"   Validation samples: {val_data.shape}")
    print(f"   Window size: {window_size}")
    print(f"   Features: {n_features}")
    
    # Flatten sequences for VAE (treat each timestep independently)
    # Shape: (n_sequences, window_size, n_features) -> (n_sequences * window_size, n_features)
    train_flat = train_data.reshape(-1, n_features)
    val_flat = val_data.reshape(-1, n_features)
    
    print(f"   Flattened training: {train_flat.shape}")
    print(f"   Flattened validation: {val_flat.shape}")
    
    # Create VAE model
    print("\n2. Creating VAE model...")
    vae = create_vae(
        input_dim=int(n_features),
        latent_dim=int(latent_dim),
        beta=float(beta)
    )
    
    vae.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate))
    
    print(f"   Input dim: {n_features}")
    print(f"   Latent dim: {latent_dim}")
    print(f"   Beta: {beta}")
    print(f"   Learning rate: {learning_rate}")
    
    # Setup callbacks
    print("\n3. Setting up callbacks...")
    
    # Model checkpoint - save best model
    checkpoint_path = os.path.join(checkpoint_dir, 'best_vae.keras')
    checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
        filepath=checkpoint_path,
        monitor='val_total_loss',
        mode='min',
        save_best_only=True,
        save_weights_only=False,
        verbose=1
    )
    
    # Early stopping
    early_stopping = tf.keras.callbacks.EarlyStopping(
        monitor='val_reconstruction_loss',
        patience=patience,
        mode='min',
        restore_best_weights=True,
        verbose=1
    )
    
    # Learning rate reduction
    reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
        monitor='val_total_loss',
        factor=0.5,
        patience=7,
        min_lr=1e-6,
        mode='min',
        verbose=1
    )
    
    # TensorBoard
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    tensorboard_dir = os.path.join(log_dir, f'vae_{timestamp}')
    tensorboard_callback = tf.keras.callbacks.TensorBoard(
        log_dir=tensorboard_dir,
        histogram_freq=1,
        write_graph=True
    )
    
    callbacks = [
        checkpoint_callback,
        early_stopping,
        reduce_lr,
        tensorboard_callback
    ]
    
    # Train model
    print("\n4. Training VAE...")
    print(f"   Epochs: {epochs}")
    print(f"   Batch size: {batch_size}")
    print(f"   Early stopping patience: {patience}")
    print("\nTraining started...\n")
    
    history = vae.fit(
        train_flat,
        train_flat,  # VAE is autoencoder, so input = target
        validation_data=(val_flat, val_flat),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1
    )
    
    print("\n" + "="*60)
    print("TRAINING COMPLETE!")
    print("="*60)
    
    # Save final model
    final_model_path = os.path.join(checkpoint_dir, 'vae_final.keras')
    vae.save(final_model_path)
    print(f"\nFinal model saved to: {final_model_path}")
    print(f"Best model saved to: {checkpoint_path}")
    
    # Save training history
    history_path = os.path.join(checkpoint_dir, 'training_history.json')
    history_dict = {key: [float(val) for val in values] 
                   for key, values in history.history.items()}
    
    with open(history_path, 'w') as f:
        json.dump(history_dict, f, indent=2)
    
    print(f"Training history saved to: {history_path}")
    
    # Save metadata
    metadata_path = os.path.join(checkpoint_dir, 'model_metadata.json')
    model_metadata = {
        'input_dim': int(n_features),
        'latent_dim': int(latent_dim),
        'beta': float(beta),
        'window_size': int(window_size),
        'n_features': int(n_features),
        'sensor_cols': metadata['sensor_cols'],
        'training_samples': int(train_flat.shape[0]),
        'validation_samples': int(val_flat.shape[0]),
        'epochs_trained': len(history.history['total_loss']),
        'final_train_loss': float(history.history['total_loss'][-1]),
        'final_val_loss': float(history.history['val_total_loss'][-1]),
        'timestamp': timestamp
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(model_metadata, f, indent=2)
    
    print(f"Model metadata saved to: {metadata_path}")
    
    # Print final statistics
    print("\nFinal Training Statistics:")
    print(f"  Final training loss: {history.history['total_loss'][-1]:.4f}")
    print(f"  Final validation loss: {history.history['val_total_loss'][-1]:.4f}")
    print(f"  Final reconstruction loss: {history.history['reconstruction_loss'][-1]:.4f}")
    print(f"  Final KL loss: {history.history['kl_loss'][-1]:.4f}")
    print(f"  Best validation loss: {min(history.history['val_total_loss']):.4f}")
    print(f"  Epochs trained: {len(history.history['total_loss'])}")
    
    print(f"\nTensorBoard logs: {tensorboard_dir}")
    print("To view training progress, run:")
    print(f"  tensorboard --logdir {tensorboard_dir}")
    
    return vae, history


if __name__ == "__main__":
    # Train the VAE
    vae, history = train_vae(
        data_path='data/processed/swat_normal.h5',
        epochs=100,
        batch_size=128,
        latent_dim=32,
        beta=0.5,
        patience=15
    )
    
    if vae is not None:
        print("\nVAE training completed successfully!")
    else:
        print("\nVAE training failed. Please check error messages above.")
