from .base import BaseAgent, AgentTask, AgentResult

class RepoScoutAgent(BaseAgent):
    name = "repo_scout_agent"
    version = "v1"

    def __init__(self, llm_client, prompt_loader, validator):
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader
        self.validator = validator

    def run(self, task: AgentTask) -> AgentResult:
        # Default implementation for repo scout
        prompt_template = self.prompt_loader.load("repo_scout.md")

        prompt = self._build_prompt(
            template=prompt_template,
            objective=task.objective,
            context=task.context
        )

        raw_response = self.llm_client.generate(prompt)
        # Note: in a fully developed orchestrator, there would be a parse_repo_scout_response in validator
        structured = self.validator._parse_json(raw_response)
        validated = self._validate_scout(structured)

        return AgentResult(
            task_id=task.task_id,
            status="success",
            summary=validated.get("summary", "Repo evaluation completed"),
            result=validated,
            errors=[],
            metadata={
                "agent": self.name,
                "version": self.version
            }
        )

    def _build_prompt(self, template, objective, context):
        return template.format(
            OBJETIVO=objective,
            CONTEXTO=context
        )

    def _validate_scout(self, structured):
        required_keys = [
            "solution_categories",
            "repeated_patterns",
            "copy_conceptually",
            "avoid_copying",
            "adoption_risks",
            "proposal_for_atlas",
            "references"
        ]

        for key in required_keys:
            if key not in structured:
                raise ValueError(f"Repo scout output missing key: {key}")

        return structured
