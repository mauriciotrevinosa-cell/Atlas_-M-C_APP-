"""
Data Layer - Demo Completo

Ejemplo de cómo usar el Data Layer de Atlas.

Run:
    cd Atlas/python
    python examples/data_layer_demo.py

Copyright (c) 2026 M&C. All rights reserved.
"""

from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from atlas.data_layer import get_data
from atlas.data_layer.sources.yahoo import YahooProvider
from atlas.data_layer.quality.validator import DataValidator
from atlas.data_layer.cache import CacheManager


def demo_basic_download():
    """Demo 1: Descarga básica"""
    print("\n" + "=" * 60)
    print("DEMO 1: Descarga Básica")
    print("=" * 60)
    
    # Descargar AAPL 2024
    print("\n📥 Downloading AAPL (2024)...")
    data = get_data("AAPL", "2024-01-01", "2024-12-31")
    
    print(f"✅ Downloaded {len(data)} rows")
    print("\nFirst 5 rows:")
    print(data.head())
    print("\nLast 5 rows:")
    print(data.tail())
    print(f"\nMetadata: {data.attrs}")


def demo_multi_asset():
    """Demo 2: Múltiples assets"""
    print("\n" + "=" * 60)
    print("DEMO 2: Múltiples Assets")
    print("=" * 60)
    
    symbols = ["AAPL", "GOOGL", "BTC-USD", "ETH-USD"]
    
    for symbol in symbols:
        print(f"\n📥 Downloading {symbol}...")
        data = get_data(symbol, "2024-11-01", "2024-12-31", use_cache=True)
        
        last_price = data['Close'].iloc[-1]
        print(f"✅ {symbol}: Last close = ${last_price:.2f}")


def demo_data_quality():
    """Demo 3: Validación de calidad"""
    print("\n" + "=" * 60)
    print("DEMO 3: Validación de Calidad")
    print("=" * 60)
    
    print("\n📥 Downloading data...")
    data = get_data("AAPL", "2024-01-01", "2024-12-31", use_cache=True)
    
    print("\n🔍 Running quality checks...")
    validation = DataValidator.validate_all(data)
    
    print(f"\n✅ Overall Quality: {validation['overall_quality']}")
    print(f"   Missing data: {validation['missing_data']['missing_pct']:.2f}%")
    print(f"   Price spikes: {validation['price_spikes']['spike_count']}")
    print(f"   Date gaps: {validation['gaps']['gap_count']}")
    print(f"   Volume anomalies: {validation['volume_anomalies']['zero_volume_count']}")


def demo_cache_system():
    """Demo 4: Sistema de cache"""
    print("\n" + "=" * 60)
    print("DEMO 4: Sistema de Cache")
    print("=" * 60)
    
    cache = CacheManager()
    
    # Primera descarga (sin cache)
    print("\n⏱️  First download (no cache)...")
    import time
    start = time.time()
    data1 = get_data("AAPL", "2024-01-01", "2024-12-31", use_cache=True)
    time1 = time.time() - start
    print(f"   Time: {time1:.2f}s")
    
    # Segunda descarga (con cache)
    print("\n⚡ Second download (from cache)...")
    start = time.time()
    data2 = get_data("AAPL", "2024-01-01", "2024-12-31", use_cache=True)
    time2 = time.time() - start
    print(f"   Time: {time2:.2f}s")
    
    print(f"\n✅ Speedup: {time1/time2:.1f}x faster with cache")
    
    # Stats de cache
    stats = cache.get_stats()
    print(f"\n📊 Cache Stats:")
    print(f"   Total files: {stats['total_files']}")
    print(f"   Total size: {stats['total_size_mb']:.2f} MB")


def demo_provider_directly():
    """Demo 5: Usar provider directamente"""
    print("\n" + "=" * 60)
    print("DEMO 5: Usar Provider Directamente")
    print("=" * 60)
    
    yahoo = YahooProvider()
    
    # Info del provider
    info = yahoo.get_info()
    print("\n📋 Yahoo Finance Provider Info:")
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    # Descargar datos
    print("\n📥 Downloading with provider...")
    data = yahoo.download("AAPL", "2024-12-01", "2024-12-31")
    
    # Validar
    print("\n🔍 Validating...")
    validation = yahoo.validate(data)
    print(f"   Quality: {validation['overall_quality']}")
    
    # Normalizar
    print("\n🔧 Normalizing...")
    normalized = yahoo.normalize(data)
    print(f"   Timezone: {normalized.index.tz}")
    print(f"   Columns: {list(normalized.columns)}")


def main():
    """
    Run all demos
    """
    print("\n" + "=" * 60)
    print("🚀 ATLAS DATA LAYER - DEMO COMPLETO")
    print("=" * 60)
    
    try:
        demo_basic_download()
        demo_multi_asset()
        demo_data_quality()
        demo_cache_system()
        demo_provider_directly()
        
        print("\n" + "=" * 60)
        print("✅ ALL DEMOS COMPLETED SUCCESSFULLY")
        print("=" * 60)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
