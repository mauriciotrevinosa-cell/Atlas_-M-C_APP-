from __future__ import annotations

import run_atlas


class DummyAria:
    def __init__(self):
        self.model = "llama3.2:1b"
        self.tools = {
            "atlas_market_data": object(),
            "atlas_macro_data": object(),
            "atlas_news": object(),
            "atlas_filings": object(),
            "atlas_sentiment": object(),
            "atlas_agent_task": object(),
            "web_search": object(),
        }


class FakeRegistry:
    def get_provider_info(self):
        return {
            "market_data": [
                {"name": "Finnhub", "available": False},
                {"name": "YahooFinance", "available": True},
            ],
            "news": [
                {"name": "NewsAPI", "available": True},
            ],
        }


def test_runtime_observability_report_lists_live_tools_and_providers(monkeypatch):
    monkeypatch.setattr(run_atlas, "get_provider_registry", lambda: FakeRegistry())

    report = run_atlas._build_runtime_observability_report(DummyAria())

    assert "ATLAS RUNTIME REPORT" in report
    assert "Live registry tools: atlas_market_data, atlas_macro_data, atlas_news, atlas_filings, atlas_sentiment" in report
    assert "Agent tools: atlas_agent_task" in report
    assert "Browser tools: web_search" in report
    assert "market_data: Finnhub (unavailable), YahooFinance" in report
