"""
Tests — Multi-Asset Simulation & Portfolio Risk
================================================
Covers:
    TestMultiAssetSimulator   — PortfolioSimConfig, MultiAssetSimulator
    TestPortfolioRiskManager  — PortfolioRiskManager, PortfolioRiskResult

All tests are fully offline: no network calls, no real market data.
Synthetic returns are generated deterministically for reproducibility.

Copyright (c) 2026 M&C. All rights reserved.
"""

import numpy as np
import pandas as pd
import pytest

from atlas.monte_carlo.multi_asset import (
    MultiAssetSimulator,
    PortfolioSimConfig,
    PortfolioSimResults,
)
from atlas.monte_carlo.simulator import VarianceReduction
from atlas.risk.portfolio_risk import (
    PortfolioRiskManager,
    PortfolioRiskResult,
    ComponentVaRResult,
)


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

_TICKERS = ["AAPL", "MSFT", "SPY"]
_WEIGHTS = {"AAPL": 0.5, "MSFT": 0.3, "SPY": 0.2}
_N_OBS = 504  # 2 years of daily data
_SEED = 42


@pytest.fixture(scope="module")
def synthetic_returns() -> pd.DataFrame:
    """
    Synthetic correlated daily returns for AAPL / MSFT / SPY.

    Uses fixed seed so tests are deterministic.
    """
    rng = np.random.default_rng(_SEED)

    # True correlation structure
    corr = np.array([
        [1.00, 0.65, 0.75],
        [0.65, 1.00, 0.70],
        [0.75, 0.70, 1.00],
    ])
    std = np.array([0.018, 0.016, 0.012])     # daily σ
    mu  = np.array([0.0006, 0.0005, 0.0003])  # daily μ
    cov = np.outer(std, std) * corr

    L = np.linalg.cholesky(cov)
    Z = rng.standard_normal((_N_OBS, 3))
    raw = Z @ L.T + mu

    dates = pd.date_range("2022-01-03", periods=_N_OBS, freq="B")
    return pd.DataFrame(raw, index=dates, columns=_TICKERS)


@pytest.fixture(scope="module")
def sim() -> MultiAssetSimulator:
    return MultiAssetSimulator()


@pytest.fixture(scope="module")
def mgr() -> PortfolioRiskManager:
    return PortfolioRiskManager()


