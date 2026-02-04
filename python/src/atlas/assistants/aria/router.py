# Router for ARIA interactions with the Brain
from atlas.data_layer.cache_store import CacheStore
from atlas.core_intelligence.signal_engine import SignalEngine
from atlas.backtesting.runner import BacktestRunner
from atlas.memory.store import MemoryStore

class BrainRouter:
    """
    Phase 8: Interface between ARIA (LLM) and Atlas Core Engines.
    Allows ARIA to 'use' the brain modules via Python calls.
    """
    
    def __init__(self):
        self.signal_engine = SignalEngine()
        self.backtester = BacktestRunner()
        self.memory = MemoryStore()
        self.cache = CacheStore()
        
    def query_signal(self, symbol: str) -> dict:
        """Get current technical signal for a symbol."""
        # 1. Fetch data (Mocked for now or via Cache)
        # data = self.cache.get(symbol) ...
        # For MVP we assume data is passed or fetched here
        return {"status": "Not implemented - requires live data fetch"}
        
    def run_simulation(self, strategy: str) -> dict:
        """Run a simulation via ARIA command."""
        # result = self.backtester.run(...)
        return {"result": "Simulation started..."}
