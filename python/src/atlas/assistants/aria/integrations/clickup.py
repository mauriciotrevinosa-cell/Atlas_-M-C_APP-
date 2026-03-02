"""
ARIA ClickUp Integration - COMPLETE

Full integration with ClickUp API for task management, automation, and AI agent access

Features:
- Create/Read/Update/Delete tasks
- List spaces, folders, lists
- Time tracking
- Comments and attachments
- Custom fields
- Webhooks for 24/7 monitoring
- AI agent communication via comments
"""

import requests
from typing import Dict, List, Any, Optional
from datetime import datetime


class ClickUpIntegration:
    """
    Complete ClickUp API integration
    
    Docs: https://clickup.com/api/
    """
    
    BASE_URL = "https://api.clickup.com/api/v2"
    
    def __init__(self, api_key: str):
        """
        Initialize ClickUp integration
        
        Args:
            api_key: ClickUp API key (get from: clickup.com/settings/apps)
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }
    
    # ==================== WORKSPACES ====================
    
    def get_workspaces(self) -> Dict[str, Any]:
        """Get all workspaces (teams)"""
        response = requests.get(
            f"{self.BASE_URL}/team",
            headers=self.headers
        )
        return self._handle_response(response)
    
    # ==================== SPACES ====================
    
    def get_spaces(self, team_id: str) -> Dict[str, Any]:
        """Get all spaces in a workspace"""
        response = requests.get(
            f"{self.BASE_URL}/team/{team_id}/space",
            headers=self.headers
        )
        return self._handle_response(response)
    
    def create_space(self, team_id: str, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new space"""
        data = {"name": name, **kwargs}
        response = requests.post(
            f"{self.BASE_URL}/team/{team_id}/space",
            headers=self.headers,
            json=data
        )
        return self._handle_response(response)
    
    # ==================== FOLDERS ====================
    
    def get_folders(self, space_id: str) -> Dict[str, Any]:
        """Get all folders in a space"""
        response = requests.get(
            f"{self.BASE_URL}/space/{space_id}/folder",
            headers=self.headers
        )
        return self._handle_response(response)
    
    # ==================== LISTS ====================
    
    def get_lists(self, folder_id: str) -> Dict[str, Any]:
        """Get all lists in a folder"""
        response = requests.get(
            f"{self.BASE_URL}/folder/{folder_id}/list",
            headers=self.headers
        )
        return self._handle_response(response)
    
    def get_folderless_lists(self, space_id: str) -> Dict[str, Any]:
        """Get lists directly in space (no folder)"""
        response = requests.get(
            f"{self.BASE_URL}/space/{space_id}/list",
            headers=self.headers
        )
        return self._handle_response(response)
    
    # ==================== TASKS ====================
    
    def get_tasks(self, list_id: str, **filters) -> Dict[str, Any]:
        """
        Get tasks from a list
        
        Filters:
            archived, page, order_by, reverse, subtasks, statuses,
            include_closed, assignees, due_date_gt, due_date_lt, etc.
        """
        response = requests.get(
            f"{self.BASE_URL}/list/{list_id}/task",
            headers=self.headers,
            params=filters
        )
        return self._handle_response(response)
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get a specific task by ID"""
        response = requests.get(
            f"{self.BASE_URL}/task/{task_id}",
            headers=self.headers
        )
        return self._handle_response(response)
    
    def create_task(self, list_id: str, name: str, **kwargs) -> Dict[str, Any]:
        """
        Create a new task
        
        Args:
            list_id: List ID to create task in
            name: Task name
            **kwargs: description, assignees, tags, status, priority,
                     due_date, start_date, time_estimate, custom_fields
        
        Example:
            task = clickup.create_task(
                list_id="123",
                name="Analyze AAPL",
                description="Run technical analysis",
                priority=1,  # 1=urgent, 2=high, 3=normal, 4=low
                due_date=1640000000000,  # Unix timestamp (ms)
                assignees=[12345]
            )
        """
        data = {"name": name, **kwargs}
        response = requests.post(
            f"{self.BASE_URL}/list/{list_id}/task",
            headers=self.headers,
            json=data
        )
        return self._handle_response(response)
    
    def update_task(self, task_id: str, **updates) -> Dict[str, Any]:
        """
        Update a task
        
        Updates: name, description, status, priority, due_date,
                assignees, archived, etc.
        """
        response = requests.put(
            f"{self.BASE_URL}/task/{task_id}",
            headers=self.headers,
            json=updates
        )
        return self._handle_response(response)
    
    def delete_task(self, task_id: str) -> Dict[str, Any]:
        """Delete a task"""
        response = requests.delete(
            f"{self.BASE_URL}/task/{task_id}",
            headers=self.headers
        )
        return self._handle_response(response)
    
    # ==================== COMMENTS ====================
    
    def get_comments(self, task_id: str) -> Dict[str, Any]:
        """Get all comments on a task"""
        response = requests.get(
            f"{self.BASE_URL}/task/{task_id}/comment",
            headers=self.headers
        )
        return self._handle_response(response)
    
    def create_comment(self, task_id: str, comment_text: str, 
                      notify_all: bool = False) -> Dict[str, Any]:
        """
        Add comment to task (AI agent can use this to respond!)
        
        Args:
            task_id: Task ID
            comment_text: Comment text
            notify_all: Notify all task watchers
        """
        data = {
            "comment_text": comment_text,
            "notify_all": notify_all
        }
        response = requests.post(
            f"{self.BASE_URL}/task/{task_id}/comment",
            headers=self.headers,
            json=data
        )
        return self._handle_response(response)
    
    # ==================== TIME TRACKING ====================
    
    def start_time_entry(self, task_id: str, description: str = "") -> Dict[str, Any]:
        """Start tracking time on task"""
        data = {"description": description}
        response = requests.post(
            f"{self.BASE_URL}/task/{task_id}/time",
            headers=self.headers,
            json=data
        )
        return self._handle_response(response)
    
    def stop_time_entry(self, team_id: str) -> Dict[str, Any]:
        """Stop current time tracking"""
        response = requests.delete(
            f"{self.BASE_URL}/team/{team_id}/time_entries/current",
            headers=self.headers
        )
        return self._handle_response(response)
    
    # ==================== WEBHOOKS (for 24/7 monitoring) ====================
    
    def create_webhook(self, team_id: str, endpoint: str, 
                      events: List[str]) -> Dict[str, Any]:
        """
        Create webhook for 24/7 task monitoring
        
        Args:
            team_id: Team ID
            endpoint: Your server URL (e.g., https://your-server.com/webhook)
            events: List of events to monitor
                    ["taskCreated", "taskUpdated", "taskDeleted",
                     "taskCommentPosted", etc.]
        
        Example:
            webhook = clickup.create_webhook(
                team_id="123",
                endpoint="https://your-server.com/aria/webhook",
                events=["taskCommentPosted", "taskCreated"]
            )
        """
        data = {
            "endpoint": endpoint,
            "events": events
        }
        response = requests.post(
            f"{self.BASE_URL}/team/{team_id}/webhook",
            headers=self.headers,
            json=data
        )
        return self._handle_response(response)
    
    def get_webhooks(self, team_id: str) -> Dict[str, Any]:
        """Get all webhooks"""
        response = requests.get(
            f"{self.BASE_URL}/team/{team_id}/webhook",
            headers=self.headers
        )
        return self._handle_response(response)
    
    # ==================== AI AGENT HELPERS ====================
    
    def respond_to_task_comment(self, task_id: str, response_text: str) -> Dict[str, Any]:
        """
        ARIA responds to a comment on a task
        
        Usage: When webhook receives "taskCommentPosted", ARIA can auto-respond
        """
        return self.create_comment(task_id, f"🤖 ARIA: {response_text}", notify_all=True)
    
    def create_task_from_message(self, list_id: str, message: str) -> Dict[str, Any]:
        """
        Create task from WhatsApp/chat message
        
        Example:
            User sends: "Create task: Analyze BTC chart"
            ARIA creates task in ClickUp
        """
        return self.create_task(
            list_id=list_id,
            name=message,
            description=f"Created by ARIA from message at {datetime.now()}"
        )
    
    def get_my_tasks(self, team_id: str, assignee_id: int) -> List[Dict]:
        """
        Get all tasks assigned to specific person
        
        Useful for: "ARIA, what are my pending tasks?"
        """
        # Get all spaces
        spaces = self.get_spaces(team_id)
        
        all_tasks = []
        for space in spaces.get("spaces", []):
            # Get folderless lists
            lists = self.get_folderless_lists(space["id"])
            
            for list_item in lists.get("lists", []):
                tasks = self.get_tasks(
                    list_item["id"],
                    assignees=[assignee_id],
                    include_closed=False
                )
                all_tasks.extend(tasks.get("tasks", []))
        
        return all_tasks
    
    # ==================== HELPER METHODS ====================
    
    def _handle_response(self, response) -> Dict[str, Any]:
        """Handle API response"""
        if response.status_code == 200:
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
                    "enum": ["create_task", "get_tasks", "update_task", 
                            "create_comment", "get_my_tasks"],
                    "description": "ClickUp action to perform"
                },
                "list_id": {
                    "type": "string",
                    "description": "List ID (for create_task)"
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID (for update/comment)"
                },
                "name": {
                    "type": "string",
                    "description": "Task name"
                },
                "description": {
                    "type": "string",
                    "description": "Task description"
                },
                "comment_text": {
                    "type": "string",
                    "description": "Comment text"
                }
            }
        }


# ==================== USAGE EXAMPLES ====================

if __name__ == "__main__":
    # Initialize
    API_KEY = "pk_YOUR_API_KEY_HERE"  # Get from clickup.com/settings/apps
    clickup = ClickUpIntegration(API_KEY)
    
    # Example 1: Get workspaces
    print("=" * 60)
    print("Example 1: Get Workspaces")
    workspaces = clickup.get_workspaces()
    if workspaces["success"]:
        for team in workspaces["data"]["teams"]:
            print(f"  - {team['name']} (ID: {team['id']})")
    
    # Example 2: Create task
    print("\n" + "=" * 60)
    print("Example 2: Create Task")
    # task = clickup.create_task(
    #     list_id="YOUR_LIST_ID",
    #     name="Analyze AAPL technical indicators",
    #     description="Check RSI, MACD, and volume",
    #     priority=2
    # )
    # print(f"Task created: {task}")
    
    # Example 3: AI Agent responds to comment
    print("\n" + "=" * 60)
    print("Example 3: ARIA responds to task")
    # response = clickup.respond_to_task_comment(
    #     task_id="TASK_ID",
    #     response_text="Analysis complete! RSI shows oversold conditions."
    # )
    # print(f"Response: {response}")
    
    print("\n" + "=" * 60)
    print("✅ ClickUp integration ready!")
    print("Next: Set up webhook for 24/7 monitoring")
