"""
Explain Signal Tool
==================

Allows ARIA to generate and explain trading signals using Phase 5 Signal Engine.
"""

from typing import Dict, Any
from atlas.assistants.aria.tools.base import Tool
from atlas.core_intelligence.signal_engine import SignalEngine
from atlas.data_layer.manager import DataManager

class ExplainSignalTool(Tool):
    def __init__(self):
        super().__init__(
            name="explain_signal",
            description="Generate and explain trading signals for an asset. Use this when asked 'should I buy?', 'what is the signal?', or 'analyze {asset}'.",
            category="analysis"
        )
        self.add_parameter("symbol", "string", "Asset symbol to analyze")
        
        self.signal_engine = SignalEngine()
        self.data_manager = DataManager()
        
    def execute(self, symbol: str) -> Dict[str, Any]:
        """
        Generate a signal and explain the reasoning.
        """
        try:
            # 1. Get Data
            data = self.data_manager.get_historical(symbol, timeframe="6mo")
            
            # 2. Run Signal Engine
            signal = self.signal_engine.generate_signal(symbol, data)
            
            # 3. Format output
            return {
                "asset": symbol,
                "action": signal.action,  # BUY, SELL, HOLD
                "confidence": signal.confidence,
                "reasoning": signal.metadata.get("analysis", "No detailed analysis provided"),
                "conflicts": signal.metadata.get("conflicts", [])
            }
        except Exception as e:
            return {"error": f"Signal generation failed: {str(e)}"}
