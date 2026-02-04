"""
ARIA Web Search Tool

Search the web using DuckDuckGo (FREE, no API key needed)
"""

from typing import Dict, List, Any, Optional
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    print("⚠️  duckduckgo-search not installed. Run: pip install duckduckgo-search")


class WebSearchTool:
    """
    Web search tool using DuckDuckGo
    
    Features:
    - FREE (no API key needed)
    - No rate limits
    - Privacy-focused
    - Text search
    - News search
    """
    
    name = "web_search"
    description = "Search the web for current information, news, and real-time data"
    
    def __init__(self):
        """Initialize web search tool"""
        self.available = DDGS_AVAILABLE
    
    def execute(self, 
                query: str,
                max_results: int = 5,
                region: str = "wt-wt",
                time_range: Optional[str] = None) -> Dict[str, Any]:
        """
        Search the web
        
        Args:
            query: Search query
            max_results: Maximum number of results (default: 5)
            region: Region code (default: "wt-wt" = worldwide)
            time_range: Time range ("d"=day, "w"=week, "m"=month, "y"=year)
        
        Returns:
            Dict with search results
        """
        if not self.available:
            return {
                "success": False,
                "error": "DuckDuckGo search not available. Install: pip install duckduckgo-search"
            }
        
        try:
            # Initialize DDGS
            ddgs = DDGS()
            
            # Search
            results = []
            
            # Text search
            search_kwargs = {
                "keywords": query,
                "region": region,
                "max_results": max_results
            }
            
            if time_range:
                search_kwargs["timelimit"] = time_range
            
            for result in ddgs.text(**search_kwargs):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", ""),
                    "source": "DuckDuckGo"
                })
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results)
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Search failed: {str(e)}"
            }
    
    def search_news(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Search news specifically
        
        Args:
            query: Search query
            max_results: Maximum results
        
        Returns:
            Dict with news results
        """
        if not self.available:
            return {
                "success": False,
                "error": "DuckDuckGo search not available"
            }
        
        try:
            ddgs = DDGS()
            results = []
            
            for result in ddgs.news(keywords=query, max_results=max_results):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("body", ""),
                    "date": result.get("date", ""),
                    "source": result.get("source", "DuckDuckGo News")
                })
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results),
                "type": "news"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"News search failed: {str(e)}"
            }
    
    def get_parameters_schema(self) -> Dict:
        """Get tool parameter schema for Ollama function calling"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (1-20)",
                    "default": 5
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range: 'd'=day, 'w'=week, 'm'=month, 'y'=year",
                    "enum": ["d", "w", "m", "y"]
                }
            },
            "required": ["query"]
        }


if __name__ == "__main__":
    # Test
    print("Testing WebSearchTool...")
    print("=" * 60)
    
    tool = WebSearchTool()
    
    if tool.available:
        # Test 1: Basic search
        print("\nTest 1: Basic web search")
        result = tool.execute("Python programming", max_results=3)
        
        if result["success"]:
            print(f"✅ Found {result['count']} results")
            for i, r in enumerate(result["results"], 1):
                print(f"\n{i}. {r['title']}")
                print(f"   {r['url']}")
        else:
            print(f"❌ Error: {result['error']}")
        
        # Test 2: News search
        print("\n" + "=" * 60)
        print("Test 2: News search")
        result = tool.search_news("Tesla stock", max_results=3)
        
        if result["success"]:
            print(f"✅ Found {result['count']} news results")
            for i, r in enumerate(result["results"], 1):
                print(f"\n{i}. {r['title']}")
                print(f"   {r['url']}")
                print(f"   Date: {r.get('date', 'N/A')}")
        else:
            print(f"❌ Error: {result['error']}")
    else:
        print("❌ DuckDuckGo search not available")
        print("Install: pip install duckduckgo-search")
    
    print("\n" + "=" * 60)
