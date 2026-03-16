from .base import BaseAgent, AgentTask, AgentResult

class PlannerAgent(BaseAgent):
    name = "planner_agent"
    version = "v1"

    def __init__(self, llm_client, prompt_loader, validator):
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader
        self.validator = validator

    def run(self, task: AgentTask) -> AgentResult:
        prompt_template = self.prompt_loader.load("planner.md")

        prompt = self._build_prompt(
            template=prompt_template,
            objective=task.objective,
            context=task.context,
            constraints=task.context.get("constraints", [])
        )

        raw_response = self.llm_client.generate(prompt)

        structured = self.validator.parse_planner_response(raw_response)

        validated = self._validate_plan(structured)

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

    def _build_prompt(self, template, objective, context, constraints):
        return template.format(
            OBJETIVO=objective,
            CONTEXTO=context,
            RESTRICCIONES=constraints
        )

    def _validate_plan(self, structured):
        required_keys = [
            "expected_result",
            "steps",
            "files_to_touch",
            "tests_required",
            "validation_criteria"
        ]

        for key in required_keys:
            if key not in structured:
                raise ValueError(f"Planner output missing key: {key}")

        if not structured["steps"]:
            raise ValueError("Planner output has empty steps")

        return structured