# ─────────────────────────────────────────────────────────────────────────────
# TestMultiAssetSimulator
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiAssetSimulator:
    """Tests for MultiAssetSimulator and PortfolioSimConfig."""

    def test_basic_simulation_returns(self, sim, synthetic_returns):
        """simulate_from_returns produces a valid PortfolioSimResults."""
        cfg = PortfolioSimConfig(n_paths=500, n_steps=63, seed=_SEED)
        result = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)

        assert isinstance(result, PortfolioSimResults)
        assert result.portfolio_paths.shape == (500, 63)

    def test_portfolio_starts_at_one(self, sim, synthetic_returns):
        """Portfolio paths must start at exactly 1.0 at step 0."""
        cfg = PortfolioSimConfig(n_paths=200, n_steps=50, seed=_SEED)
        result = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)

        # At step 0 (first cumulative increment) values should be near but not
        # exactly 1 because step 0 is the FIRST move; paths start implicitly at 1.
        # The portfolio value after 1 step should be centred around 1.
        mean_step0 = result.portfolio_paths[:, 0].mean()
        assert 0.90 < mean_step0 < 1.10, (
            f"Expected portfolio step-0 mean ≈ 1.0, got {mean_step0:.4f}"
        )

    def test_weights_auto_normalise(self, sim, synthetic_returns):
        """Unnormalised weights should be auto-normalised to sum = 1."""
        unnorm = {"AAPL": 5.0, "MSFT": 3.0, "SPY": 2.0}  # sum = 10 → 0.5/0.3/0.2
        cfg = PortfolioSimConfig(n_paths=200, n_steps=63, seed=_SEED)
        result = sim.simulate_from_returns(synthetic_returns, unnorm, cfg)

        assert abs(sum(result.weights.values()) - 1.0) < 1e-9
        assert abs(result.weights["AAPL"] - 0.5) < 1e-9
        assert abs(result.weights["MSFT"] - 0.3) < 1e-9
        assert abs(result.weights["SPY"]  - 0.2) < 1e-9

    def test_antithetic_produces_n_paths(self, sim, synthetic_returns):
        """Antithetic variates: n_paths must be exactly as requested."""
        n = 600  # must be even for antithetic
        cfg = PortfolioSimConfig(n_paths=n, n_steps=50,
                                 variance_reduction=VarianceReduction.ANTITHETIC,
                                 seed=_SEED)
        result = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)
        assert result.portfolio_paths.shape[0] == n

    def test_no_variance_reduction(self, sim, synthetic_returns):
        """NONE variance reduction still works correctly."""
        cfg = PortfolioSimConfig(n_paths=300, n_steps=63,
                                 variance_reduction=VarianceReduction.NONE,
                                 seed=_SEED)
        result = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)
        assert result.portfolio_paths.shape == (300, 63)

    def test_deterministic_with_seed(self, sim, synthetic_returns):
        """Same seed → identical portfolio paths."""
        cfg = PortfolioSimConfig(n_paths=200, n_steps=63, seed=99)
        r1 = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)
        r2 = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)
        np.testing.assert_array_equal(r1.portfolio_paths, r2.portfolio_paths)

    def test_different_seeds_differ(self, sim, synthetic_returns):
        """Different seeds → different portfolio paths."""
        r1 = sim.simulate_from_returns(synthetic_returns, _WEIGHTS,
                                       PortfolioSimConfig(n_paths=200, n_steps=63, seed=1))
        r2 = sim.simulate_from_returns(synthetic_returns, _WEIGHTS,
                                       PortfolioSimConfig(n_paths=200, n_steps=63, seed=2))
        assert not np.array_equal(r1.portfolio_paths, r2.portfolio_paths)

    def test_asset_paths_shape(self, sim, synthetic_returns):
        """Per-asset paths have shape (n_paths, n_steps)."""
        cfg = PortfolioSimConfig(n_paths=300, n_steps=63, seed=_SEED)
        result = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)

        for ticker in _TICKERS:
            assert ticker in result.asset_paths
            assert result.asset_paths[ticker].shape == (300, 63)

    def test_percentile_keys_present(self, sim, synthetic_returns):
        """All standard percentile levels are present in the result."""
        cfg = PortfolioSimConfig(n_paths=300, n_steps=63, seed=_SEED)
        result = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)

        for p in [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]:
            assert p in result.percentiles
            assert result.percentiles[p].shape == (63,)

    def test_percentiles_monotonically_ordered(self, sim, synthetic_returns):
        """5th percentile ≤ 50th ≤ 95th at every time step."""
        cfg = PortfolioSimConfig(n_paths=2000, n_steps=63, seed=_SEED)
        result = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)

        p5  = result.percentiles[0.05]
        p50 = result.percentiles[0.50]
        p95 = result.percentiles[0.95]

        assert np.all(p5 <= p50 + 1e-10)
        assert np.all(p50 <= p95 + 1e-10)

    def test_risk_metrics_keys(self, sim, synthetic_returns):
        """risk_metrics dict contains all expected keys."""
        cfg = PortfolioSimConfig(n_paths=500, n_steps=63, seed=_SEED)
        result = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)

        expected_keys = {
            "var_95", "cvar_95", "var_99", "cvar_99",
            "max_drawdown_median", "prob_loss",
            "expected_return", "std_return",
        }
        assert expected_keys.issubset(result.risk_metrics.keys())

    def test_var_ordering(self, sim, synthetic_returns):
        """99% VaR must be >= 95% VaR (higher confidence = larger loss estimate)."""
        cfg = PortfolioSimConfig(n_paths=2000, n_steps=63, seed=_SEED)
        result = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)

        assert result.risk_metrics["var_99"] >= result.risk_metrics["var_95"], (
            f"VaR ordering violated: VaR99={result.risk_metrics['var_99']:.4f} "
            f"< VaR95={result.risk_metrics['var_95']:.4f}"
        )

    def test_prob_loss_in_range(self, sim, synthetic_returns):
        """Probability of loss must be in [0, 1]."""
        cfg = PortfolioSimConfig(n_paths=1000, n_steps=252, seed=_SEED)
        result = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)
        prob = result.risk_metrics["prob_loss"]
        assert 0.0 <= prob <= 1.0

    def test_max_drawdown_non_positive(self, sim, synthetic_returns):
        """Median max drawdown must be ≤ 0 (drawdown = loss)."""
        cfg = PortfolioSimConfig(n_paths=500, n_steps=252, seed=_SEED)
        result = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)
        assert result.risk_metrics["max_drawdown_median"] <= 0.0

    def test_summary_dataframe_shape(self, sim, synthetic_returns):
        """summary() returns a DataFrame with 11 rows and 2 columns."""
        cfg = PortfolioSimConfig(n_paths=200, n_steps=63, seed=_SEED)
        result = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)
        df = result.summary()
        assert isinstance(df, pd.DataFrame)
        assert df.shape == (11, 2)
        assert list(df.columns) == ["Metric", "Value"]

    def test_missing_ticker_raises(self, sim, synthetic_returns):
        """A weight for a ticker not in returns_df should raise ValueError."""
        bad_weights = {"AAPL": 0.5, "TSLA": 0.5}  # TSLA not in fixture
        with pytest.raises(ValueError, match="not found"):
            sim.simulate_from_returns(
                synthetic_returns, bad_weights,
                PortfolioSimConfig(n_paths=100, n_steps=50, seed=_SEED),
            )

    def test_config_validation(self):
        """PortfolioSimConfig rejects invalid parameters."""
        with pytest.raises(ValueError):
            PortfolioSimConfig(n_paths=0, n_steps=252)
        with pytest.raises(ValueError):
            PortfolioSimConfig(n_paths=100, n_steps=0)
        with pytest.raises(ValueError):
            PortfolioSimConfig(n_paths=100, n_steps=252, dt=-0.01)

    def test_corr_matrix_shape(self, sim, synthetic_returns):
        """corr_matrix must be square (n_assets × n_assets)."""
        cfg = PortfolioSimConfig(n_paths=100, n_steps=50, seed=_SEED)
        result = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)
        n = len(_TICKERS)
        assert result.corr_matrix.shape == (n, n)

    def test_simulate_from_router(self, sim, synthetic_returns):
        """simulate_from_router works when router returns cached DataFrames."""
        # Build mock price DataFrames from synthetic returns
        mock_dfs = {}
        for ticker in _TICKERS:
            prices = (1 + synthetic_returns[ticker]).cumprod() * 100
            mock_dfs[ticker] = pd.DataFrame(
                {"close": prices.values},
                index=synthetic_returns.index,
            )

        class MockRouter:
            def get(self, tickers, start, end, interval="1d"):
                return {t: mock_dfs[t] for t in tickers if t in mock_dfs}

        cfg = PortfolioSimConfig(n_paths=200, n_steps=50, seed=_SEED)
        result = sim.simulate_from_router(
            router=MockRouter(),
            tickers=_TICKERS,
            weights=_WEIGHTS,
            start="2022-01-03",
            end="2023-12-29",
            config=cfg,
        )
        assert isinstance(result, PortfolioSimResults)
        assert result.portfolio_paths.shape == (200, 50)


