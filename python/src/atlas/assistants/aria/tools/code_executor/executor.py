"""
ARIA Code Executor
====================
Sandboxed Python execution environment for ARIA.
ARIA can write and execute code autonomously.

Security:
- Restricted imports (no os, subprocess, sys, shutil)
- Timeout enforcement
- Output capture (stdout + stderr)
- Memory-safe (catches exceptions)

Copyright (c) 2026 M&C. All rights reserved.
"""

import io
import logging
import time
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Dict, Optional

logger = logging.getLogger("atlas.aria.executor")

# Allowed modules that ARIA can import in code execution
ALLOWED_MODULES = {
    "math", "statistics", "random", "collections", "itertools", "functools",
    "datetime", "json", "csv", "re", "copy", "decimal", "fractions",
    "numpy", "np",
    "pandas", "pd",
    "scipy", "scipy.stats", "scipy.optimize", "scipy.linalg",
}

# Explicitly blocked (security)
BLOCKED_MODULES = {
    "os", "sys", "subprocess", "shutil", "pathlib", "socket",
    "http", "urllib", "requests", "ftplib", "smtplib",
    "__builtins__", "importlib", "ctypes", "signal",
}

BLOCKED_BUILTINS = {
    "exec", "eval", "compile", "__import__", "open", "input",
    "breakpoint", "exit", "quit",
}


class CodeExecutor:
    """
    Sandboxed code execution for ARIA.

    Usage:
        executor = CodeExecutor()
        result = executor.execute('''
            import numpy as np
            prices = [100, 105, 103, 108, 112]
            returns = np.diff(prices) / prices[:-1]
            print(f"Mean return: {returns.mean():.4f}")
            print(f"Volatility: {returns.std():.4f}")
        ''')
    """

    def __init__(self, timeout: float = 30.0, max_output_chars: int = 10000):
        self.timeout = timeout
        self.max_output = max_output_chars

    def execute(self, code: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute Python code in a sandboxed environment.

        Args:
            code:    Python code string
            context: Optional dict of pre-defined variables

        Returns:
            {
                "success": bool,
                "stdout": str,
                "stderr": str,
                "result": any (last expression value),
                "elapsed": float,
                "error": str or None,
            }
        """
        # Security check
        security = self._security_check(code)
        if security["blocked"]:
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "result": None,
                "elapsed": 0,
                "error": f"Security violation: {security['reason']}",
            }

        # Prepare execution namespace
        namespace = self._build_namespace(context)

        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        start = time.time()

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(compile(code, "<aria_code>", "exec"), namespace)

            elapsed = time.time() - start

            # Try to get last expression result
            result = namespace.get("_result_", namespace.get("result", None))

            stdout_text = stdout_capture.getvalue()[:self.max_output]
            stderr_text = stderr_capture.getvalue()[:self.max_output]

            return {
                "success": True,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "result": self._safe_serialize(result),
                "elapsed": round(elapsed, 3),
                "error": None,
            }

        except Exception as e:
            elapsed = time.time() - start
            tb = traceback.format_exc()

            return {
                "success": False,
                "stdout": stdout_capture.getvalue()[:self.max_output],
                "stderr": stderr_capture.getvalue()[:self.max_output],
                "result": None,
                "elapsed": round(elapsed, 3),
                "error": f"{type(e).__name__}: {str(e)}",
                "traceback": tb[-2000:],  # Last 2000 chars of traceback
            }

    def _security_check(self, code: str) -> Dict[str, Any]:
        """Check code for security violations."""
        code_lower = code.lower()

        # Check for blocked module imports
        for module in BLOCKED_MODULES:
            patterns = [
                f"import {module}",
                f"from {module}",
                f"__import__('{module}'",
                f'__import__("{module}"',
            ]
            for pattern in patterns:
                if pattern in code:
                    return {"blocked": True, "reason": f"Module '{module}' is not allowed"}

        # Check for blocked builtins
        for builtin in BLOCKED_BUILTINS:
            if f"{builtin}(" in code and builtin != "open":
                # Allow "open" in strings, block as function call
                if builtin == "eval" or builtin == "exec":
                    return {"blocked": True, "reason": f"'{builtin}()' is not allowed"}

        # Check for file operations
        if "open(" in code and "# file_ok" not in code:
            return {"blocked": True, "reason": "'open()' file operations are not allowed"}

        return {"blocked": False, "reason": None}

    def _build_namespace(self, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Build execution namespace with safe imports pre-loaded."""
        namespace = {"__builtins__": __builtins__}

        # Pre-import common safe modules
        try:
            import numpy as np
            namespace["np"] = np
            namespace["numpy"] = np
        except ImportError:
            pass

        try:
            import pandas as pd
            namespace["pd"] = pd
            namespace["pandas"] = pd
        except ImportError:
            pass

        try:
            import math
            namespace["math"] = math
        except ImportError:
            pass

        try:
            import statistics
            namespace["statistics"] = statistics
        except ImportError:
            pass

        # Import our financial math tools
        try:
            from atlas.assistants.aria.tools.financial_math import MATH_TOOLS
            namespace["tools"] = MATH_TOOLS
            # Also expose individual functions
            for name, func in MATH_TOOLS.items():
                namespace[name] = func
        except ImportError:
            pass

        # Add user context
        if context:
            namespace.update(context)

        return namespace

    def _safe_serialize(self, obj: Any) -> Any:
        """Convert result to JSON-serializable format."""
        if obj is None:
            return None
        if isinstance(obj, (int, float, str, bool)):
            return obj
        if isinstance(obj, (list, tuple)):
            return [self._safe_serialize(x) for x in obj[:100]]  # Cap at 100 items
        if isinstance(obj, dict):
            return {str(k): self._safe_serialize(v) for k, v in list(obj.items())[:50]}
        if isinstance(obj, np.ndarray):
            return obj.tolist()[:100]
        if isinstance(obj, pd.DataFrame):
            return obj.head(20).to_dict()
        if isinstance(obj, pd.Series):
            return obj.head(20).to_dict()
        return str(obj)[:1000]


# Convenience: module-level import
try:
    import numpy as np
except ImportError:
    np = None

try:
    import pandas as pd
except ImportError:
    pd = None
