import json
import time
import urllib.request

BASE = "http://localhost:8088"


def check_endpoint(name, url, check_keys=None):
    try:
        start = time.time()
        response = urllib.request.urlopen(url, timeout=15)
        data = json.loads(response.read())
        elapsed_ms = int((time.time() - start) * 1000)
        if check_keys:
            missing = [key for key in check_keys if key not in data]
            status = "FAIL(missing:" + ",".join(missing) + ")" if missing else "PASS"
        else:
            status = "PASS"
        print(f"[{status}] {name} ({elapsed_ms}ms)")
        return data
    except Exception as exc:
        print(f"[FAIL] {name} - {exc}")
        return None


def main():
    print("=== ATLAS ENDPOINT AUDIT ===")
    print()

    check_endpoint("health", f"{BASE}/api/health")
    check_endpoint("system/verify", f"{BASE}/api/system/verify?ticker=AAPL", ["stages", "ok"])

    data = check_endpoint("quote/AAPL (fresh)", f"{BASE}/api/quote/AAPL", ["ticker", "price"])
    if data:
        print(f"    price={data.get('price')}, _cached={data.get('_cached')}")

    time.sleep(0.5)
    data = check_endpoint("quote/AAPL (cached)", f"{BASE}/api/quote/AAPL", ["ticker", "price"])
    if data:
        print(f"    price={data.get('price')}, _cached={data.get('_cached')}")

    data = check_endpoint(
        "market_data/AAPL", f"{BASE}/api/market_data/AAPL", ["ticker", "price", "ohlc"]
    )
    if data:
        print(f"    bars={len(data.get('ohlc', []))}, _cached={data.get('_cached')}")

    time.sleep(0.5)
    data = check_endpoint(
        "market_data/AAPL (cached)",
        f"{BASE}/api/market_data/AAPL",
        ["ticker", "price", "ohlc"],
    )
    if data:
        print(f"    bars={len(data.get('ohlc', []))}, _cached={data.get('_cached')}")

    data = check_endpoint(
        "monitor/tick", f"{BASE}/api/monitor/tick?tickers=AAPL,MSFT,NVDA", ["tickers"]
    )
    if data:
        print(f"    tickers_count={len(data.get('tickers', {}))}")

    data = check_endpoint(
        "strategy/analyze/AAPL", f"{BASE}/api/strategy/analyze/AAPL", ["ticker", "signal"]
    )
    if data:
        print(f"    signal={data.get('signal')}")

    data = check_endpoint("trader/analyze/AAPL", f"{BASE}/api/trader/analyze/AAPL", ["ticker"])
    if data:
        print(f"    composite_score={data.get('composite_score')}")

    data = check_endpoint("factors/AAPL", f"{BASE}/api/factors/AAPL", ["ticker"])
    if data:
        print(f"    keys={list(data.keys())[:5]}")

    data = check_endpoint("strategy/backtest/AAPL", f"{BASE}/api/strategy/backtest/AAPL", ["ticker"])
    if data:
        print(f"    total_return={data.get('total_return_pct')}")

    data = check_endpoint("vizlab/brain", f"{BASE}/api/vizlab/brain", ["nodes", "edges"])
    if data:
        print(f"    nodes={len(data.get('nodes', []))}, edges={len(data.get('edges', []))}")

    data = check_endpoint("options/surface/SPY", f"{BASE}/api/options/surface/SPY", ["ticker"])
    if data:
        print(f"    surface_points={len(data.get('surface', []))}")

    data = check_endpoint("analytics/summary/AAPL", f"{BASE}/api/analytics/summary/AAPL", ["ticker"])
    if data:
        print(f"    keys={list(data.keys())[:5]}")

    try:
        payload = json.dumps({"ticker": "AAPL", "scenarios": ["bull", "bear", "base"]}).encode()
        request = urllib.request.Request(
            f"{BASE}/api/scenarios/analyze",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        response = urllib.request.urlopen(request, timeout=15)
        data = json.loads(response.read())
        print(f"[PASS] scenarios/analyze - keys={list(data.keys())[:4]}")
    except Exception as exc:
        print(f"[FAIL] scenarios/analyze - {exc}")

    try:
        payload = json.dumps({"device_id": "test-device", "device_name": "Test"}).encode()
        request = urllib.request.Request(
            f"{BASE}/api/device/register",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        response = urllib.request.urlopen(request, timeout=10)
        data = json.loads(response.read())
        print(f"[PASS] device/register - {data}")
    except Exception as exc:
        print(f"[FAIL] device/register - {exc}")

    print()
    print("=== DONE ===")


if __name__ == "__main__":
    main()
