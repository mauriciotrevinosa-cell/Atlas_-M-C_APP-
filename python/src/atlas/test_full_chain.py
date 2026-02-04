import pandas as pd
import numpy as np
from atlas.core_intelligence.signal_engine import SignalEngine
from atlas.core_intelligence.prob_engine import ProbabilityEngine
from atlas.backtesting.runner import BacktestRunner
from atlas.memory.store import MemoryStore

def generate_market_data(days=200):
    """Generate mock market data with a trend."""
    dates = pd.date_range(start="2025-01-01", periods=days)
    # Simulate a trending market
    prices = [100]
    for _ in range(days-1):
        change = np.random.normal(0.5, 2.0) # slightly bullish bias
        prices.append(prices[-1] + change)
        
    data = pd.DataFrame({
        'close': prices,
        'open': prices, # Simplified
        'high': [p + 1 for p in prices],
        'low': [p - 1 for p in prices],
        'volume': np.random.randint(1000, 10000, days)
    }, index=dates)
    return data

def test_full_chain():
    print("🔗 Running ATLAS FULL CHAIN Test (Simulating Phase 4-8 interaction)...")
    
    # 0. Data Ingestion (Mocked Phase 1)
    data = generate_market_data()
    print(f"✅ Data Generated: {len(data)} bars")
    
    # 1. Signal Generation (Phase 4)
    sig_engine = SignalEngine()
    signals = sig_engine.evaluate(data, "trend_following")
    last_sig = signals['signal'].iloc[-1]
    print(f"✅ Signal Engine: Last Signal = {last_sig}")
    
    # 2. Probability Analysis (Phase 5)
    prob_engine = ProbabilityEngine()
    volatility = data['close'].pct_change().rolling(20).std()
    probs = prob_engine.calculate_probabilities(signals, volatility)
    print(f"✅ Probability Engine: {probs}")
    
    # 3. Backtesting (Phase 6)
    backtester = BacktestRunner(initial_capital=10000)
    results = backtester.run(data, "trend_following")
    print(f"✅ Backtest Runner: Return = {results['total_return_pct']}% | Sharpe = {results['sharpe_ratio']}")
    
    # 4. Memory Storage (Phase 7)
    memory = MemoryStore("data/test_memory.json")
    memory.save_run(results)
    print(f"✅ Memory Store: Test run saved to data/test_memory.json")
    
    print("\n🚀 FULL CHAIN SUCCESSFUL. Atlas Core is operational.")

if __name__ == "__main__":
    test_full_chain()
