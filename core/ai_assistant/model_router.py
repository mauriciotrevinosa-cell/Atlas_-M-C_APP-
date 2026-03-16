class ModelRouter:
    def route(self, agent_name: str, risk_level: str = "low") -> str:
        if agent_name == "planner_agent":
            return "ollama:qwen2.5" if risk_level == "low" else "gpt"

        if agent_name == "reviewer_agent":
            return "gpt"

        if agent_name == "test_agent":
            return "claude"

        if agent_name == "repo_scout_agent":
            return "gemini"

        return "ollama:llama3.1"
