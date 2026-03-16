import logging

class AuditLogger:
    def __init__(self, log_config=None):
        self.logger = logging.getLogger("AtlasAgents")
        # In a real system, you might configure specific file handlers or remote logging here
        
    def log_start(self, task_id: str, agent_name: str, objective: str):
        self.logger.info(f"START Task {task_id} | Agent: {agent_name} | Objective: {objective}")

    def log_end(self, task_id: str, status: str, summary: str):
        self.logger.info(f"END Task {task_id} | Status: {status} | Summary: {summary}")
