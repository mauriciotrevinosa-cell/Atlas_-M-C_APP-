from .base import BaseAgent, AgentTask, AgentResult

class IngestionAgent(BaseAgent):
    name = "ingestion_agent"
    version = "v1"

    def __init__(self, llm_client, prompt_loader, validator):
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader
        self.validator = validator

    def run(self, task: AgentTask) -> AgentResult:
        prompt_template = self.prompt_loader.load("ingestion.md")

        prompt = self._build_prompt(
            template=prompt_template,
            objective=task.objective,
            raw_data=task.inputs.get("raw_data", "")
        )

        raw_response = self.llm_client.generate(prompt)
        structured = self.validator._parse_json(raw_response)
        validated = self._validate_ingestion(structured)

        return AgentResult(
            task_id=task.task_id,
            status="success",
            summary=validated.get("summary", "Document ingestion completed"),
            result=validated,
            errors=[],
            metadata={
                "agent": self.name,
                "version": self.version
            }
        )

    def _build_prompt(self, template, objective, raw_data):
        return template.format(
            OBJETIVO=objective,
            DATOS_RAW=raw_data
        )

    def _validate_ingestion(self, structured):
        required_keys = [
            "executive_summary",
            "key_concepts",
            "entities",
            "relations",
            "actionable_data",
            "ambiguities",
            "knowledge_pack"
        ]

        for key in required_keys:
            if key not in structured:
                raise ValueError(f"Ingestion agent output missing key: {key}")

        return structured
