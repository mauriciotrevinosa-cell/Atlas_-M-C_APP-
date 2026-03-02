
import sys
import os
import pandas as pd

# Add python/src to path
sys.path.append(os.getcwd() + '/python/src')

try:
    print("🚀 Initializing DataManager...")
    from atlas.data_layer import DataManager
    dm = DataManager()
    
    symbol = "AAPL"
    start = "2024-01-01"
    end = "2024-01-31"
    
    print(f"\n📥 Fetching data for {symbol} ({start} to {end})...")
    df = dm.get_historical(symbol, start, end)
    
    print("\n✅ SUCCESS! Data retrieved:")
    print(df.head())
    print(f"\n📊 Stats: {len(df)} rows, Columns: {list(df.columns)}")
    
    # Test Timeframe
    print("\n⏳ Testing Timeframe 'ytd'...")
    df_ytd = dm.get_historical(symbol, timeframe="ytd")
    print(f"✅ YTD Fetch successful: {len(df_ytd)} rows from {df_ytd.index[0].date()} to {df_ytd.index[-1].date()}")
    
    print("\n⏳ Testing Timeframe '1mo'...")
    df_1mo = dm.get_historical(symbol, timeframe="1mo")
    print(f"✅ 1 Month Fetch successful: {len(df_1mo)} rows")

    # Test Cache (if implemented in this version)
    print("\n📦 Testing Cache Fetch (Second call should be faster)...")
    df_cache = dm.get_historical(symbol, start, end)
    print("✅ Cache fetch successful.")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
