from __future__ import annotations

import json

import pandas as pd

from atlas.assistants.aria.tools.agent_task import AtlasAgentTaskTool
from atlas.assistants.aria.tools.provider_registry_tools import (
    AtlasFilingsTool,
    AtlasMacroDataTool,
    AtlasMarketDataTool,
    AtlasNewsTool,
    AtlasSentimentTool,
)
from atlas.assistants.aria.tools.setup import register_all_tools
from atlas.core.ai_assistant.task_schema import AgentResult


class FakeRegistry:
    def get_provider_info(self):
        return {"market_data": [{"name": "FakeMarket"}]}

    def get_quote(self, symbol: str):
        return {"symbol": symbol, "price": 123.45, "provider": "FakeMarket"}

    def get_price(self, symbol: str, start: str, end: str, interval: str = "1d"):
        index = pd.to_datetime(["2026-01-02", "2026-01-03", "2026-01-06"])
        return pd.DataFrame(
            {
                "open": [100.0, 101.0, 102.0],
                "high": [101.0, 102.0, 103.0],
                "low": [99.0, 100.0, 101.0],
                "close": [100.5, 101.5, 102.5],
                "volume": [1000, 1100, 1200],
            },
            index=index,
        )

    def get_macro(self, series_id: str, start=None, end=None):
        index = pd.to_datetime(["2025-10-01", "2026-01-01"])
        return pd.DataFrame({"value": [2.1, 2.4]}, index=index)

    def get_news(self, query=None, category="general"):
        return [
            {
                "headline": "Atlas test headline",
                "summary": "Atlas test summary",
                "source": "FakeWire",
                "url": "https://example.test/news",
                "datetime": "2026-03-25T12:00:00Z",
            }
        ]

    def get_filings(self, ticker: str, filing_type: str = "10-K", count: int = 5):
        return [
            {
                "ticker": ticker,
                "date": "2026-02-01",
                "accession_number": "0000000000-26-000001",
                "filing_type": filing_type,
            }
        ]

    def get_sentiment(self, symbol=None, text=None):
        if symbol:
            return {"symbol": symbol, "bullish": 0.6}
        if text:
            return {"label": "positive", "score": 0.91}
        return None


class DummyAria:
    def __init__(self):
        self.tools = {}

    def register_tool(self, tool):
        self.tools[tool.name] = tool


class FakeOrchestrator:
    def execute(self, task):
        return AgentResult(
            task_id=task.task_id,
            status="success",
            summary=f"Handled {task.agent_name}",
            result={"agent": task.agent_name, "objective": task.objective},
            errors=[],
            metadata={"agent": task.agent_name},
        )


def test_market_data_tool_quote_and_history_are_json_safe():
    registry = FakeRegistry()
    tool = AtlasMarketDataTool(registry=registry)

    quote = tool.execute(symbol="AAPL")
    history = tool.execute(symbol="AAPL", mode="historical", limit=2)

    assert quote["success"] is True
    assert history["success"] is True
    assert history["rows"] == 3
    json.dumps(quote)
    json.dumps(history)


def test_registry_tools_return_structured_results():
    registry = FakeRegistry()

    macro = AtlasMacroDataTool(registry=registry).execute(series_id="GDP")
    news = AtlasNewsTool(registry=registry).execute(query="AAPL")
    filings = AtlasFilingsTool(registry=registry).execute(ticker="AAPL")
    sentiment = AtlasSentimentTool(registry=registry).execute(text="Strong earnings beat expectations")

    assert macro["success"] is True
    assert news["articles"][0]["title"] == "Atlas test headline"
    assert filings["filings"][0]["ticker"] == "AAPL"
    assert sentiment["data"]["label"] == "positive"


def test_agent_task_tool_uses_orchestrator():
    tool = AtlasAgentTaskTool(orchestrator=FakeOrchestrator())
    result = tool.execute(agent_name="planner_agent", objective="Build a plan")

    assert result["success"] is True
    assert result["result"]["agent"] == "planner_agent"


def test_register_all_tools_includes_new_registry_and_agent_tools():
    aria = DummyAria()
    register_all_tools(aria)

    expected = {
        "atlas_market_data",
        "atlas_macro_data",
        "atlas_news",
        "atlas_filings",
        "atlas_sentiment",
        "atlas_agent_task",
    }
    assert expected.issubset(set(aria.tools))
