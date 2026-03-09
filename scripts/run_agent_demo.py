import sys
import os

# Ensure the root of the project is in the path to allow imports like 'core...'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.ai_assistant.agent_registry import AgentRegistry
from core.ai_assistant.orchestrator import AgentOrchestrator
from core.ai_assistant.agents.planner_agent import PlannerAgent
from core.ai_assistant.agents.base import AgentTask
from core.ai_assistant.result_validator import ResultValidator
from core.ai_assistant.audit.agent_runs import AuditLogger
from services.llm.providers.ollama_provider import OllamaProvider

class DummyPromptLoader:
    def load(self, prompt_name: str) -> str:
        # Load the prompt string from the actual core file
        path = os.path.join("core", "ai_assistant", "prompts", prompt_name)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

def run_demo():
    print("Initializing Atlas Agent Ecosystem Demo (Sprint 4)")
    print("-" * 50)
    
    # 1. Initialize infra
    registry = AgentRegistry()
    logger = AuditLogger()
    validator = ResultValidator()
    prompt_loader = DummyPromptLoader()
    
    # 2. Initialize real LLM provider (Ollama with qwen2.5)
    # Ensure Ollama is running (`ollama serve` and `ollama run qwen2.5`)
    try:
        print("Connecting to Ollama (model: qwen2.5)...")
        llm_provider = OllamaProvider(model="qwen2.5")
    except Exception as e:
        print(f"Error setting up Ollama: {e}")
        return

    # 3. Create and register the Planner Agent
    print("Registering Planner Agent...")
    planner = PlannerAgent(llm_client=llm_provider, prompt_loader=prompt_loader, validator=validator)
    registry.register(planner)

    # 4. Orchestrator
    orchestrator = AgentOrchestrator(registry=registry, audit_logger=logger)

    # 5. Define a real task mimicking Atlas capabilities
    task = AgentTask(
        task_id="demo_sprint_4",
        agent_name="planner_agent",
        objective="Create a modular UI component for displaying the Portfolio Volatility 3D chart.",
        context={
            "project": "Atlas",
            "module": "finance_dashboard",
            "constraints": [
                "Use vanilla HTML/JS and Three.js.",
                "Maintain separation of concerns (backend data, frontend rendering)."
            ]
        },
        inputs={}
    )

    print("\nExecuting Task:")
    print(f"Objective: {task.objective}")
    print("Agent is thinking (this might take a few seconds)...")
    
    try:
        result = orchestrator.execute(task)
        
        print("\n" + "=" * 50)
        print(f"Status: {result.status}")
        print(f"Summary:\n{result.summary}")
        print("-" * 50)
        print("Structured JSON Result parsed by ResultValidator:")
        import json
        print(json.dumps(result.result, indent=2))
        print("=" * 50)
        
    except ConnectionError as e:
        print(f"\n[Error] Connection Failed. Ensure Ollama is running and accessible.")
        print(f"Detail: {e}")
    except ValueError as e:
        print(f"\n[Error] Validation Failed. The LLM might not have returned the exact JSON schema required.")
        print(f"Detail: {e}")
    except Exception as e:
        import traceback
        print(f"\n[Error] Unexpected exception:")
        traceback.print_exc()

if __name__ == "__main__":
    run_demo()
