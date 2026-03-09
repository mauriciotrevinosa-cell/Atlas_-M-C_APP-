"""
Test configuration for Atlas Python package.
Adds python/src to sys.path so 'atlas' is importable.
"""
import sys
from pathlib import Path

# Ensure atlas package is importable
_SRC = Path(__file__).parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
