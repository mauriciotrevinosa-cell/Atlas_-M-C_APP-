"""
ARIA Notion Integration - COMPLETE

Full integration with Notion API for knowledge base, notes, and databases

Features:
- Create/Read/Update pages
- Database operations (create, query, filter)
- Block operations (text, headings, lists, code, etc.)
- Search across workspace
- AI agent can read/write notes
"""

import requests
from typing import Dict, List, Any, Optional
from datetime import datetime


class NotionIntegration:
    """
    Complete Notion API integration
    
    Docs: https://developers.notion.com/
    """
    
    BASE_URL = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"
    
    def __init__(self, api_key: str):
        """
        Initialize Notion integration
        
        Args:
            api_key: Notion integration token
                     Get from: notion.so/my-integrations
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": self.NOTION_VERSION
        }
    
    # ==================== PAGES ====================
    
    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get page by ID"""
        response = requests.get(
            f"{self.BASE_URL}/pages/{page_id}",
            headers=self.headers
        )
        return self._handle_response(response)
    
    def create_page(self, parent_id: str, title: str, 
                   properties: Optional[Dict] = None,
                   children: Optional[List] = None) -> Dict[str, Any]:
        """
        Create a new page
        
        Args:
            parent_id: Parent page/database ID
            title: Page title
            properties: Page properties (for database pages)
            children: Page content blocks
        
        Example:
            page = notion.create_page(
                parent_id="database_id",
                title="AAPL Analysis - Jan 2024",
                properties={
                    "Status": {"select": {"name": "In Progress"}},
                    "Priority": {"number": 1}
                },
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": "Analysis results..."}}]
                        }
                    }
                ]
            )
        """
        parent = {"type": "database_id", "database_id": parent_id} if properties else \
                 {"type": "page_id", "page_id": parent_id}
        
        data = {
            "parent": parent,
            "properties": {
                "title": {
                    "title": [{"type": "text", "text": {"content": title}}]
                },
                **(properties or {})
            }
        }
        
        if children:
            data["children"] = children
        
        response = requests.post(
            f"{self.BASE_URL}/pages",
            headers=self.headers,
            json=data
        )
        return self._handle_response(response)
    
    def update_page(self, page_id: str, properties: Dict) -> Dict[str, Any]:
        """Update page properties"""
        data = {"properties": properties}
        response = requests.patch(
            f"{self.BASE_URL}/pages/{page_id}",
            headers=self.headers,
            json=data
        )
        return self._handle_response(response)
    
    # ==================== BLOCKS ====================
    
    def get_block_children(self, block_id: str) -> Dict[str, Any]:
        """Get all children blocks of a block/page"""
        response = requests.get(
            f"{self.BASE_URL}/blocks/{block_id}/children",
            headers=self.headers
        )
        return self._handle_response(response)
    
    def append_block_children(self, block_id: str, children: List[Dict]) -> Dict[str, Any]:
        """
        Append blocks to a page
        
        Args:
            block_id: Parent block/page ID
            children: List of blocks to append
        
        Example:
            notion.append_block_children(
                block_id="page_id",
                children=[
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "Analysis Results"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": "RSI: 45, MACD: Bullish"}}]
                        }
                    }
                ]
            )
        """
        data = {"children": children}
        response = requests.patch(
            f"{self.BASE_URL}/blocks/{block_id}/children",
            headers=self.headers,
            json=data
        )
        return self._handle_response(response)
    
    # ==================== DATABASES ====================
    
    def query_database(self, database_id: str, 
                      filter_obj: Optional[Dict] = None,
                      sorts: Optional[List] = None) -> Dict[str, Any]:
        """
        Query database with filters and sorts
        
        Example:
            results = notion.query_database(
                database_id="db_id",
                filter_obj={
                    "property": "Status",
                    "select": {"equals": "In Progress"}
                },
                sorts=[{"property": "Priority", "direction": "ascending"}]
            )
        """
        data = {}
        if filter_obj:
            data["filter"] = filter_obj
        if sorts:
            data["sorts"] = sorts
        
        response = requests.post(
            f"{self.BASE_URL}/databases/{database_id}/query",
            headers=self.headers,
            json=data
        )
        return self._handle_response(response)
    
    def get_database(self, database_id: str) -> Dict[str, Any]:
        """Get database schema"""
        response = requests.get(
            f"{self.BASE_URL}/databases/{database_id}",
            headers=self.headers
        )
        return self._handle_response(response)
    
    def create_database(self, parent_page_id: str, title: str, 
                       properties: Dict) -> Dict[str, Any]:
        """
        Create a new database
        
        Example:
            db = notion.create_database(
                parent_page_id="page_id",
                title="Trading Journal",
                properties={
                    "Symbol": {"title": {}},
                    "Entry Price": {"number": {"format": "dollar"}},
                    "Status": {"select": {"options": [
                        {"name": "Open", "color": "green"},
                        {"name": "Closed", "color": "gray"}
                    ]}},
                    "Date": {"date": {}}
                }
            )
        """
        data = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties
        }
        response = requests.post(
            f"{self.BASE_URL}/databases",
            headers=self.headers,
            json=data
        )
        return self._handle_response(response)
    
    # ==================== SEARCH ====================
    
    def search(self, query: str, filter_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Search workspace
        
        Args:
            query: Search query
            filter_type: "page" or "database" (None = all)
        """
        data = {"query": query}
        if filter_type:
            data["filter"] = {"value": filter_type, "property": "object"}
        
        response = requests.post(
            f"{self.BASE_URL}/search",
            headers=self.headers,
            json=data
        )
        return self._handle_response(response)
    
    # ==================== AI AGENT HELPERS ====================
    
    def create_note(self, parent_id: str, title: str, content: str) -> Dict[str, Any]:
        """
        ARIA creates a note (simplified)
        
        Usage: "ARIA, create note about today's market analysis"
        """
        children = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                }
            }
        ]
        return self.create_page(parent_id, title, children=children)
    
    def append_to_journal(self, page_id: str, entry: str) -> Dict[str, Any]:
        """
        Add entry to trading journal
        
        Usage: "ARIA, log: Entered AAPL at $180, target $190"
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        children = [
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": timestamp}}]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": entry}}]
                }
            }
        ]
        return self.append_block_children(page_id, children)
    
    def create_trade_record(self, database_id: str, symbol: str, 
                           entry_price: float, **kwargs) -> Dict[str, Any]:
        """
        Create trade record in database
        
        Example:
            trade = notion.create_trade_record(
                database_id="db_id",
                symbol="AAPL",
                entry_price=180.50,
                status="Open",
                notes="Bullish breakout"
            )
        """
        properties = {
            "Symbol": {"title": [{"text": {"content": symbol}}]},
            "Entry Price": {"number": entry_price},
            "Date": {"date": {"start": datetime.now().isoformat()}}
        }
        
        # Add optional properties
        if "status" in kwargs:
            properties["Status"] = {"select": {"name": kwargs["status"]}}
        if "notes" in kwargs:
            properties["Notes"] = {"rich_text": [{"text": {"content": kwargs["notes"]}}]}
        
        return self.create_page(database_id, symbol, properties=properties)
    
    def read_page_content(self, page_id: str) -> str:
        """
        Read page content as plain text
        
        Usage: "ARIA, what does my strategy doc say?"
        """
        blocks = self.get_block_children(page_id)
        
        if not blocks["success"]:
            return "Error reading page"
        
        content = []
        for block in blocks["data"].get("results", []):
            block_type = block.get("type")
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3"]:
                rich_text = block.get(block_type, {}).get("rich_text", [])
                text = " ".join([t.get("plain_text", "") for t in rich_text])
                content.append(text)
        
        return "\n\n".join(content)
    
    # ==================== HELPER METHODS ====================
    
    def _handle_response(self, response) -> Dict[str, Any]:
        """Handle API response"""
        if response.status_code in [200, 201]:
            return {"success": True, "data": response.json()}
        else:
            return {
                "success": False,
                "error": response.text,
                "status_code": response.status_code
            }
    
    def get_parameters_schema(self) -> Dict:
        """Schema for Ollama tool calling"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create_note", "read_page", "append_to_journal", 
                            "create_trade_record", "search"],
                    "description": "Notion action to perform"
                },
                "parent_id": {
                    "type": "string",
                    "description": "Parent page/database ID"
                },
                "page_id": {
                    "type": "string",
                    "description": "Page ID to read/update"
                },
                "title": {
                    "type": "string",
                    "description": "Page title"
                },
                "content": {
                    "type": "string",
                    "description": "Page content"
                },
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            }
        }


# ==================== USAGE EXAMPLES ====================

if __name__ == "__main__":
    # Initialize
    API_KEY = "secret_YOUR_INTEGRATION_TOKEN"  # From notion.so/my-integrations
    notion = NotionIntegration(API_KEY)
    
    # Example 1: Search workspace
    print("=" * 60)
    print("Example 1: Search Workspace")
    # results = notion.search("trading")
    # print(f"Found {len(results.get('data', {}).get('results', []))} results")
    
    # Example 2: Create note
    print("\n" + "=" * 60)
    print("Example 2: ARIA creates note")
    # note = notion.create_note(
    #     parent_id="PAGE_ID",
    #     title="Market Analysis - Jan 2024",
    #     content="Today's analysis shows strong bullish momentum in tech stocks..."
    # )
    # print(f"Note created: {note}")
    
    # Example 3: Read page content
    print("\n" + "=" * 60)
    print("Example 3: ARIA reads strategy doc")
    # content = notion.read_page_content("PAGE_ID")
    # print(f"Content: {content[:200]}...")
    
    print("\n" + "=" * 60)
    print("✅ Notion integration ready!")
    print("Next: Share pages with your integration")
