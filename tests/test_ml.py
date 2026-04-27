import sys
sys.path.insert(0, r"C:\Users\mauri\OneDrive\Desktop\Atlas\python\src")

import yfinance as yf
import pandas as pd

print("=== Testing FeaturePipeline ===")
try:
    from atlas.core_intelligence.engines.ml.ml_suite import (
        FeaturePipeline, XGBoostEngine, RandomForestEngine
    )
    print("[PASS] Imports OK")
    
    # Get data
    t = yf.Ticker("AAPL")
    hist = t.history(period="2y", auto_adjust=True)
    hist_norm = hist.copy()
    hist_norm.columns = [c.lower() for c in hist_norm.columns]
    print(f"[INFO] Data shape: {hist_norm.shape}")
    print(f"[INFO] Columns: {list(hist_norm.columns)}")
    
    # Test FeaturePipeline
    pipeline = FeaturePipeline(lookback=20, horizon=5)
    print(f"[INFO] FeaturePipeline methods: {[m for m in dir(pipeline) if not m.startswith('_')]}")
    
    # Try build()
    try:
        result = pipeline.build(hist_norm, label_method="direction")
        print(f"[PASS] pipeline.build() returned: {type(result)}")
        if isinstance(result, tuple):
            X, y = result
            print(f"       X shape: {X.shape}, y shape: {y.shape}")
    except Exception as e:
        print(f"[FAIL] pipeline.build(): {e}")
        import traceback; traceback.print_exc()
    
    # Try build_features()
    try:
        X = pipeline.build_features(hist_norm)
        print(f"[PASS] build_features() shape: {X.shape}")
    except Exception as e:
        print(f"[FAIL] build_features(): {e}")
    
    # Try XGBoostEngine
    try:
        xgb = XGBoostEngine(name="test_xgb", model_dir=r"C:\Users\mauri\OneDrive\Desktop\Atlas\data\models")
        print(f"[PASS] XGBoostEngine created")
    except Exception as e:
        print(f"[FAIL] XGBoostEngine: {e}")

except Exception as e:
    print(f"[FAIL] {e}")
    import traceback; traceback.print_exc()
