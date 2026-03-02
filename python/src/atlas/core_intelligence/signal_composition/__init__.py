"""
Signal composition package exports.
"""

from .signal_compositor import (
    OrderProposal,
    Signal,
    SignalCompositor,
    consensus_action,
    kelly_fraction,
    volatility_scalar,
)

__all__ = [
    "OrderProposal",
    "Signal",
    "SignalCompositor",
    "consensus_action",
    "kelly_fraction",
    "volatility_scalar",
]
