class AgentRegistry:
    def __init__(self):
        self._agents = {}

    def register(self, agent):
        self._agents[agent.name] = agent

    def get(self, agent_name: str):
        if agent_name not in self._agents:
            raise KeyError(f"Agent not found: {agent_name}")
        return self._agents[agent_name]

    def list_agents(self):
        return list(self._agents.keys())
