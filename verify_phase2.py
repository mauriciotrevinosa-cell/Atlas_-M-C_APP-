
import sys
import os
import pandas as pd
import numpy as np

# Ensure we can import the project
sys.path.append(os.path.join(os.getcwd(), 'python', 'src'))

try:
    from atlas.market_state import RegimeDetector, VolatilityRegime, MarketInternals, SentimentAnalyzer
    print("✅ Successfully imported atlas.market_state")
    
    # Create dummy data
    dates = pd.date_range('2024-01-01', periods=100)
    data = pd.DataFrame({
        'Open': np.linspace(100, 110, 100),
        'High': np.linspace(101, 111, 100),
        'Low': np.linspace(99, 109, 100),
        'Close': np.linspace(100, 110, 100),
        'Volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    print("Testing RegimeDetector...")
    rd = RegimeDetector(lookback=10)
    regime = rd.detect(data)
    print(f"  Regime: {regime}")
    
    print("Testing VolatilityRegime...")
    vr = VolatilityRegime(lookback=20)
    vol = vr.classify(data)
    print(f"  Vol Regime: {vol}")
    
    print("Testing MarketInternals...")
    mi = MarketInternals()
    stats = mi.calculate(data)
    print(f"  Stats: {stats}")
    
    print("Testing SentimentAnalyzer...")
    sa = SentimentAnalyzer()
    sent = sa.analyze(data)
    print(f"  Sentiment: {sent}")
    
    print("\n🎉 ALL TESTS PASSED")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    sys.exit(1)
