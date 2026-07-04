from __future__ import annotations

import pytest

from atlas.rl import ActionScheme, RiskAdjustedRewardScheme, TradeAction, TradingEnvironment


def test_default_action_scheme_validates_and_serializes():
    scheme = ActionScheme.single_asset_default()

    assert scheme.action_dim == 5
    assert scheme.validate(2).name == "BUY_LARGE"
    assert scheme.names() == ["HOLD", "BUY_SMALL", "BUY_LARGE", "SELL_SMALL", "SELL_LARGE"]
    assert scheme.to_dict()["actions"][0]["name"] == "HOLD"

    with pytest.raises(ValueError):
        scheme.validate(99)


def test_action_scheme_requires_contiguous_ids():
    with pytest.raises(ValueError):
        ActionScheme(
            [
                TradeAction(0, "HOLD", "hold"),
                TradeAction(2, "BUY", "buy", 0.25),
            ]
        )


def test_risk_adjusted_reward_explains_components():
    scheme = RiskAdjustedRewardScheme(
        sharpe_weight=0.01,
        drawdown_threshold=-0.05,
        drawdown_weight=0.5,
        turnover_weight=0.1,
        cost_weight=0.2,
    )

    reward = scheme.compute(
        0.01,
        [0.01, -0.002, 0.004, 0.003, -0.001, 0.006, 0.002, 0.005, -0.003, 0.004, 0.006],
        drawdown=-0.08,
        turnover=0.25,
        trade_cost=0.001,
    )

    assert reward.base_return == 0.01
    assert reward.sharpe_bonus > 0
    assert reward.drawdown_penalty == pytest.approx(-0.04)
    assert reward.turnover_penalty == pytest.approx(-0.025)
    assert reward.cost_penalty == pytest.approx(-0.0002)
    assert reward.to_dict()["total"] == pytest.approx(reward.total)


def test_trading_environment_uses_action_and_reward_schemes():
    env = TradingEnvironment(
        seed=7,
        episode_length=8,
        reward_scheme=RiskAdjustedRewardScheme(
            sharpe_weight=0.0,
            drawdown_threshold=-1.0,
            drawdown_weight=0.0,
            turnover_weight=0.5,
            cost_weight=1.0,
        ),
    )

    env.reset()
    _, reward, _, info = env.step(1)

    components = info["reward_components"]
    assert info["action"].startswith("BUY_SM @")
    assert info["turnover"] > 0
    assert info["trade_cost"] > 0
    assert components["turnover_penalty"] < 0
    assert components["cost_penalty"] < 0
    assert reward == pytest.approx(components["total"])
