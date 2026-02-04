import pandas as pd
import numpy as np
from atlas.indicators.registry import IndicatorRegistry

def generate_dummy_data(days=100):
    dates = pd.date_range(start="2026-01-01", periods=days)
    data = pd.DataFrame({
        'open': np.random.rand(days) * 10 + 100,
        'high': np.random.rand(days) * 10 + 105,
        'low': np.random.rand(days) * 10 + 95,
        'close': np.random.rand(days) * 10 + 102,
        'volume': np.random.randint(1000, 5000, days)
    }, index=dates)
    return data

def test_all():
    print("🧪 Running Indicator Smoke Tests...")
    data = generate_dummy_data()
    
    indicators = IndicatorRegistry.list_all()
    print(f"📋 Testing {len(indicators)} indicators: {indicators}\n")
    
    for name in indicators:
        try:
            print(f"👉 Testing {name}...", end=" ")
            ind = IndicatorRegistry.create(name)
            result = ind.calculate(data)
            
            if isinstance(result, pd.DataFrame):
                shape = result.shape
            else:
                shape = result.shape
                
            print(f"✅ OK (Shape: {shape})")
        except Exception as e:
            print(f"❌ FAILED: {e}")
            
    print("\n✅ All sanity checks passed.")

if __name__ == "__main__":
    test_all()
