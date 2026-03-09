from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class CheckResult:
    name: str
    method: str
    path: str
    status: int
    ok: bool
    detail: str


def _run_request(
    client: TestClient,
    name: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> CheckResult:
    try:
        if method == "GET":
            response = client.get(path)
        elif method == "POST":
            response = client.post(path, json=payload or {})
        else:
            return CheckResult(name, method, path, -1, False, f"Unsupported method: {method}")

        detail = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                keys = list(body.keys())[:8]
                detail = f"keys={keys}"
            else:
                detail = f"type={type(body).__name__}"
        except Exception:
            detail = "non-json response"

        ok = response.status_code == 200
        if not ok:
            detail = f"{detail} body={response.text[:180]}"
        return CheckResult(name, method, path, response.status_code, ok, detail)
    except Exception as exc:
        return CheckResult(name, method, path, -1, False, str(exc)[:220])


def main() -> int:
    from apps.server.server import app

    client = TestClient(app)
    results: list[CheckResult] = []

    checks = [
        ("Health", "GET", "/api/health", None),
        ("Command Center", "GET", "/api/system/command_center", None),
        ("Thought Map", "GET", "/api/system/thought_map", None),
        ("System Verify", "GET", "/api/system/verify?ticker=AAPL", None),
        ("Quote", "GET", "/api/quote/AAPL", None),
        ("Market Data", "GET", "/api/market_data/AAPL", None),
        ("Analytics Summary", "GET", "/api/analytics/summary/AAPL?period=1y", None),
        ("Analytics Correlation", "GET", "/api/analytics/correlation?tickers=AAPL,MSFT,SPY&period=1y&return_method=log", None),
        (
            "Portfolio Risk",
            "POST",
            "/api/risk/portfolio/assess",
            {"tickers": ["AAPL", "MSFT", "SPY"], "period": "1y", "return_method": "log"},
        ),
        (
            "Portfolio Monte Carlo",
            "POST",
            "/api/montecarlo/portfolio/simulate",
            {
                "tickers": ["AAPL", "MSFT", "SPY"],
                "period": "1y",
                "return_method": "log",
                "n_paths": 400,
                "horizon_days": 120,
                "seed": 7,
            },
        ),
        ("Portfolio", "GET", "/api/portfolio", None),
        ("Signal Compose", "GET", "/api/signal/compose/AAPL?capital=100000", None),
        ("Strategy Analyze", "GET", "/api/strategy/analyze/AAPL?period=6mo", None),
        ("Strategy Backtest", "GET", "/api/strategy/backtest/AAPL?period=1y", None),
        ("Trader Analyze", "GET", "/api/trader/analyze/AAPL?period=1y", None),
        ("Trader Screen", "GET", "/api/trader/screen?period=1y&top_n=3", None),
        ("Factors", "GET", "/api/factors/AAPL?period=1y", None),
        ("Options Surface", "GET", "/api/options/surface/SPY", None),
        ("VizLab Status", "GET", "/api/vizlab/system_status", None),
        ("Agents Status", "GET", "/api/agents/status", None),
        ("Sim Snapshot", "GET", "/api/sim/dashboard/snapshot", None),
    ]

    for name, method, path, payload in checks:
        results.append(_run_request(client, name, method, path, payload))

    scenario_payload = {"ticker": "AAPL", "initial_capital": 10000, "start_date": "2020-01-01"}
    session_id: str | None = None
    try:
        scenario_resp = client.post("/api/scenario/start", json=scenario_payload)
        scenario_detail = ""
        try:
            scenario_body = scenario_resp.json()
            if isinstance(scenario_body, dict):
                scenario_detail = f"keys={list(scenario_body.keys())[:8]}"
                session_id = scenario_body.get("session_id")
        except Exception:
            scenario_detail = "non-json response"
        results.append(
            CheckResult(
                name="Scenario Start",
                method="POST",
                path="/api/scenario/start",
                status=scenario_resp.status_code,
                ok=scenario_resp.status_code == 200,
                detail=scenario_detail,
            )
        )
    except Exception as exc:
        results.append(
            CheckResult(
                name="Scenario Start",
                method="POST",
                path="/api/scenario/start",
                status=-1,
                ok=False,
                detail=str(exc)[:220],
            )
        )

    if session_id:
        results.append(_run_request(client, "Scenario Next", "POST", f"/api/scenario/{session_id}/next"))
        results.append(
            _run_request(
                client,
                "Scenario Switch",
                "POST",
                "/api/scenario/switch_ticker",
                {"session_id": session_id, "ticker": "MSFT"},
            )
        )

    passed = sum(1 for r in results if r.ok)
    failed = len(results) - passed

    print("=" * 72)
    print("ATLAS DESKTOP <-> SERVER LOOP VERIFICATION")
    print("=" * 72)
    for r in results:
        status = "OK" if r.ok else "FAIL"
        print(f"[{status}] {r.method:4} {r.path:55} -> {r.status}")
        print(f"      {r.detail}")
    print("-" * 72)
    print(f"Summary: {passed}/{len(results)} checks passed ({failed} failed)")

    report = {
        "passed": passed,
        "failed": failed,
        "total": len(results),
        "results": [r.__dict__ for r in results],
    }
    out_path = PROJECT_ROOT / "outputs" / "desktop_server_loop_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report: {out_path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