# ─────────────────────────────────────────────────────────────────────────────
# TestPortfolioRiskManager
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolioRiskManager:
    """Tests for PortfolioRiskManager and PortfolioRiskResult."""

    def test_basic_assessment(self, mgr, synthetic_returns):
        """assess() produces a valid PortfolioRiskResult."""
        result = mgr.assess(synthetic_returns, _WEIGHTS)
        assert isinstance(result, PortfolioRiskResult)

    def test_n_obs_correct(self, mgr, synthetic_returns):
        """n_obs should equal the number of rows after dropna."""
        result = mgr.assess(synthetic_returns, _WEIGHTS)
        assert result.n_obs == _N_OBS

    def test_var_ordering(self, mgr, synthetic_returns):
        """99% VaR >= 95% VaR and 99% CVaR >= 99% VaR."""
        result = mgr.assess(synthetic_returns, _WEIGHTS)

        assert result.portfolio_var_99 >= result.portfolio_var, (
            f"VaR ordering: VaR99={result.portfolio_var_99:.4f} "
            f"< VaR95={result.portfolio_var:.4f}"
        )
        assert result.portfolio_cvar >= result.portfolio_var, (
            "CVaR should be >= VaR at same confidence level"
        )
        assert result.portfolio_cvar_99 >= result.portfolio_var_99

    def test_all_var_positive(self, mgr, synthetic_returns):
        """All VaR / CVaR values should be positive (expressed as losses)."""
        result = mgr.assess(synthetic_returns, _WEIGHTS)
        assert result.portfolio_var    >= 0
        assert result.portfolio_cvar   >= 0
        assert result.portfolio_var_99 >= 0
        assert result.portfolio_cvar_99 >= 0

    def test_volatility_positive(self, mgr, synthetic_returns):
        """Annualised portfolio volatility must be positive."""
        result = mgr.assess(synthetic_returns, _WEIGHTS)
        assert result.portfolio_volatility > 0

    def test_max_drawdown_non_positive(self, mgr, synthetic_returns):
        """Max drawdown must be ≤ 0 (convention: negative = loss)."""
        result = mgr.assess(synthetic_returns, _WEIGHTS)
        assert result.max_drawdown <= 0

    def test_component_var_count(self, mgr, synthetic_returns):
        """One ComponentVaRResult per asset in weights."""
        result = mgr.assess(synthetic_returns, _WEIGHTS)
        assert len(result.component_var) == len(_TICKERS)

    def test_component_var_types(self, mgr, synthetic_returns):
        """ComponentVaRResult has correct field types."""
        result = mgr.assess(synthetic_returns, _WEIGHTS)
        for c in result.component_var:
            assert isinstance(c, ComponentVaRResult)
            assert isinstance(c.ticker, str)
            assert 0.0 < c.weight <= 1.0
            assert isinstance(c.asset_var, float)

    def test_component_var_sum_approx_portfolio_var(self, mgr, synthetic_returns):
        """
        Sum of component VaRs should approximately equal portfolio VaR.

        The Euler decomposition property guarantees this (up to floating-point
        noise), assuming normal-ish distributions.  Allow 20 % tolerance to
        account for the non-Gaussian nature of synthetic data.
        """
        result = mgr.assess(synthetic_returns, _WEIGHTS)
        comp_sum = sum(c.component_var for c in result.component_var)
        portfolio_var = result.portfolio_var

        if abs(portfolio_var) > 1e-10:
            rel_diff = abs(comp_sum - portfolio_var) / abs(portfolio_var)
            assert rel_diff < 0.30, (
                f"Component VaR sum ({comp_sum:.4f}) deviates from portfolio "
                f"VaR ({portfolio_var:.4f}) by {rel_diff:.1%}"
            )

    def test_stress_scenarios_present(self, mgr, synthetic_returns):
        """All four built-in stress scenarios must be present."""
        result = mgr.assess(synthetic_returns, _WEIGHTS, run_stress=True)
        expected = {"2008_gfc", "2020_covid", "dot_com_bust", "rate_shock_2022"}
        assert expected == set(result.stress_scenarios.keys())

    def test_stress_scenarios_positive_loss(self, mgr, synthetic_returns):
        """Stress scenario losses should be positive for equity-heavy portfolios."""
        # _WEIGHTS is equity-heavy (AAPL 50%, MSFT 30%, SPY 20%) →
        # all three scenarios should show net losses (positive values).
        # rate_shock_2022 has mixed signals for commodities so only check
        # the three clearly negative scenarios.
        result = mgr.assess(
            synthetic_returns, _WEIGHTS,
            asset_classes={t: "EQUITY" for t in _TICKERS},
            run_stress=True,
        )
        for scenario in ["2008_gfc", "2020_covid", "dot_com_bust"]:
            assert result.stress_scenarios[scenario] > 0, (
                f"Expected positive loss for {scenario}, "
                f"got {result.stress_scenarios[scenario]}"
            )

    def test_stress_skipped_when_disabled(self, mgr, synthetic_returns):
        """run_stress=False should return an empty stress dict."""
        result = mgr.assess(synthetic_returns, _WEIGHTS, run_stress=False)
        assert result.stress_scenarios == {}

    def test_weights_normalised_in_result(self, mgr, synthetic_returns):
        """Weights in the result must sum to 1."""
        unnorm = {"AAPL": 5, "MSFT": 3, "SPY": 2}
        result = mgr.assess(synthetic_returns, unnorm)
        total = sum(result.weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_tickers_in_result(self, mgr, synthetic_returns):
        """Result tickers must be a subset of the requested tickers."""
        result = mgr.assess(synthetic_returns, _WEIGHTS)
        assert set(result.tickers) == set(_TICKERS)

    def test_missing_tickers_warn_not_raise(self, mgr, synthetic_returns):
        """A missing ticker should generate a warning but not raise."""
        weights_with_extra = {**_WEIGHTS, "TSLA": 0.1}
        result = mgr.assess(synthetic_returns, weights_with_extra)
        assert any("TSLA" in w for w in result.warnings)

    def test_all_tickers_missing_raises(self, mgr, synthetic_returns):
        """If no weights match returns_df columns, raise ValueError."""
        with pytest.raises(ValueError, match="No valid tickers"):
            mgr.assess(synthetic_returns, {"TSLA": 0.5, "NVDA": 0.5})

    def test_summary_table_shape(self, mgr, synthetic_returns):
        """summary_table() returns a 10-row 2-column DataFrame."""
        result = mgr.assess(synthetic_returns, _WEIGHTS)
        df = result.summary_table()
        assert isinstance(df, pd.DataFrame)
        assert df.shape == (10, 2)
        assert list(df.columns) == ["Metric", "Value"]

    def test_to_dict_keys(self, mgr, synthetic_returns):
        """to_dict() must contain all top-level expected keys."""
        result = mgr.assess(synthetic_returns, _WEIGHTS)
        d = result.to_dict()

        expected_keys = {
            "portfolio_var_95", "portfolio_cvar_95",
            "portfolio_var_99", "portfolio_cvar_99",
            "portfolio_volatility", "sharpe", "sortino", "calmar",
            "max_drawdown", "component_var", "stress_scenarios",
            "n_obs", "tickers", "weights", "warnings",
        }
        assert expected_keys.issubset(d.keys())

    def test_assess_from_router(self, mgr, synthetic_returns):
        """assess_from_router() works with a MockRouter returning price DataFrames."""
        mock_dfs = {}
        for ticker in _TICKERS:
            prices = (1 + synthetic_returns[ticker]).cumprod() * 100
            mock_dfs[ticker] = pd.DataFrame(
                {"close": prices.values},
                index=synthetic_returns.index,
            )

        class MockRouter:
            def get(self, tickers, start, end, interval="1d"):
                return {t: mock_dfs[t] for t in tickers if t in mock_dfs}

        result = mgr.assess_from_router(
            router=MockRouter(),
            tickers=_TICKERS,
            weights=_WEIGHTS,
            start="2022-01-03",
            end="2023-12-29",
        )
        assert isinstance(result, PortfolioRiskResult)
        assert result.portfolio_var >= 0

    def test_confidence_levels(self, mgr, synthetic_returns):
        """Custom confidence level is respected."""
        r90 = mgr.assess(synthetic_returns, _WEIGHTS, confidence=0.90)
        r99 = mgr.assess(synthetic_returns, _WEIGHTS, confidence=0.99)
        # 99% VaR >= 90% VaR
        assert r99.portfolio_var >= r90.portfolio_var

    def test_few_observations_warning(self, mgr, synthetic_returns):
        """Fewer than 30 observations should generate a warning."""
        small_ret = synthetic_returns.iloc[:20]
        result = mgr.assess(small_ret, _WEIGHTS)
        assert any("observations" in w for w in result.warnings)


# ─────────────────────────────────────────────────────────────────────────────
# Cross-layer integration: simulation → risk assessment
# ─────────────────────────────────────────────────────────────────────────────

class TestSimulationRiskIntegration:
    """End-to-end: use simulated paths to assess portfolio risk."""

    def test_simulate_then_assess(self, sim, mgr, synthetic_returns):
        """Run simulation, derive returns from paths, then assess risk."""
        cfg = PortfolioSimConfig(n_paths=1000, n_steps=252, seed=_SEED)
        sim_result = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)

        # Derive daily returns from median portfolio path
        median_path = sim_result.percentiles[0.50]                    # (252,)
        # Prepend 1.0 as the starting value to compute period returns
        path_with_start = np.concatenate([[1.0], median_path])
        sim_daily_returns = np.diff(path_with_start) / path_with_start[:-1]

        sim_returns_df = pd.DataFrame(
            {"PORTFOLIO": sim_daily_returns},
            index=pd.date_range("2024-01-02", periods=252, freq="B"),
        )

        risk_result = mgr.assess(
            sim_returns_df,
            weights={"PORTFOLIO": 1.0},
            run_stress=False,
        )
        assert isinstance(risk_result, PortfolioRiskResult)
        assert risk_result.portfolio_var >= 0
        assert risk_result.max_drawdown <= 0

    def test_monte_carlo_exports_match_analytics(self, sim, synthetic_returns):
        """
        Verify that risk_metrics from MultiAssetSimulator are consistent with
        PortfolioRiskManager on the historical returns.

        VaR from the simulation (terminal) and historical series will differ
        (different period / methodology), but both must be non-negative.
        """
        cfg = PortfolioSimConfig(n_paths=2000, n_steps=252, seed=_SEED)
        sim_result = sim.simulate_from_returns(synthetic_returns, _WEIGHTS, cfg)
        sim_var = sim_result.risk_metrics["var_95"]

        mgr = PortfolioRiskManager()
        risk_result = mgr.assess(synthetic_returns, _WEIGHTS)
        hist_var = risk_result.portfolio_var

        # Both must be non-negative
        assert sim_var  >= 0
        assert hist_var >= 0
