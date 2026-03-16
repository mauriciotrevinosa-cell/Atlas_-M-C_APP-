from .base import BaseAgent, AgentTask, AgentResult

class ReviewerAgent(BaseAgent):
    name = "reviewer_agent"
    version = "v1"

    def __init__(self, llm_client, prompt_loader, validator):
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader
        self.validator = validator

    def run(self, task: AgentTask) -> AgentResult:
        prompt_template = self.prompt_loader.load("reviewer.md")

        prompt = self._build_prompt(
            template=prompt_template,
            context=task.context,
            code=task.inputs.get("code", ""),
            diff=task.inputs.get("diff", "")
        )

        raw_response = self.llm_client.generate(prompt)
        structured = self.validator.parse_reviewer_response(raw_response)
        validated = self._validate_review(structured)

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

    def _build_prompt(self, template, context, code, diff):
        return template.format(
            CONTEXTO=context,
            CODIGO=code or diff
        )

    def _validate_review(self, structured):
        required_keys = [
            "verdict",
            "critical_findings",
            "important_findings",
            "merge_recommendation",
            "concrete_fixes"
        ]

        for key in required_keys:
            if key not in structured:
                raise ValueError(f"Reviewer output missing key: {key}")

        return structured
