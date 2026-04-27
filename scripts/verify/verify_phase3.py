
import sys
import os
import pandas as pd
import numpy as np

# Ensure we can import the project
sys.path.append(os.path.join(os.getcwd(), 'python', 'src'))

try:
    from atlas.features import FeatureRegistry
    from atlas.features.technical import trend, momentum, volatility, volume
    from atlas.features.microstructure import vpin, kyle_lambda, order_book_imbalance
    
    print("✅ Successfully imported atlas.features modules")
    
    # Create dummy data
    dates = pd.date_range('2024-01-01', periods=100)
    data = pd.DataFrame({
        'Open': np.linspace(100, 110, 100) + np.random.randn(100),
        'High': np.linspace(102, 112, 100) + np.random.randn(100),
        'Low': np.linspace(98, 108, 100) + np.random.randn(100),
        'Close': np.linspace(100, 110, 100) + np.random.randn(100),
        'Volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    print("\n--- Testing Technical Indicators ---")
    sma = trend.sma(data['Close'], 20)
    print(f"SMA(20) last: {sma.iloc[-1]:.2f}")
    
    rsi = momentum.rsi(data['Close'], 14)
    print(f"RSI(14) last: {rsi.iloc[-1]:.2f}")
    
    atr = volatility.atr(data, 14)
    print(f"ATR(14) last: {atr.iloc[-1]:.2f}")
    
    obv = volume.obv(data)
    print(f"OBV last: {obv.iloc[-1]:.0f}")
    
    print("\n--- Testing Microstructure ---")
    vpin_calc = vpin.VPIN(bucket_size=5000, n_buckets=5)
    vpin_val = vpin_calc.calculate(data)
    print(f"VPIN last: {vpin_val.iloc[-1]:.4f}")
    
    k_lambda = kyle_lambda.estimate_kyle_lambda(data, window=20)
    print(f"Kyle's Lambda last: {k_lambda.iloc[-1]:.6f}")
    
    # Mock order book data for OBI
    bid_vol = pd.Series(np.random.randint(100, 500, 100), index=dates)
    ask_vol = pd.Series(np.random.randint(100, 500, 100), index=dates)
    obi = order_book_imbalance.calculate_obi(bid_vol, ask_vol)
    print(f"OBI last: {obi.iloc[-1]:.4f}")
    
    print("\n--- Testing Registry ---")
    registry = FeatureRegistry()
    registry.register("sma_20", lambda d: trend.sma(d['Close'], 20))
    registry.register("rsi_14", lambda d: momentum.rsi(d['Close'], 14))
    
    results = registry.calculate_all(data)
    print(f"Registry results shape: {results.shape}")
    print(f"Registry columns: {results.columns.tolist()}")

    print("\n🎉 ALL PHASE 3 TESTS PASSED")

except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
