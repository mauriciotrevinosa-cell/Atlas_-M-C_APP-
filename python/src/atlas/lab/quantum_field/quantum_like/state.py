"""
Quantum-Like State Representation (Classical CPU)
"""
from __future__ import annotations
from typing import Optional
import numpy as np


class QuantumLikeState:
    """
    Minimal classical representation of a quantum-like state vector.
    Amplitudes are complex-valued; norm is preserved by normalise().
    """

    def __init__(self, n_dims: int = 2, amplitudes: Optional[np.ndarray] = None):
        if amplitudes is not None:
            self.amplitudes = np.asarray(amplitudes, dtype=complex)
        else:
            self.amplitudes = np.zeros(n_dims, dtype=complex)
            self.amplitudes[0] = 1.0  # default: |0⟩ basis state

    @property
    def n_dims(self) -> int:
        return len(self.amplitudes)

    def normalise(self) -> "QuantumLikeState":
        norm = np.linalg.norm(self.amplitudes)
        if norm > 0:
            self.amplitudes = self.amplitudes / norm
        return self

    def probabilities(self) -> np.ndarray:
        return np.abs(self.amplitudes) ** 2

    def __repr__(self) -> str:
        return f"QuantumLikeState(n_dims={self.n_dims}, norm={np.linalg.norm(self.amplitudes):.4f})"
