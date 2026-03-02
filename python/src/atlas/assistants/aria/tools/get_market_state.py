"""
Get Market State Tool for ARIA
=============================

Allows ARIA to analyze market regimes (Bull/Bear/Sideways) and volatility.
Use this when users ask "How is the market?", "Is it bullish?", "What's the regime?".

Copyright (c) 2026 M&C. All rights reserved.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from atlas.assistants.aria.tools.base import Tool
from atlas.data_layer import DataManager
from atlas.core_intelligence.market_state.regime import MarketStateAnalyzer, MarketRegime

class GetMarketStateTool(Tool):
    """
    Tool for analyzing market state (Regime & Volatility)
    """
    
    def __init__(self):
        super().__init__(
            name="get_market_state",
            description="Analyze market regime (Bull/Bear/Sideways) and volatility for a symbol",
            category="analysis"
        )
        
        self.add_parameter(
            "symbol",
            "string",
            "Ticker symbol (e.g., AAPL, SPY, BTC-USD)",
            required=True
        )
        
        self.add_parameter(
            "period",
            "string",
            "Analysis period (e.g., '1y', '6mo', 'ytd')",
            required=False,
            default="1y"
        )
        
        # Initialize DataManager & Analyzer
        self.dm = DataManager()
        self.analyzer = MarketStateAnalyzer()
        
    def execute(self, symbol: str, period: str = "1y") -> dict:
        """
        Execute market state analysis
        """
        try:
            print(f"📊 Analyzing market state for {symbol} ({period})...")
            
            # 1. Fetch Data
            df = self.dm.get_historical(symbol, timeframe=period)
            
            if df.empty:
                return {"error": f"No data found for {symbol}"}
                
            # 2. Analyze Regime
            state = self.analyzer.analyze(df)
            
            # 3. Format result strictly for ARIA to read
            return {
                "symbol": symbol,
                "period": period,
                "current_regime": state.regime.value,  # e.g., "BULL_TREND"
                "regime_confidence": f"{state.confidence:.1f}%",
                "volatility_regime": state.volatility_state, # e.g., "HIGH_VOLATILITY"
                "trend_strength": f"{state.trend_strength:.2f} (ADX)",
                "description": self._get_human_description(state)
            }
            
        except Exception as e:
            return {"error": str(e)}

    def _get_human_description(self, state) -> str:
        """Generate a short sentence describing the state"""
        regime = state.regime.value.replace("_", " ").title()
        vol = state.volatility_state.replace("_", " ").lower()
        return f"The market is in a {regime} with {vol}."

if __name__ == "__main__":
    tool = GetMarketStateTool()
    print(tool.execute("AAPL", "1y"))
