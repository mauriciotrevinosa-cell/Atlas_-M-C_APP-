class AgentOrchestrator:
    def __init__(self, registry, audit_logger):
        self.registry = registry
        self.audit_logger = audit_logger

    def execute(self, task):
        agent = self.registry.get(task.agent_name)

        self.audit_logger.log_start(task.task_id, task.agent_name, task.objective)

        result = agent.run(task)

        self.audit_logger.log_end(
            task_id=task.task_id,
            status=result.status,
            summary=result.summary
        )

        return result
