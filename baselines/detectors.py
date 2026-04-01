"""
Baseline Anomaly Detection Methods

Implements standard anomaly detection techniques for comparison:
- Threshold-based detection
- Isolation Forest
- One-Class SVM
- LSTM Autoencoder

Author: GenTwin Team
Date: February 2026
"""

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, f1_score
import tensorflow as tf
from typing import Dict, Tuple
import pickle


class ThresholdDetector:
    """Simple threshold-based anomaly detector (>3σ from mean)."""
    
    def __init__(self, n_sigma: float = 3.0):
        self.n_sigma = n_sigma
        self.mean = None
        self.std = None
    
    def fit(self, X: np.ndarray):
        """Fit on normal data."""
        self.mean = np.mean(X, axis=0)
        self.std = np.std(X, axis=0)
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict anomalies (1 = anomaly, 0 = normal)."""
        if self.mean is None:
            raise ValueError("Model not fitted yet")
        
        # Calculate z-scores
        z_scores = np.abs((X - self.mean) / (self.std + 1e-8))
        
        # Any feature beyond threshold = anomaly
        anomalies = np.any(z_scores > self.n_sigma, axis=1).astype(int)
        
        return anomalies
    
    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """Return anomaly scores."""
        z_scores = np.abs((X - self.mean) / (self.std + 1e-8))
        return np.max(z_scores, axis=1)


class IsolationForestDetector:
    """Isolation Forest anomaly detector."""
    
    def __init__(self, contamination: float = 0.1, random_state: int = 42):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100
        )
    
    def fit(self, X: np.ndarray):
        """Fit on normal data."""
        self.model.fit(X)
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict anomalies (1 = anomaly, 0 = normal)."""
        # sklearn returns -1 for anomalies, 1 for normal
        predictions = self.model.predict(X)
        return (predictions == -1).astype(int)
    
    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """Return anomaly scores (more negative = more anomalous)."""
        return -self.model.score_samples(X)


class OneClassSVMDetector:
    """One-Class SVM anomaly detector."""
    
    def __init__(self, nu: float = 0.1, gamma: str = 'auto', kernel: str = 'rbf', max_samples: int = 10000):
        self.model = OneClassSVM(nu=nu, gamma=gamma, kernel=kernel)
        self.max_samples = max_samples
    
    def fit(self, X: np.ndarray):
        """Fit on normal data (subsamples if too large for efficiency)."""
        # Subsample if dataset too large (SVM is O(n^2) with RBF kernel)
        if len(X) > self.max_samples:
            print(f"    Subsampling {len(X)} samples to {self.max_samples} for SVM training...")
            indices = np.random.choice(len(X), self.max_samples, replace=False)
            X_train = X[indices]
        else:
            X_train = X
        
        self.model.fit(X_train)
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict anomalies (1 = anomaly, 0 = normal)."""
        predictions = self.model.predict(X)
        return (predictions == -1).astype(int)
    
    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """Return anomaly scores."""
        return -self.model.score_samples(X)


class LSTMAutoencoderDetector:
    """LSTM Autoencoder for sequence anomaly detection."""
    
    def __init__(self, 
                 input_dim: int,
                 encoding_dim: int = 32,
                 lstm_units: int = 64,
                 threshold_percentile: float = 95):
        self.input_dim = int(input_dim)  # Ensure Python int for Keras 3
        self.encoding_dim = int(encoding_dim)
        self.lstm_units = int(lstm_units)
        self.threshold_percentile = threshold_percentile
        self.model = None
        self.threshold = None
    
    def _build_model(self):
        """Build LSTM autoencoder."""
        # Encoder
        inputs = tf.keras.Input(shape=(None, self.input_dim))
        encoded = tf.keras.layers.LSTM(self.lstm_units, return_sequences=False)(inputs)
        encoded = tf.keras.layers.Dense(self.encoding_dim)(encoded)
        
        # Decoder
        decoded = tf.keras.layers.RepeatVector(1)(encoded)
        decoded = tf.keras.layers.LSTM(self.lstm_units, return_sequences=True)(decoded)
        decoded = tf.keras.layers.TimeDistributed(tf.keras.layers.Dense(self.input_dim))(decoded)
        
        # Model
        model = tf.keras.Model(inputs, decoded)
        model.compile(optimizer='adam', loss='mse')
        
        return model
    
    def fit(self, X: np.ndarray, epochs: int = 20, batch_size: int = 128):
        """Fit on normal data."""
        print(f"    Building LSTM-AE model (input_dim={self.input_dim})...")
        self.model = self._build_model()
        
        # Reshape for LSTM if needed
        if len(X.shape) == 2:
            X = X.reshape((X.shape[0], 1, X.shape[1]))
        
        print(f"    Training LSTM-AE on {len(X)} samples for {epochs} epochs...")
        self.model.fit(
            X, X,
            epochs=epochs,
            batch_size=batch_size,
            verbose=1  # Show training progress
        )
        
        # Calculate threshold from training data
        print("    Calculating anomaly threshold...")
        train_errors = self.score_samples(X)
        self.threshold = np.percentile(train_errors, self.threshold_percentile)
        
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict anomalies (1 = anomaly, 0 = normal)."""
        scores = self.score_samples(X)
        return (scores > self.threshold).astype(int)
    
    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """Return reconstruction errors."""
        if len(X.shape) == 2:
            X = X.reshape((X.shape[0], 1, X.shape[1]))
        
        reconstructed = self.model.predict(X, verbose=0)
        errors = np.mean(np.square(X - reconstructed), axis=(1, 2))
        
        return errors


