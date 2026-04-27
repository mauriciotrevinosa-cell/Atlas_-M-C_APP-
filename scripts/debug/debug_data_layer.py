
import sys
import os
sys.path.append(os.getcwd() + '/python/src')

try:
    from atlas.data_layer import get_data
    print("Import successful")
    data = get_data("AAPL", "2024-01-01", "2024-01-05")
    print("Data download successful")
    print(data.head())
except Exception as e:
    print(f"Error: {e}")
