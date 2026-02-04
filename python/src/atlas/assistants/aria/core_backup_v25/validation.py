"""
Compatibility shim for legacy imports.

Allows `from aria.core.validation import ...` to keep working after the
module was renamed to `aria_validation.py`.
"""

from .aria_validation import (  # noqa: F401
    validate_tool_params,
    ValidationError,
    ParameterValidator,
    ParameterType,
    TOOL_SCHEMAS,
)

__all__ = [
    "validate_tool_params",
    "ValidationError",
    "ParameterValidator",
    "ParameterType",
    "TOOL_SCHEMAS",
]
