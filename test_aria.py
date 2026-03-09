import sys
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\mauri\OneDrive\Desktop\Atlas")
sys.path.insert(0, str(PROJECT_ROOT / "python" / "src"))

print("=== Testing ARIA imports ===")
try:
    from atlas.assistants.aria import create_aria
    print("[PASS] create_aria imported")
except Exception as e:
    print(f"[FAIL] create_aria: {e}")

try:
    from atlas.assistants.aria.tools import register_phase1_tools
    print("[PASS] register_phase1_tools imported")
except Exception as e:
    print(f"[FAIL] register_phase1_tools: {e}")

try:
    from atlas.assistants.aria.tools.setup import register_all_tools
    print("[PASS] register_all_tools imported")
except Exception as e:
    print(f"[FAIL] register_all_tools: {e}")

print()
print("=== Creating ARIA instance ===")
try:
    aria = create_aria()
    print(f"[PASS] ARIA created: {type(aria).__name__}")
    print(f"       model: {getattr(aria, 'model', 'unknown')}")
    print(f"       history len: {len(getattr(aria, 'history', []))}")
except Exception as e:
    print(f"[FAIL] create_aria(): {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

print()
print("=== Registering Phase 1 tools ===")
try:
    registered = register_phase1_tools(aria)
    print(f"[PASS] Phase 1 tools: {', '.join(registered)}")
except Exception as e:
    print(f"[FAIL] register_phase1_tools: {e}")
    import traceback; traceback.print_exc()

print()
print("=== Registering all tools (setup.py) ===")
try:
    recovered = register_all_tools(aria)
    print(f"[PASS] Recovered/additional tools: {recovered}")
except Exception as e:
    print(f"[FAIL] register_all_tools: {e}")
    import traceback; traceback.print_exc()

print()
print("=== Testing a simple ARIA query ===")
try:
    # Test without Ollama - just check if ask() is defined
    print(f"[PASS] aria.ask method exists: {callable(getattr(aria, 'ask', None))}")
    # Check tools registered
    tools = getattr(aria, '_tools', getattr(aria, 'tools', {}))
    if tools:
        print(f"[PASS] Tools registered: {list(tools.keys()) if isinstance(tools, dict) else len(tools)}")
    else:
        print("[INFO] No tools dict found directly on aria object")
except Exception as e:
    print(f"[FAIL] {e}")

print()
print("=== DONE ===")
