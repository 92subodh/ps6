"""
Variational Autoencoder (VAE) Model for SWaT Sensor Data

This module implements a Beta-VAE architecture for learning latent representations
of normal SWaT operation, which can be used to generate synthetic attack scenarios.

Author: GenTwin Team
Date: February 2026
"""

import tensorflow as tf
from tensorflow.keras import layers
import keras
import numpy as np


@keras.saving.register_keras_serializable(package="SWaT")
class Sampling(layers.Layer):
    """
    Reparameterization trick for VAE sampling.
    
    Uses (z_mean, z_log_var) to sample z = mean + exp(log_var/2) * epsilon
    where epsilon ~ N(0, I)
    """
    
    def call(self, inputs):
        z_mean, z_log_var = inputs
        batch = tf.shape(z_mean)[0]
        dim = tf.shape(z_mean)[1]
        epsilon = tf.random.normal(shape=(batch, dim))
        return z_mean + tf.exp(0.5 * z_log_var) * epsilon


@keras.saving.register_keras_serializable(package="SWaT")
class SWaTVAE(tf.keras.Model):
    """
    Variational Autoencoder for SWaT sensor data.
    
    Architecture:
    - Encoder: Input(51) → Dense(128) → Dense(64) → [mu(32), logvar(32)]
    - Decoder: Latent(32) → Dense(64) → Dense(128) → Output(51)
    - Uses LeakyReLU activation
    - Includes batch normalization layers
    - Implements reparameterization trick
    
    Training:
    - Beta-VAE variant with configurable beta (default 0.5)
    - Loss = Reconstruction Loss + beta * KL Divergence
    """
    
    def __init__(self, 
                 input_dim: int = 51,
                 latent_dim: int = 32,
                 beta: float = 0.5,
                 name: str = "swat_vae",
                 **kwargs):
        """
        Initialize the VAE model.
        
        Args:
            input_dim: Number of input features (sensors/actuators)
            latent_dim: Dimensionality of latent space
            beta: Weight for KL divergence term (beta-VAE)
            name: Model name
        """
        super(SWaTVAE, self).__init__(name=name, **kwargs)
        
        # Ensure dimensions are Python integers (Keras 3.x requirement)
        self.input_dim = int(input_dim)
        self.latent_dim = int(latent_dim)
        self.beta = float(beta)
        
        # Build encoder
        self.encoder = self._build_encoder()
        
        # Build decoder
        self.decoder = self._build_decoder()
        
        # Metrics
        self.total_loss_tracker = tf.keras.metrics.Mean(name="total_loss")
        self.reconstruction_loss_tracker = tf.keras.metrics.Mean(name="reconstruction_loss")
        self.kl_loss_tracker = tf.keras.metrics.Mean(name="kl_loss")
    
    def _build_encoder(self):
        """Build the encoder network."""
        encoder_inputs = tf.keras.Input(shape=(self.input_dim,), name='encoder_input')
        
        # Layer 1: 128 units
        x = layers.Dense(128, name='encoder_dense_1')(encoder_inputs)
        x = layers.LeakyReLU(alpha=0.2, name='encoder_leaky_1')(x)
        x = layers.BatchNormalization(name='encoder_bn_1')(x)
        
        # Layer 2: 64 units
        x = layers.Dense(64, name='encoder_dense_2')(x)
        x = layers.LeakyReLU(alpha=0.2, name='encoder_leaky_2')(x)
        x = layers.BatchNormalization(name='encoder_bn_2')(x)
        
        # Latent space parameters
        z_mean = layers.Dense(self.latent_dim, name='z_mean')(x)
        z_log_var = layers.Dense(self.latent_dim, name='z_log_var')(x)
        
        # Sampling layer
        z = Sampling(name='sampling')([z_mean, z_log_var])
        
        encoder = tf.keras.Model(
            encoder_inputs, 
            [z_mean, z_log_var, z], 
            name='encoder'
        )
        
        return encoder
    
    def _build_decoder(self):
        """Build the decoder network."""
        latent_inputs = tf.keras.Input(shape=(self.latent_dim,), name='decoder_input')
        
        # Layer 1: 64 units
        x = layers.Dense(64, name='decoder_dense_1')(latent_inputs)
        x = layers.LeakyReLU(alpha=0.2, name='decoder_leaky_1')(x)
        x = layers.BatchNormalization(name='decoder_bn_1')(x)
        
        # Layer 2: 128 units
        x = layers.Dense(128, name='decoder_dense_2')(x)
        x = layers.LeakyReLU(alpha=0.2, name='decoder_leaky_2')(x)
        x = layers.BatchNormalization(name='decoder_bn_2')(x)
        
        # Output layer
        decoder_outputs = layers.Dense(self.input_dim, activation='linear', name='decoder_output')(x)
        
        decoder = tf.keras.Model(
            latent_inputs,
            decoder_outputs,
            name='decoder'
        )
        
        return decoder
    
    @property
    def metrics(self):
        """Return metrics tracked during training."""
        return [
            self.total_loss_tracker,
            self.reconstruction_loss_tracker,
            self.kl_loss_tracker,
        ]
    
    def call(self, inputs, training=None):
        """Forward pass through the VAE."""
        z_mean, z_log_var, z = self.encoder(inputs, training=training)
        reconstruction = self.decoder(z, training=training)
        return reconstruction
    
    def encode(self, inputs):
        """
        Encode inputs to latent space.
        
        Args:
            inputs: Input data (batch_size, input_dim)
            
        Returns:
            Tuple of (z_mean, z_log_var, z)
        """
        return self.encoder(inputs)
    
    def decode(self, z):
        """
        Decode latent vectors to input space.
        
        Args:
            z: Latent vectors (batch_size, latent_dim)
            
        Returns:
            Reconstructed data (batch_size, input_dim)
        """
        return self.decoder(z)
    
    def train_step(self, data):
        """Custom training step with VAE loss."""
        # Unpack data for Keras 3.x compatibility
        if isinstance(data, tuple):
            data = data[0]  # Extract x from (x, y) tuple
        
        with tf.GradientTape() as tape:
            # Forward pass
            z_mean, z_log_var, z = self.encoder(data)
            reconstruction = self.decoder(z)
            
            # Reconstruction loss (MSE)
            reconstruction_loss = tf.reduce_mean(
                tf.reduce_sum(
                    tf.square(data - reconstruction),
                    axis=1
                )
            )
            
            # KL divergence loss
            kl_loss = -0.5 * tf.reduce_mean(
                tf.reduce_sum(
                    1 + z_log_var - tf.square(z_mean) - tf.exp(z_log_var),
                    axis=1
                )
            )
            
            # Total loss with beta weighting
            total_loss = reconstruction_loss + self.beta * kl_loss
        
        # Compute gradients and update weights
        grads = tape.gradient(total_loss, self.trainable_weights)
        self.optimizer.apply_gradients(zip(grads, self.trainable_weights))
        
        # Update metrics
        self.total_loss_tracker.update_state(total_loss)
        self.reconstruction_loss_tracker.update_state(reconstruction_loss)
        self.kl_loss_tracker.update_state(kl_loss)
        
        return {
            "total_loss": self.total_loss_tracker.result(),
            "reconstruction_loss": self.reconstruction_loss_tracker.result(),
            "kl_loss": self.kl_loss_tracker.result(),
        }
    
    def test_step(self, data):
        """Custom test step."""
        # Unpack data for Keras 3.x compatibility
        if isinstance(data, tuple):
            data = data[0]  # Extract x from (x, y) tuple
        
        # Forward pass
        z_mean, z_log_var, z = self.encoder(data)
        reconstruction = self.decoder(z)
        
        # Reconstruction loss
        reconstruction_loss = tf.reduce_mean(
            tf.reduce_sum(
                tf.square(data - reconstruction),
                axis=1
            )
        )
        
        # KL divergence loss
        kl_loss = -0.5 * tf.reduce_mean(
            tf.reduce_sum(
                1 + z_log_var - tf.square(z_mean) - tf.exp(z_log_var),
                axis=1
            )
        )
        
        # Total loss
        total_loss = reconstruction_loss + self.beta * kl_loss
        
        # Update metrics
        self.total_loss_tracker.update_state(total_loss)
        self.reconstruction_loss_tracker.update_state(reconstruction_loss)
        self.kl_loss_tracker.update_state(kl_loss)
        
        return {
            "total_loss": self.total_loss_tracker.result(),
            "reconstruction_loss": self.reconstruction_loss_tracker.result(),
            "kl_loss": self.kl_loss_tracker.result(),
        }
    
    def get_config(self):
        """Get model configuration for serialization."""
        return {
            'input_dim': self.input_dim,
            'latent_dim': self.latent_dim,
            'beta': self.beta,
        }


