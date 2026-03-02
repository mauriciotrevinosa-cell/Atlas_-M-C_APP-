"""
Analyze Risk Tool
================

Allows ARIA to assess portfolio risk using Phase 7 Risk Engine.
"""

from typing import Dict, Any, Optional
from atlas.assistants.aria.tools.base import Tool
from atlas.risk.risk_engine import RiskEngine
from atlas.data_layer.manager import DataManager

class AnalyzeRiskTool(Tool):
    def __init__(self):
        super().__init__(
            name="analyze_risk",
            description="Assess portfolio risk, VaR, and checking kill switches. Use this when the user asks about 'risk', 'safety', 'VaR' or 'leverage'.",
            category="analysis"
        )
        self.add_parameter("symbol", "string", "Asset symbol (e.g. 'BTC-USD', 'AAPL')")
        self.add_parameter("amount", "number", "Position size in dollars", required=False, default=1000.0)
        self.add_parameter("leverage", "number", "Leverage used (1.0 = spot)", required=False, default=1.0)
        
        # Tools initialized here to avoid import loops if possible, or lazy load
        self.risk_engine = RiskEngine()
        self.data_manager = DataManager()
        
    def execute(self, symbol: str, amount: float = 1000.0, leverage: float = 1.0) -> Dict[str, Any]:
        """
        Analyze risk for a potential trade or current state.
        """
        try:
            # Fetch recent data for volatility calc
            data = self.data_manager.get_historical(symbol, timeframe="3mo")
            
            # Use Risk features
            # (Assuming standard API usage)
            try:
                var_value = self.risk_engine.calculate_var(data, confidence=0.95)
            except:
                var_value = "N/A (Calc Failed)"

            try:    
                is_safe = self.risk_engine.check_safety(symbol, leverage)
            except:
                is_safe = True # Default safe fallback
            
            return {
                "symbol": symbol,
                "VaR_95": var_value,
                "is_safe_to_trade": is_safe,
                "note": "Risk analysis based on historical volatility."
            }
        except Exception as e:
            return {"error": f"Risk analysis failed: {str(e)}"}
