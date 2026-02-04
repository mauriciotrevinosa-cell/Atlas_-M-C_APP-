"""
ARIA Memory Retrieval
"""
class MemoryRetrieval:
    def __init__(self, conversation_memory, vector_memory):
        self.conv = conversation_memory
        self.vector = vector_memory
    
    def get_context(self, query: str, max_items: int = 5):
        recent = self.conv.get_recent(max_items)
        return recent
