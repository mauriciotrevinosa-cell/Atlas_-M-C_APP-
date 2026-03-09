"""
Atlas Quantitative Algorithms Library
======================================
Production-ready implementations of the algorithms defined in:
  docs/ALGORITHMS_LIBRARY.md

Plus advanced methods extracted from quant-traderr-lab (MIT licensed):
  Ornstein-Uhlenbeck, Wavelet Transform, RMT Filter, Market Physics,
  Fisher Transform, Singular Spectrum Analysis (SSA), Yield Curve (Nelson-Siegel)

Modules:
  black_litterman   — Bayesian portfolio optimization (Black-Litterman 1992)
  execution_algos   — TWAP / VWAP / Almgren-Chriss optimal execution
  ornstein_uhlenbeck— Mean-reversion process (pairs trading, rate models)
  wavelet_analysis  — Continuous & discrete wavelet transforms (CWT/DWT)
  rmt_filter        — Random Matrix Theory correlation filter (Marchenko-Pastur)
  market_physics    — Ising Model, Lyapunov Exponent, Lempel-Ziv Complexity
  fisher_transform  — Fisher Transform oscillator + Shannon Entropy
  ssa               — Singular Spectrum Analysis (decompose/denoise/forecast)
  yield_curve       — Nelson-Siegel(-Svensson) term structure + curve metrics
"""

from .black_litterman    import BlackLittermanModel
from .execution_algos    import TWAPAlgo, VWAPAlgo, AlmgrenChrissOptimizer
from .ornstein_uhlenbeck import OrnsteinUhlenbeckProcess, OUFitter
from .wavelet_analysis   import WaveletAnalyzer
from .rmt_filter         import RMTFilter, MarchenkoPastur
from .market_physics     import IsingMarketModel, LyapunovEstimator, LempelZivComplexity
from .fisher_transform   import FisherTransform, ShannonEntropy
from .ssa                import SSAnalyzer
from .yield_curve        import NelsonSiegel, NelsonSiegelSvensson, YieldCurveAnalyzer

__all__ = [
    # Portfolio
    'BlackLittermanModel',
    # Execution
    'TWAPAlgo', 'VWAPAlgo', 'AlmgrenChrissOptimizer',
    # Mean-reversion
    'OrnsteinUhlenbeckProcess', 'OUFitter',
    # Signal processing
    'WaveletAnalyzer',
    # Portfolio noise reduction
    'RMTFilter', 'MarchenkoPastur',
    # Physics-inspired
    'IsingMarketModel', 'LyapunovEstimator', 'LempelZivComplexity',
    # Information-theoretic
    'FisherTransform', 'ShannonEntropy',
    # Spectral decomposition
    'SSAnalyzer',
    # Term structure
    'NelsonSiegel', 'NelsonSiegelSvensson', 'YieldCurveAnalyzer',
]
