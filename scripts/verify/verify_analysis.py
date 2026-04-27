
import requests
import time
import sys
import json

BASE_URL = "http://localhost:8000"

def test_market_data():
    print("\n--- Testing Live Market Data API ---")
    ticker = "SPY"
    try:
        url = f"{BASE_URL}/api/market_data/{ticker}"
        print(f"GET {url}")
        res = requests.get(url)
        
        if res.status_code == 200:
            data = res.json()
            print("✅ Success!")
            print(f"Ticker: {data['ticker']}")
            print(f"Price: {data['price']}")
            print(f"OHLC Candles: {len(data['ohlc'])}")
            print(f"News Items: {len(data['news'])}")
            if data['news']:
                print(f"Latest News: {data['news'][0]['title']}")
        else:
            print(f"❌ Failed: {res.status_code} - {res.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connecton Error: Is the server running?")

def test_scenario_news():
    print("\n--- Testing Scenario News Engine ---")
    try:
        # 1. Start Scenario
        url = f"{BASE_URL}/api/scenario/start"
        payload = {"ticker": "SPY", "start_date": "2020-01-01", "initial_capital": 10000}
        print(f"POST {url}")
        res = requests.post(url, json=payload)
        
        if res.status_code != 200:
            print(f"❌ Start Failed: {res.text}")
            return

        session_id = res.json()['session_id']
        print(f"Session started: {session_id}")
        
        # 2. Step through to find news (e.g. Feb 2020)
        print("Stepping through simulation...")
        news_found = False
        
        # We need to step enough times to hit a news event (e.g. Feb 20, 2020)
        # 2020-01-01 to 2020-02-20 is about 35 trading days
        for i in range(40):
            res = requests.post(f"{BASE_URL}/api/scenario/{session_id}/next")
            state = res.json().get('state')
            if not state: break
            
            date = state['date']
            reasoning = state['reasoning']
            
            # Check for news in reasoning
            for line in reasoning:
                if "NEWS:" in line:
                    print(f"✅ News Found on {date}: {line}")
                    news_found = True
                    
            if news_found: break
            
        if not news_found:
            print("⚠️ No news found in first 40 steps (might need more steps or check date logic)")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_market_data()
    test_scenario_news()
