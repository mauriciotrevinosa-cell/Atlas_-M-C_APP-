"""Tests for MarketIntelAgent."""

from atlas.core.ai_assistant import build_system
from atlas.core.ai_assistant.agents.market_intel_agent import MarketIntelAgent
from atlas.core.ai_assistant.task_schema import AgentResult, AgentTask


def test_market_intel_agent_scores_priority_assets():
    task = AgentTask(
        task_id="market-intel-1",
        agent_name="market_intel_agent",
        objective="Build a market intelligence brief",
        inputs={
            "watchlist": ["BTC", "SOL"],
            "signals": [
                {
                    "ticker": "BTC",
                    "title": "BTC ETF flow accelerates",
                    "category": "macro",
                    "relevance_score": 0.8,
                    "sentiment_score": 0.4,
                },
                {
                    "tickers": ["SOL"],
                    "title": "SOL ecosystem revenue spikes",
                    "category": "news",
                    "relevance_score": 0.7,
                    "sentiment_score": 0.3,
                },
            ],
            "whale_events": [
                {
                    "ticker": "BTC",
                    "event_type": "large_buy",
                    "size": 120_000_000,
                    "confidence": 0.9,
                }
            ],
            "market_snapshot": {
                "BTC": {
                    "volume_ratio": 2.4,
                    "funding_rate": 0.04,
                    "open_interest_change_pct": 18,
                    "liquidation_usd": 12_000_000,
                },
                "SOL": {"volume_ratio": 1.4},
            },
        },
    )

    result = MarketIntelAgent().safe_run(task)

    assert isinstance(result, AgentResult)
    assert result.status == "success"
    assert result.task_id == "market-intel-1"
    assert result.metadata["agent"] == "market_intel_agent"
    assert result.metadata["mode"] == "read_only"
    assert result.result["priority_assets"][0]["symbol"] == "BTC"
    assert result.result["priority_assets"][0]["attention_level"] in {"high", "critical"}
    assert result.result["risk_flags"]
    assert "BTC" in result.result["catalyst_map"]
    assert any(task["agent_name"] == "repo_scout_agent" for task in result.result["suggested_agent_tasks"])


def test_market_intel_agent_handles_empty_inputs():
    task = AgentTask(
        task_id="market-intel-empty",
        agent_name="market_intel_agent",
        objective="Build a market intelligence brief",
        inputs={},
    )

    result = MarketIntelAgent().safe_run(task)

    assert result.status == "success"
    assert result.result["priority_assets"] == []
    assert result.result["data_gaps"]
    assert "No priority assets" in result.result["market_brief"]


def test_market_intel_agent_is_registered_in_build_system():
    orch = build_system(llm_client=lambda prompt: "{}")

    assert "market_intel_agent" in orch.registry.list_agents()
    agent = orch.registry.get("market_intel_agent")
    assert isinstance(agent, MarketIntelAgent)
