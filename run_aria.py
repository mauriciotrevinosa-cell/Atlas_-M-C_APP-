from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "python" / "src"))

from atlas.assistants.aria import create_aria
from atlas.assistants.aria.tools import register_phase1_tools
from atlas.assistants.aria.tools.setup import register_all_tools


def main() -> None:
    try:
        aria = create_aria()
        registered = register_phase1_tools(aria)
        recovered_count = register_all_tools(aria)

        print("\nARIA ready. Type 'quit' to exit.")
        if recovered_count:
            print(f"Registered tools: {', '.join(registered)} (+{recovered_count} recovered)")
        else:
            print(f"Registered tools: {', '.join(registered)}")
        print("-" * 50)

        while True:
            user_input = input("\nYou: ")
            if user_input.lower().strip() in {"quit", "exit"}:
                break

            print("ARIA: thinking...", end="\r")
            response = aria.ask(user_input)
            print(f"ARIA: {response}")

    except Exception as exc:
        print(f"Error: {exc}")
        print("Tip: make sure Ollama is running.")


if __name__ == "__main__":
    main()
