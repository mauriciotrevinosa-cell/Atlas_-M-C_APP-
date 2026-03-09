"""
Physics-Inspired Market Models
================================
Reference: quant-traderr-lab (MIT license) — Ising, Lyapunov, Lempel-Ziv pipelines
           Bouchaud & Potters (2003) "Theory of Financial Risk and Derivative Pricing"

Modules:
  IsingMarketModel    — Phase transition model (ferromagnetism → market sentiment)
  LyapunovEstimator   — Chaos measure via phase-space reconstruction
  LempelZivComplexity — Market randomness / information entropy estimator

─────────────────────────────────────────────────────────────────────────────
ISING MODEL:
  Spins σᵢ ∈ {+1, -1} model agent sentiment (bullish/bearish).
  Energy: E = -J·Σ σᵢσⱼ  (J = coupling; high T = random, low T = ordered)
  Metropolis-Hastings MC finds equilibrium magnetization M = <σ>.
  Critical temperature: Tc ≈ 2J/ln(1+√2) ≈ 2.269J (2D Ising)
  Interpretation:
    M → +1 : bull market (consensus up)
    M → -1 : bear market (consensus down)
    M ≈ 0  : transitional / uncertain regime

LYAPUNOV EXPONENT:
  Measures divergence of nearby trajectories → market predictability.
  Positive λ₁ → chaotic (unpredictable)
  Negative λ₁ → ordered / predictable
  Uses Time Delay Embedding (Takens theorem) + Method of Analogues.

LEMPEL-ZIV COMPLEXITY:
  Kolmogorov-inspired complexity measure for financial time series.
  High LZ → random walk (efficient market)
  Low LZ  → structure present (exploitable inefficiency)
  LZc ∈ [0, 1] after normalization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  ISING MARKET MODEL
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class IsingResult:
    """Output of Ising market simulation."""
    temperature:    float
    magnetization:  float   # M ∈ [-1, +1]
    energy:         float   # per spin
    susceptibility: float   # dM/dT — peaks at Tc (phase transition)
    regime:         str     # 'BULL' | 'BEAR' | 'TRANSITION'
    critical_temp:  float
    is_critical:    bool    # |T - Tc| < 0.1·Tc

    def to_dict(self) -> Dict:
        return {
            'temperature':    round(self.temperature, 4),
            'magnetization':  round(self.magnetization, 4),
            'energy':         round(self.energy, 6),
            'susceptibility': round(self.susceptibility, 4),
            'regime':         self.regime,
            'critical_temp':  round(self.critical_temp, 4),
            'is_critical':    self.is_critical,
        }


class IsingMarketModel:
    """
    2D Ising model of financial market sentiment.

    Maps volatility and return data to spin dynamics.
    Temperature T = σ / σ_long × J (higher vol → higher T → more disorder).

    Parameters
    ----------
    size : lattice side (total spins = size²; default 20 → 400 agents)
    J    : coupling constant (default 1.0; higher = stronger herding)
    """

    def __init__(self, size: int = 20, J: float = 1.0):
        self.size = size
        self.J    = J
        self._critical_temp = 2.0 * J / np.log(1.0 + np.sqrt(2.0))  # 2D Ising Tc

        # Initialize random spins
        self._spins = np.random.choice([-1, 1], size=(size, size))

    @property
    def critical_temperature(self) -> float:
        return self._critical_temp

    # ── Metropolis-Hastings simulation ────────────────────────────────────

    def run(
        self,
        temperature: float,
        n_steps:     int = 5_000,
        burn_in:     int = 1_000,
        measure_every: int = 10,
    ) -> IsingResult:
        """
        Run Metropolis-Hastings MC to equilibrium.

        Parameters
        ----------
        temperature  : reduced temperature T (in units of J/k_B)
        n_steps      : total MC sweeps
        burn_in      : steps before measurement begins
        measure_every: record every N steps

        Returns
        -------
        IsingResult with magnetization, energy, susceptibility
        """
        T = max(temperature, 0.01)
        N = self.size ** 2

        mag_history = []
        ene_history = []

        spins = self._spins.copy()

        for step in range(n_steps + burn_in):
            # Single spin flip
            i = np.random.randint(self.size)
            j = np.random.randint(self.size)

            # Periodic boundary conditions
            nbrs_sum = (
                spins[(i+1) % self.size, j] + spins[(i-1) % self.size, j] +
                spins[i, (j+1) % self.size] + spins[i, (j-1) % self.size]
            )

            dE = 2.0 * self.J * spins[i, j] * nbrs_sum

            # Accept/reject
            if dE <= 0 or np.random.random() < np.exp(-dE / T):
                spins[i, j] *= -1

            if step >= burn_in and step % measure_every == 0:
                M = float(spins.mean())
                E = float(-self.J * np.sum(
                    spins * (np.roll(spins, 1, axis=0) + np.roll(spins, 1, axis=1))
                )) / N
                mag_history.append(M)
                ene_history.append(E)

        self._spins = spins

        mag_arr = np.array(mag_history)
        ene_arr = np.array(ene_history)

        M_mean  = float(np.mean(np.abs(mag_arr)))
        E_mean  = float(np.mean(ene_arr))
        # Susceptibility χ = (N/T) × Var[M]
        chi     = float((N / T) * np.var(mag_arr))

        # Regime classification
        if M_mean > 0.4:
            regime = 'BULL'
        elif M_mean < -0.4:
            regime = 'BEAR'
        else:
            regime = 'TRANSITION'

        is_crit = abs(T - self._critical_temp) < 0.1 * self._critical_temp

        return IsingResult(
            temperature    = T,
            magnetization  = M_mean,
            energy         = E_mean,
            susceptibility = chi,
            regime         = regime,
            critical_temp  = self._critical_temp,
            is_critical    = is_crit,
        )

    def map_market_data(
        self,
        returns: np.ndarray,
        window:  int = 20,
    ) -> np.ndarray:
        """
        Map returns to temperature series for regime tracking.

        T(t) = σ(t) / σ_long × Tc
        Higher volatility → higher T (closer to phase transition).
        """
        r      = np.asarray(returns, dtype=np.float64)
        vol    = np.array([r[max(0, i-window):i+1].std() for i in range(len(r))])
        sigma_long = vol.mean() + 1e-9
        temps  = vol / sigma_long * self._critical_temp
        return temps

    def temperature_sweep(
        self,
        t_min:   float = 0.5,
        t_max:   float = 5.0,
        n_temps: int   = 20,
        n_steps: int   = 3_000,
    ) -> List[IsingResult]:
        """
        Sweep temperature range to identify phase transition point.

        Returns list of IsingResult — magnetization drops near Tc.
        """
        results = []
        for T in np.linspace(t_min, t_max, n_temps):
            self._spins = np.random.choice([-1, 1], size=(self.size, self.size))
            results.append(self.run(T, n_steps=n_steps))
        return results

    def __repr__(self) -> str:
        return f'IsingMarketModel(size={self.size}, J={self.J}, Tc={self._critical_temp:.3f})'


# ══════════════════════════════════════════════════════════════════════════════
#  LYAPUNOV EXPONENT
# ══════════════════════════════════════════════════════════════════════════════

class LyapunovEstimator:
    """
    Largest Lyapunov Exponent (LLE) estimator for financial time series.

    Uses Time Delay Embedding (Takens theorem) + Method of Analogues
    (nearest-neighbor divergence tracking).

    Parameters
    ----------
    tau     : time delay (embedding lag), default 1
    dim     : embedding dimension, default 3
    min_sep : minimum temporal separation for nearest neighbor search
    """

    def __init__(
        self,
        tau:     int = 1,
        dim:     int = 3,
        min_sep: int = 5,
    ):
        self.tau     = tau
        self.dim     = dim
        self.min_sep = min_sep

    def embed(self, x: np.ndarray) -> np.ndarray:
        """
        Phase space reconstruction (Takens embedding).

        Returns (M, dim) matrix where M = N - (dim-1)×tau.
        """
        x = np.asarray(x, dtype=np.float64)
        N = len(x)
        M = N - (self.dim - 1) * self.tau

        if M <= 0:
            raise ValueError(
                f'LyapunovEstimator: time series too short for embedding. '
                f'Need N > (dim-1)×tau = {(self.dim-1)*self.tau}'
            )

        embedded = np.empty((M, self.dim))
        for d in range(self.dim):
            embedded[:, d] = x[d * self.tau: d * self.tau + M]

        return embedded

    def estimate(
        self,
        x:             np.ndarray,
        steps:         int = 20,
        n_neighbors:   int = 10,
    ) -> Dict:
        """
        Estimate the Largest Lyapunov Exponent using Rosenstein's method.

        Algorithm:
          1. Embed time series in phase space (Takens)
          2. For each point, find nearest neighbor (min temporal separation)
          3. Track divergence: d(t) ≈ d₀ × exp(λ₁ × t)
          4. Estimate λ₁ via linear regression on log(d(t)) vs t

        Returns
        -------
        dict with: lyapunov, is_chaotic, phase_space (for visualization)
        """
        x   = np.asarray(x, dtype=np.float64)
        x   = (x - x.mean()) / (x.std() + 1e-9)  # standardize

        try:
            embedded = self.embed(x)
        except ValueError as e:
            return {'error': str(e), 'lyapunov': 0.0, 'is_chaotic': False}

        M  = len(embedded)
        K  = min(n_neighbors, M // 4)
        T  = min(steps, M // 4)

        # KD-tree nearest neighbors (brute force for small M)
        divergences = []
        valid_refs  = []

        for i in range(M - T):
            # Find K nearest neighbors with min temporal separation
            dists = np.full(M, np.inf)
            for j in range(M - T):
                if abs(i - j) >= self.min_sep:
                    dists[j] = float(np.linalg.norm(embedded[i] - embedded[j]))

            nn_idx = np.argpartition(dists, K)[:K]
            nn_idx = nn_idx[dists[nn_idx] < np.inf]

            if len(nn_idx) == 0:
                continue

            # Average log divergence over forecast horizon
            d0   = np.mean([dists[j] for j in nn_idx])
            if d0 < 1e-10:
                continue

            log_div = []
            for t in range(T):
                if i + t >= M or all(j + t >= M for j in nn_idx):
                    break
                valid_nn = [j for j in nn_idx if j + t < M]
                if not valid_nn:
                    break
                d_t = np.mean([np.linalg.norm(embedded[i+t] - embedded[j+t]) for j in valid_nn])
                if d_t > 1e-10:
                    log_div.append(np.log(d_t / d0))

            if len(log_div) > 3:
                divergences.append(log_div)
                valid_refs.append(i)

        if not divergences:
            return {
                'lyapunov':    0.0,
                'is_chaotic':  False,
                'error':       'Not enough valid reference points for LLE estimation.',
                'phase_space': embedded,
            }

        # Average divergence curve and fit line
        max_len = min(len(d) for d in divergences)
        div_arr = np.array([d[:max_len] for d in divergences]).mean(axis=0)

        t_vals  = np.arange(max_len, dtype=float)
        # Linear fit: log_div ≈ λ₁ × t + const
        coeffs  = np.polyfit(t_vals, div_arr, 1)
        lam1    = float(coeffs[0])  # slope = λ₁

        # R² of the fit
        y_pred  = np.polyval(coeffs, t_vals)
        ss_res  = float(np.sum((div_arr - y_pred) ** 2))
        ss_tot  = float(np.sum((div_arr - div_arr.mean()) ** 2))
        r2      = 1.0 - ss_res / (ss_tot + 1e-9)

        return {
            'lyapunov':         round(lam1, 6),
            'is_chaotic':       lam1 > 0,
            'r_squared':        round(r2, 4),
            'interpretation':   self._interpret(lam1),
            'divergence_curve': div_arr.tolist(),
            'phase_space':      embedded,
            'n_valid_refs':     len(valid_refs),
        }

    @staticmethod
    def _interpret(lam: float) -> str:
        if lam > 0.5:  return 'HIGHLY CHAOTIC — unpredictable market'
        if lam > 0.1:  return 'MILDLY CHAOTIC — some structure present'
        if lam > -0.1: return 'BORDERLINE — near random walk'
        return 'ORDERED — mean-reverting structure detected'

    def __repr__(self) -> str:
        return f'LyapunovEstimator(τ={self.tau}, dim={self.dim})'


# ══════════════════════════════════════════════════════════════════════════════
#  LEMPEL-ZIV COMPLEXITY
# ══════════════════════════════════════════════════════════════════════════════

class LempelZivComplexity:
    """
    Lempel-Ziv Complexity (LZc) — market randomness measure.

    Based on the string complexity algorithm from Lempel & Ziv (1976).
    Applied to binarized financial time series:
      - Binary encoding: 1 if return > 0 (up), 0 if return ≤ 0 (down)
      - LZc(binaryString) → count of distinct substrings

    Normalized LZc ∈ [0, 1]:
      LZc → 1.0: pure random walk (maximum complexity = efficient market)
      LZc → 0.0: pure periodicity (minimum complexity = predictable)

    Rolling LZc: detects regime shifts in market efficiency.

    Reference:
      Lempel, A., Ziv, J. (1976). "On the Complexity of Finite Sequences". IEEE.
      Alvarez-Ramirez, J. et al. (2012). "Time-varying Hurst exponent for US stock markets"
    """

    @staticmethod
    def encode_binary(
        x:          np.ndarray,
        method:     str = 'sign',
        threshold:  float = 0.0,
    ) -> str:
        """
        Convert time series to binary string.

        Methods:
          'sign'   : 1 if x > threshold else 0
          'median' : 1 if x > median(x) else 0
          'zscore' : 1 if z-score > 0 else 0
        """
        x = np.asarray(x, dtype=np.float64)

        if method == 'median':
            threshold = float(np.median(x))
        elif method == 'zscore':
            x = (x - x.mean()) / (x.std() + 1e-9)
            threshold = 0.0

        return ''.join('1' if v > threshold else '0' for v in x)

    @staticmethod
    def lz76(binary_string: str) -> int:
        """
        Lempel-Ziv 76 complexity (LZ76).

        Counts the number of distinct substrings added to the vocabulary
        as the string is scanned left to right.

        Time complexity: O(N²) naive; O(N log N) with suffix trees.
        This implementation is O(N²) — sufficient for N < 10,000.
        """
        s   = binary_string
        n   = len(s)
        if n == 0:
            return 0

        vocab = set()
        i, k, l = 0, 1, 1
        c = 1  # complexity count

        while k + l <= n:
            if s[i + l - 1: i + l] not in s[k: k + l]:
                vocab.add(s[k: k + l])
                c += 1
                i  = k + l
                k  = i
                l  = 1
            else:
                l += 1

        return c

    @staticmethod
    def normalized_lzc(binary_string) -> float:
        """
        Normalize LZ complexity to [0, 1].

        LZc_norm = c(N) × log₂(N) / N
        (approaches 1 for random binary strings of length N)

        Accepts either a binary string or a numpy ndarray (auto-encoded via sign method).
        """
        # Accept numpy arrays — auto-encode via sign method
        if isinstance(binary_string, np.ndarray):
            binary_string = ''.join('1' if v > 0 else '0' for v in binary_string)

        n = len(binary_string)
        if n < 2:
            return 0.0

        c = LempelZivComplexity.lz76(binary_string)
        # Theoretical max: c_max ≈ N / log₂(N)
        c_max = n / (np.log2(n) + 1e-9)
        return min(float(c / c_max), 1.0)

    def compute(
        self,
        returns:    np.ndarray,
        method:     str = 'sign',
        normalize:  bool = True,
    ) -> Dict:
        """
        Compute Lempel-Ziv complexity of a return series.

        Parameters
        ----------
        returns   : price return series
        method    : binarization method ('sign', 'median', 'zscore')
        normalize : if True, return normalized LZc ∈ [0, 1]

        Returns
        -------
        dict with: lzc, binary_string, n, interpretation
        """
        r      = np.asarray(returns, dtype=np.float64)
        binstr = self.encode_binary(r, method=method)

        if normalize:
            lzc = self.normalized_lzc(binstr)
        else:
            lzc = float(self.lz76(binstr))

        return {
            'lzc':            round(lzc, 4),
            'n':              len(r),
            'method':         method,
            'normalized':     normalize,
            'interpretation': self._interpret(lzc, normalize),
            'binary_sample':  binstr[:50] + '...',
        }

    def rolling_lzc(
        self,
        returns: np.ndarray,
        window:  int = 60,
        step:    int = 1,
    ) -> np.ndarray:
        """
        Compute rolling normalized LZc over a sliding window.

        Useful for detecting regime changes in market efficiency.
        Drops in LZc suggest exploitable structure emerging.
        """
        r   = np.asarray(returns, dtype=np.float64)
        N   = len(r)
        out = np.full(N, np.nan)

        for i in range(window, N, step):
            window_data = r[i - window: i]
            binstr      = self.encode_binary(window_data)
            out[i]      = self.normalized_lzc(binstr)

        return out

    @staticmethod
    def _interpret(lzc: float, normalized: bool = True) -> str:
        if not normalized:
            return f'Raw LZc = {lzc:.0f} substrings'

        if lzc > 0.85: return 'RANDOM WALK — highly efficient, hard to predict'
        if lzc > 0.70: return 'NEAR-RANDOM — low predictability'
        if lzc > 0.55: return 'MODERATE STRUCTURE — some patterns exploitable'
        if lzc > 0.40: return 'STRUCTURED — mean reversion / trends present'
        return 'HIGHLY ORDERED — strong recurring patterns'

    def __repr__(self) -> str:
        return 'LempelZivComplexity()'
