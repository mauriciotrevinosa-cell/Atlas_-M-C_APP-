"""
Atlas ARIA Trader — Quantitative Learning Machine
Combines: Technical + Factor + Fundamental + Momentum + Regime signals
into a single elite composite score with trade predictions.
"""

from .composite_scorer import CompositeScorer, TraderResult

__all__ = ["CompositeScorer", "TraderResult"]
