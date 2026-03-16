import json

class ResultValidator:
    def parse_planner_response(self, raw_response: str) -> dict:
        return self._parse_json(raw_response)
        
    def parse_reviewer_response(self, raw_response: str) -> dict:
        return self._parse_json(raw_response)

    def parse_test_agent_response(self, raw_response: str) -> dict:
        return self._parse_json(raw_response)

    def parse_context_curator_response(self, raw_response: str) -> dict:
        return self._parse_json(raw_response)

    def _parse_json(self, response: str) -> dict:
        # Simple extraction for robust JSON parsing
        try:
            start_index = response.find("{")
            end_index = response.rfind("}")
            if start_index == -1 or end_index == -1:
                return {}
            json_str = response[start_index:end_index+1]
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {}
