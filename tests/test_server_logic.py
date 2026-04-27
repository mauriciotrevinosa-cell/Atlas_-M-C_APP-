
import sys
import os
import pandas as pd
import unittest
from unittest.mock import MagicMock

# Add python source to path
sys.path.append(os.path.join(os.getcwd(), "python", "src"))

from atlas.evaluation.scenario import ScenarioSession, NewsEngine, ScenarioState

class TestScenarioLogic(unittest.TestCase):
    
    def test_news_engine(self):
        print("\nTesting News Engine...")
        engine = NewsEngine("SPY")
        
        # Test loading events
        self.assertTrue(len(engine.events) > 0)
        
        # Test fetching specific date
        news = engine.get_news("2020-03-09") # Black Monday
        self.assertTrue(len(news) > 0)
        self.assertIn("BLACK MONDAY", news[0]['title'])
        print(f"✅ News Found: {news[0]['title']}")
        
        # Test empty date
        news_empty = engine.get_news("1999-01-01")
        self.assertEqual(len(news_empty), 0)
        print("✅ No news for 1999-01-01 (Correct)")

    def test_scenario_session_integration(self):
        print("\nTesting Scenario Session Integration...")
        
        # Create Mock Data
        dates = pd.date_range(start="2020-01-01", periods=100)
        data = pd.DataFrame({
            "close": [100 + i for i in range(100)],
            "volume": [1000] * 100
        }, index=dates)
        
        session = ScenarioSession(data, ticker="SPY")
        
        # Step 1
        state = session.next_step()
        self.assertIsNotNone(state)
        self.assertEqual(state.price, 100.0)
        print(f"✅ Step 1 State: {state.date} Price=${state.price}")
        
        # Check if News Engine was initialized
        self.assertIsNotNone(session.news_engine)
        
if __name__ == '__main__':
    unittest.main()
