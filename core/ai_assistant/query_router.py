import json

class QueryRouter:
    """
    The main facing router that takes raw user text and
    determines which workflow (agent) should be triggered.
    """
    
    def __init__(self, llm_provider):
        self.llm = llm_provider
        self.system_prompt = (
            "You are ARIA's core intent router for the Atlas ecosystem.\n"
            "Given a user query, pick ONE of the following agents to handle it:\n"
            "- 'planner_agent': If the user asks for a feature implementation, blueprint, or design.\n"
            "- 'reviewer_agent': If the user asks to review code or check for bugs.\n"
            "- 'test_agent': If the user asks to create or improve unit tests.\n"
            "- 'repo_scout_agent': If the user asks to find patterns or search the internet/repo.\n"
            "Respond ONLY with a valid JSON in this format: {\"route\": \"<agent_name>\"}"
        )

    def route(self, user_query: str) -> str:
        """
        Takes raw string from User and returns agent name.
        """
        combined_prompt = f"{self.system_prompt}\n\nUser Query:\n{user_query}"
        
        try:
            # Tell the LLM provider we want JSON output
            raw_response = self.llm.generate(combined_prompt, format="json", temperature=0.1)
            
            # Extract JSON block
            start_index = raw_response.find("{")
            end_index = raw_response.rfind("}")
            
            if start_index == -1 or end_index == -1:
                return "planner_agent" # default fallback
                
            json_str = raw_response[start_index:end_index+1]
            data = json.loads(json_str)
            
            return data.get("route", "planner_agent")
            
        except Exception as e:
            # Fallback for Phase 1 safely
            return "planner_agent"
