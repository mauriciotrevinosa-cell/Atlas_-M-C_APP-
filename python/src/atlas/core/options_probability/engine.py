"""
Options probability orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from .distribution import PriceDistribution, RiskNeutralDistribution
from .fetcher import OptionsChain, OptionsChainFetcher
from .iv_surface import IVSurfacePoint, ImpliedVolatilitySurface


@dataclass(slots=True)
class OptionsProbabilityResult:
    symbol: str
    as_of_utc: str
    underlying_price: float
    surface_points: list[IVSurfacePoint]
    distribution: PriceDistribution
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "as_of_utc": self.as_of_utc,
            "underlying_price": self.underlying_price,
            "surface_points": [asdict(p) for p in self.surface_points],
            "distribution": asdict(self.distribution),
            "metadata": self.metadata,
        }


class OptionsProbabilityEngine:
    """Fetches options data and derives a probability distribution for terminal price."""

    def __init__(
        self,
        fetcher: OptionsChainFetcher | None = None,
        iv_surface: ImpliedVolatilitySurface | None = None,
        distribution_model: RiskNeutralDistribution | None = None,
    ) -> None:
        self.fetcher = fetcher or OptionsChainFetcher()
        self.iv_surface = iv_surface or ImpliedVolatilitySurface()
        self.distribution_model = distribution_model or RiskNeutralDistribution()

    def analyze(self, symbol: str, chain: OptionsChain | None = None) -> OptionsProbabilityResult:
        resolved_chain = chain or self.fetcher.fetch(symbol)
        points = self.iv_surface.build(resolved_chain)
        distribution = self.distribution_model.estimate(resolved_chain)
        surface_summary = self.iv_surface.summarize(points)

        metadata = {
            "n_calls": int(len(resolved_chain.calls)),
            "n_puts": int(len(resolved_chain.puts)),
            "surface": surface_summary,
            "distribution_horizon_days": distribution.horizon_days,
        }
        return OptionsProbabilityResult(
            symbol=resolved_chain.symbol,
            as_of_utc=resolved_chain.as_of_utc,
            underlying_price=float(resolved_chain.underlying_price),
            surface_points=points,
            distribution=distribution,
            metadata=metadata,
        )

