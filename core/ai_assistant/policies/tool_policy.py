class ToolPolicy:
    """
    Controls which agents have access to which tools.
    In Phase 1, we aggressively lock down dangerous tools.
    """
    
    # Map agent name to a list of allowed tool names
    _rules = {
        "planner_agent": ["read_file", "list_dir", "summarize_context"],
        "reviewer_agent": ["read_file", "code_diff"],
        "test_agent": ["read_file"],
        "repo_scout_agent": ["search_repo", "list_dir"],
        "context_curator_agent": ["read_file"],
        "ingestion_agent": ["read_file"]
    }

    def can_access(self, agent_name: str, tool_name: str) -> bool:
        """
        Checks if an agent is permitted to use a specific tool.
        """
        allowed = self._rules.get(agent_name, [])
        return tool_name in allowed

    def get_allowed_tools(self, agent_name: str) -> list[str]:
        return self._rules.get(agent_name, [])
