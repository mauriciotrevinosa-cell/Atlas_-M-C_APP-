from __future__ import annotations

from atlas.assistants.aria.tools import web_search
from atlas.assistants.aria.tools.web_search import WebSearchTool


def test_web_search_tool_uses_ddgs_query_signature(monkeypatch) -> None:
    calls = {}

    class FakeDDGS:
        def text(self, query: str, **kwargs):
            calls["query"] = query
            calls["kwargs"] = kwargs
            return [{"title": "Result", "href": "https://example.com", "body": "Snippet"}]

        def close(self) -> None:
            calls["closed"] = True

    monkeypatch.setattr(web_search, "DDGS", FakeDDGS)
    monkeypatch.setattr(web_search, "DDGS_BACKEND", "ddgs")
    monkeypatch.setattr(web_search, "DDGS_AVAILABLE", True)

    result = WebSearchTool().execute("atlas test", max_results=2)

    assert result["success"] is True
    assert result["count"] == 1
    assert calls["query"] == "atlas test"
    assert calls["kwargs"]["max_results"] == 2
    assert calls["closed"] is True


def test_web_search_tool_keeps_legacy_duckduckgo_signature(monkeypatch) -> None:
    calls = {}

    class FakeDDGS:
        def text(self, **kwargs):
            calls.update(kwargs)
            return [{"title": "Legacy", "href": "https://example.com", "body": "Snippet"}]

    monkeypatch.setattr(web_search, "DDGS", FakeDDGS)
    monkeypatch.setattr(web_search, "DDGS_BACKEND", "duckduckgo_search")
    monkeypatch.setattr(web_search, "DDGS_AVAILABLE", True)

    result = WebSearchTool().execute("legacy query", max_results=1)

    assert result["success"] is True
    assert result["count"] == 1
    assert calls["keywords"] == "legacy query"
