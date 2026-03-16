from .base import BaseAgent, AgentTask, AgentResult

class ContextCuratorAgent(BaseAgent):
    name = "context_curator_agent"
    version = "v1"

    def __init__(self, llm_client, prompt_loader, validator):
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader
        self.validator = validator

    def run(self, task: AgentTask) -> AgentResult:
        prompt_template = self.prompt_loader.load("context_curator.md")

        prompt = self._build_prompt(
            template=prompt_template,
            objective=task.objective,
            raw_context=task.inputs.get("raw_context", "")
        )

        raw_response = self.llm_client.generate(prompt)
        structured = self.validator.parse_context_curator_response(raw_response)
        validated = self._validate_curation(structured)

        return AgentResult(
            task_id=task.task_id,
            status="success",
            summary=validated["summary"],
            result=validated,
            errors=[],
            metadata={
                "agent": self.name,
                "version": self.version
            }
        )

    def _build_prompt(self, template, objective, raw_context):
        return template.format(
            OBJETIVO=objective,
            CONTEXTO_RAW=raw_context
        )

    def _validate_curation(self, structured):
        required_keys = [
            "required_context",
            "optional_context",
            "irrelevant_context",
            "compact_prompt_context",
            "context_risks"
        ]

        for key in required_keys:
            if key not in structured:
                raise ValueError(f"Context curator output missing key: {key}")

        return structured
