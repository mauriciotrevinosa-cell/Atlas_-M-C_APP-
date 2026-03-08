import urllib.request
import json
import time

BASE = "http://localhost:8088"

def test(name, url, check_keys=None):
    try:
        start = time.time()
        r = urllib.request.urlopen(url, timeout=15)
        data = json.loads(r.read())
        ms = int((time.time() - start) * 1000)
        if check_keys:
            missing = [k for k in check_keys if k not in data]
            status = "FAIL(missing:" + ",".join(missing) + ")" if missing else "PASS"
        else:
            status = "PASS"
        print(f"[{status}] {name} ({ms}ms)")
        return data
    except Exception as e:
        print(f"[FAIL] {name} - {e}")
        return None

print("=== ATLAS ENDPOINT AUDIT ===")
print()

# Health
test("health", f"{BASE}/api/health")

# System verify
test("system/verify", f"{BASE}/api/system/verify?ticker=AAPL", ["stages", "ok"])

# Quote - first call (fresh)
d = test("quote/AAPL (fresh)", f"{BASE}/api/quote/AAPL", ["ticker", "price"])
if d: print(f"    price={d.get('price')}, _cached={d.get('_cached')}")

# Quote - second call (cached)
time.sleep(0.5)
d = test("quote/AAPL (cached)", f"{BASE}/api/quote/AAPL", ["ticker", "price"])
if d: print(f"    price={d.get('price')}, _cached={d.get('_cached')}")

# Market data
d = test("market_data/AAPL", f"{BASE}/api/market_data/AAPL", ["ticker", "price", "ohlc"])
if d: print(f"    bars={len(d.get('ohlc', []))}, _cached={d.get('_cached')}")

# Market data cached
time.sleep(0.5)
d = test("market_data/AAPL (cached)", f"{BASE}/api/market_data/AAPL", ["ticker", "price", "ohlc"])
if d: print(f"    bars={len(d.get('ohlc', []))}, _cached={d.get('_cached')}")

# Monitor tick
d = test("monitor/tick", f"{BASE}/api/monitor/tick?tickers=AAPL,MSFT,NVDA", ["tickers"])
if d: print(f"    tickers_count={len(d.get('tickers', {}))}")

# Strategy analyze
d = test("strategy/analyze/AAPL", f"{BASE}/api/strategy/analyze/AAPL", ["ticker", "signal"])
if d: print(f"    signal={d.get('signal')}")

# Trader analyze
d = test("trader/analyze/AAPL", f"{BASE}/api/trader/analyze/AAPL", ["ticker"])
if d: print(f"    composite_score={d.get('composite_score')}")

# Factors
d = test("factors/AAPL", f"{BASE}/api/factors/AAPL", ["ticker"])
if d: print(f"    keys={list(d.keys())[:5]}")

# Backtest
d = test("strategy/backtest/AAPL", f"{BASE}/api/strategy/backtest/AAPL", ["ticker"])
if d: print(f"    total_return={d.get('total_return_pct')}")

# VizLab brain
d = test("vizlab/brain", f"{BASE}/api/vizlab/brain", ["nodes", "edges"])
if d: print(f"    nodes={len(d.get('nodes', []))}, edges={len(d.get('edges', []))}")

# Options surface
d = test("options/surface/SPY", f"{BASE}/api/options/surface/SPY", ["ticker"])
if d: print(f"    surface_points={len(d.get('surface', []))}")

# Analytics summary
d = test("analytics/summary/AAPL", f"{BASE}/api/analytics/summary/AAPL", ["ticker"])
if d: print(f"    keys={list(d.keys())[:5]}")

# Scenarios
try:
    import urllib.parse
    payload = json.dumps({"ticker": "AAPL", "scenarios": ["bull", "bear", "base"]}).encode()
    req = urllib.request.Request(f"{BASE}/api/scenarios/analyze", data=payload, headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=15)
    d = json.loads(r.read())
    print(f"[PASS] scenarios/analyze - keys={list(d.keys())[:4]}")
except Exception as e:
    print(f"[FAIL] scenarios/analyze - {e}")

# Device register
try:
    payload = json.dumps({"device_id": "test-device", "device_name": "Test"}).encode()
    req = urllib.request.Request(f"{BASE}/api/device/register", data=payload, headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=10)
    d = json.loads(r.read())
    print(f"[PASS] device/register - {d}")
except Exception as e:
    print(f"[FAIL] device/register - {e}")

print()
print("=== DONE ===")
