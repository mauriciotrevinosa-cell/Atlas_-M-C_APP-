"""
Yahoo Finance Data Provider

Provider gratuito para datos históricos de mercado.

Soporta:
- Acciones (AAPL, GOOGL, etc.)
- Crypto (BTC-USD, ETH-USD)
- Forex (EURUSD=X)
- Índices (^GSPC, ^DJI)
- Futuros (GC=F, CL=F)

Copyright (c) 2026 M&C. All rights reserved.
"""

import yfinance as yf
import pandas as pd
from typing import Optional
from ..base import DataProvider
from ..quality.validator import DataValidator
from ..normalization.normalizer import DataNormalizer


class YahooProvider(DataProvider):
    """
    Yahoo Finance data provider
    
    Ventajas:
    - ✅ 100% GRATIS
    - ✅ No requiere API key
    - ✅ Datos históricos ilimitados
    - ✅ Multi-asset (stocks, crypto, forex, etc.)
    
    Limitaciones:
    - ⚠️  No real-time tick data
    - ⚠️  No order book / Level 2
    - ⚠️  Rate limits no documentados
    
    Example:
        >>> yahoo = YahooProvider()
        >>> data = yahoo.download("AAPL", "2024-01-01", "2024-12-31")
        >>> print(data.head())
    """
    
    version = "1.0.0"
    supported_assets = ["stocks", "crypto", "forex", "indices", "futures"]
    rate_limit = "No oficial (usar con moderación)"
    
    def download(self, symbol: str, start: str, end: str, 
                 interval: str = "1d") -> pd.DataFrame:
        """
        Descargar datos históricos de Yahoo Finance
        
        Args:
            symbol: Ticker symbol
                   Stocks: "AAPL", "GOOGL"
                   Crypto: "BTC-USD", "ETH-USD"
                   Forex: "EURUSD=X"
                   Indices: "^GSPC", "^DJI"
                   Futures: "GC=F", "CL=F"
            start: Fecha inicio (YYYY-MM-DD)
            end: Fecha fin (YYYY-MM-DD)
            interval: Timeframe
                     Valid: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        
        Returns:
            pd.DataFrame con columnas: Open, High, Low, Close, Volume
        
        Raises:
            ValueError: Si el símbolo es inválido
            Exception: Si hay errores de red o API
        """
        try:
            # Descargar con yfinance
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start, end=end, interval=interval)
            
            # Verificar que hay datos
            if data.empty:
                raise ValueError(f"No data found for {symbol} between {start} and {end}")
            
            # Remover columnas innecesarias
            columns_to_keep = ['Open', 'High', 'Low', 'Close', 'Volume']
            data = data[columns_to_keep]
            
            # Limpiar index (remover timezone info si existe)
            if data.index.tz is not None:
                data.index = data.index.tz_localize(None)
            
            return data
        
        except Exception as e:
            raise Exception(f"Error downloading {symbol} from Yahoo Finance: {str(e)}")
    
    def validate(self, data: pd.DataFrame) -> dict:
        """
        Validar calidad de datos
        
        Delega a DataValidator para consistencia
        """
        normalized_cols = data.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        return DataValidator().validate(normalized_cols)
    
    def normalize(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Normalizar formato
        
        Delega a DataNormalizer para consistencia
        """
        return DataNormalizer.to_atlas_format(data, provider="yahoo")
    
    def get_current_price(self, symbol: str) -> float:
        """
        Obtener precio actual (último cierre)
        
        Args:
            symbol: Ticker symbol
        
        Returns:
            float: Último precio de cierre
        
        Example:
            >>> yahoo = YahooProvider()
            >>> price = yahoo.get_current_price("AAPL")
            >>> print(f"AAPL: ${price:.2f}")
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Intentar varios campos (depende del tipo de asset)
            price = (
                info.get('currentPrice') or
                info.get('regularMarketPrice') or
                info.get('previousClose')
            )
            
            if price is None:
                raise ValueError(f"Could not get price for {symbol}")
            
            return float(price)
        
        except Exception as e:
            raise Exception(f"Error getting current price for {symbol}: {str(e)}")
    
    def get_info(self) -> dict:
        """Información del provider"""
        return {
            'name': 'Yahoo Finance',
            'version': self.version,
            'supported_assets': self.supported_assets,
            'rate_limit': self.rate_limit,
            'api_key_required': False,
            'cost': 'FREE',
            'data_quality': 'Good for EOD, acceptable for intraday'
        }


# ==================== TESTS ====================

if __name__ == "__main__":
    """
    Tests rápidos del Yahoo Provider
    
    Run:
        cd Atlas/python/src/atlas/data_layer/sources
        python yahoo.py
    """
    
    print("=" * 60)
    print("🧪 TESTING YAHOO FINANCE PROVIDER")
    print("=" * 60)
    
    yahoo = YahooProvider()
    
    # Test 1: Descargar AAPL
    print("\n[Test 1] Downloading AAPL (2024)...")
    try:
        data = yahoo.download("AAPL", "2024-01-01", "2024-12-31")
        print(f"✅ Success! Downloaded {len(data)} rows")
        print(data.head())
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 2: Descargar BTC-USD
    print("\n[Test 2] Downloading BTC-USD (last 30 days)...")
    try:
        data = yahoo.download("BTC-USD", "2024-12-01", "2024-12-31")
        print(f"✅ Success! Downloaded {len(data)} rows")
        print(data.tail())
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 3: Símbolo inválido
    print("\n[Test 3] Invalid symbol (INVALID123)...")
    try:
        data = yahoo.download("INVALID123", "2024-01-01", "2024-12-31")
        print(f"❌ Should have failed but didn't")
    except Exception as e:
        print(f"✅ Correctly failed: {e}")
    
    # Test 4: Current price
    print("\n[Test 4] Getting current price for AAPL...")
    try:
        price = yahoo.get_current_price("AAPL")
        print(f"✅ AAPL current price: ${price:.2f}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 5: Provider info
    print("\n[Test 5] Provider info...")
    info = yahoo.get_info()
    print("✅ Provider info:")
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 60)
