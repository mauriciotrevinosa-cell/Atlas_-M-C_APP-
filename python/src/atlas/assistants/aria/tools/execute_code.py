"""
ARIA Execute Code Tool

WARNING: this runs code with exec() inside the Atlas server process with full
builtins — it is NOT a sandbox. Only register it in trusted, local-only
setups (see ATLAS_ENABLE_CODE_EXEC in run_atlas.py).
"""
import sys
import io
from typing import Dict, Any

class ExecuteCodeTool:
    name = "execute_code"
    description = "Execute Python code in the Atlas server process (not sandboxed)"
    
    def execute(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        try:
            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()
            
            exec(code, {"__builtins__": __builtins__})
            
            output = buffer.getvalue()
            sys.stdout = old_stdout
            
            return {"success": True, "output": output}
        except Exception as e:
            sys.stdout = old_stdout
            return {"success": False, "error": str(e)}
    
    def get_parameters_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"}
            },
            "required": ["code"]
        }
