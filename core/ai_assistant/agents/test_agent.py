from .base import BaseAgent, AgentTask, AgentResult

class TestAgent(BaseAgent):
    name = "test_agent"
    version = "v1"

    def __init__(self, llm_client, prompt_loader, validator):
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader
        self.validator = validator

    def run(self, task: AgentTask) -> AgentResult:
        prompt_template = self.prompt_loader.load("test_agent.md")

        prompt = self._build_prompt(
            template=prompt_template,
            objective=task.objective,
            context=task.context,
            implementation_details=task.inputs.get("implementation", "")
        )

        raw_response = self.llm_client.generate(prompt)
        structured = self.validator.parse_test_agent_response(raw_response)
        validated = self._validate_tests(structured)

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

    def _build_prompt(self, template, objective, context, implementation_details):
        return template.format(
            OBJETIVO=objective,
            CONTEXTO=context,
            IMPLEMENTACION=implementation_details
        )

    def _validate_tests(self, structured):
        required_keys = [
            "functional_risks",
            "nominal_cases",
            "edge_cases",
            "error_cases",
            "fixtures_needed",
            "pytest_starter_code",
            "missing_coverage"
        ]

        for key in required_keys:
            if key not in structured:
                raise ValueError(f"Test agent output missing key: {key}")

        return structured