def create_vae(input_dim: int = 51, 
               latent_dim: int = 32, 
               beta: float = 0.5) -> SWaTVAE:
    """
    Factory function to create a VAE model.
    
    Args:
        input_dim: Number of input features
        latent_dim: Dimensionality of latent space
        beta: Beta-VAE weight parameter
        
    Returns:
        Compiled SWaTVAE model
    """
    vae = SWaTVAE(
        input_dim=input_dim,
        latent_dim=latent_dim,
        beta=beta
    )
    
    vae.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001))
    
    return vae


if __name__ == "__main__":
    # Test VAE creation
    print("Creating VAE model...")
    vae = create_vae(input_dim=51, latent_dim=32, beta=0.5)
    
    # Print model summary
    print("\nEncoder Summary:")
    vae.encoder.summary()
    
    print("\nDecoder Summary:")
    vae.decoder.summary()
    
    # Test with dummy data
    print("\nTesting with dummy data...")
    dummy_input = tf.random.normal((32, 51))  # Batch of 32 samples
    
    # Test encoding
    z_mean, z_log_var, z = vae.encode(dummy_input)
    print(f"Encoded shape - z_mean: {z_mean.shape}, z: {z.shape}")
    
    # Test decoding
    reconstruction = vae.decode(z)
    print(f"Reconstruction shape: {reconstruction.shape}")
    
    # Test full forward pass
    output = vae(dummy_input)
    print(f"Full VAE output shape: {output.shape}")
    
    print("\nVAE model test successful!")
