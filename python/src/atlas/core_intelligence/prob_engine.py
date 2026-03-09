import pandas as pd
import numpy as np
from typing import Dict

class ProbabilityEngine:
    """
    Phase 5: Converts raw signals and volatility into probabilities.
    Output: { bullish: 0.x, bearish: 0.y, neutral: 0.z }
    """
    
    def calculate_probabilities(self, signals: pd.DataFrame, volatility: pd.Series) -> Dict[str, float]:
        """
        Transform last signal + volatility context into probabilities.
        """
        last_signal = signals['combined_score'].iloc[-1]
        current_vol = volatility.iloc[-1] if not volatility.empty else 0.0
        
        # Base probability from signal strength (-3 to 3 approx)
        # Sigmoid function to map to 0-1
        bullish_prob = 1 / (1 + np.exp(-last_signal))
        bearish_prob = 1 - bullish_prob
        
        # Adjust for volatility (Higher vol = higher uncertainty/neutrality)
        uncertainty = min(current_vol * 10, 0.3) # Artificial scaling
        
        adjusted_bull = bullish_prob * (1 - uncertainty)
        adjusted_bear = bearish_prob * (1 - uncertainty)
        neutral = 1 - (adjusted_bull + adjusted_bear)
        
        return {
            "bullish": round(float(adjusted_bull), 4),
            "bearish": round(float(adjusted_bear), 4),
            "neutral": round(float(neutral), 4)
        }