class BaselineEvaluator:
    """Evaluate multiple baseline detectors."""
    
    def __init__(self, detectors: Dict = None):
        if detectors is None:
            self.detectors = {}
        else:
            self.detectors = detectors
    
    def add_detector(self, name: str, detector):
        """Add a detector to evaluate."""
        self.detectors[name] = detector
    
    def train_all(self, X_train: np.ndarray):
        """Train all detectors."""
        print("Training baseline detectors...")
        for name, detector in self.detectors.items():
            print(f"  Training {name}...")
            detector.fit(X_train)
        print("Training complete!")
    
    def evaluate_all(self, 
                    X_test: np.ndarray, 
                    y_test: np.ndarray) -> Dict:
        """
        Evaluate all detectors.
        
        Args:
            X_test: Test data
            y_test: True labels (0=normal, 1=anomaly)
            
        Returns:
            Dictionary of results
        """
        results = {}
        
        for name, detector in self.detectors.items():
            print(f"Evaluating {name}...")
            
            # Predict
            predictions = detector.predict(X_test)
            
            # Calculate metrics
            precision = precision_score(y_test, predictions, zero_division=0)
            recall = recall_score(y_test, predictions, zero_division=0)
            f1 = f1_score(y_test, predictions, zero_division=0)
            
            # Detection rate by severity (if available)
            detection_rate = np.mean(predictions[y_test == 1]) * 100
            fpr = np.mean(predictions[y_test == 0]) * 100
            
            results[name] = {
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'detection_rate': detection_rate,
                'false_positive_rate': fpr,
                'predictions': predictions
            }
        
        return results
    
    def save(self, filepath: str):
        """Save trained detectors."""
        with open(filepath, 'wb') as f:
            pickle.dump(self, f)
    
    @staticmethod
    def load(filepath: str):
        """Load trained detectors."""
        with open(filepath, 'rb') as f:
            return pickle.load(f)


def create_baseline_detectors(input_dim: int, svm_max_samples: int = 10000) -> Dict:
    """
    Create standard set of baseline detectors.
    
    Args:
        input_dim: Number of input features
        svm_max_samples: Max samples for SVM training (to avoid slow training)
        
    Returns:
        Dictionary of detector instances
    """
    detectors = {
        'Threshold (3σ)': ThresholdDetector(n_sigma=3.0),
        'Isolation Forest': IsolationForestDetector(contamination=0.1),
        'One-Class SVM': OneClassSVMDetector(nu=0.1, max_samples=svm_max_samples),
        'LSTM Autoencoder': LSTMAutoencoderDetector(input_dim=input_dim)
    }
    
    return detectors


if __name__ == "__main__":
    # Test detectors with dummy data
    print("Testing baseline detectors...")
    
    # Generate dummy data
    np.random.seed(42)
    X_train = np.random.randn(1000, 51)  # Normal data
    X_test_normal = np.random.randn(200, 51)  # Normal test
    X_test_anomaly = np.random.randn(200, 51) + 5  # Anomalous test
    
    X_test = np.vstack([X_test_normal, X_test_anomaly])
    y_test = np.array([0] * 200 + [1] * 200)
    
    # Create and train detectors
    detectors = create_baseline_detectors(input_dim=51, svm_max_samples=1000)
    evaluator = BaselineEvaluator(detectors)
    evaluator.train_all(X_train)
    
    # Evaluate
    results = evaluator.evaluate_all(X_test, y_test)
    
    # Print results
    print("\nResults:")
    for name, metrics in results.items():
        print(f"\n{name}:")
        print(f"  Precision: {metrics['precision']:.3f}")
        print(f"  Recall: {metrics['recall']:.3f}")
        print(f"  F1-Score: {metrics['f1_score']:.3f}")
        print(f"  Detection Rate: {metrics['detection_rate']:.1f}%")
    
    print("\nBaseline detector test complete!")
