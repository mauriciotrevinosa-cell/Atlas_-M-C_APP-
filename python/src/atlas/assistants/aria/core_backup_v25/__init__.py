"""
ARIA Core Module

Contains the main chat engine, system prompts, and validation logic.

Version: 2.0 - Refined Edition
Updated: 2026-02-03
"""

from .chat import ARIA, create_aria
from .system_prompt import (
    get_system_prompt,
    ARIA_SYSTEM_PROMPT_V2,
    get_tool_guidelines,
    SYSTEM_PROMPT_METADATA
)
from .validation import (
    validate_tool_params,
    ValidationError,
    ParameterValidator,
    ParameterType,
    TOOL_SCHEMAS
)

# Version info
__version__ = "2.0.0"
__author__ = "M&C"
__status__ = "Refined"

# What's exported when someone does: from aria.core import *
__all__ = [
    # Main classes
    'ARIA',
    'create_aria',
    
    # System prompt
    'get_system_prompt',
    'ARIA_SYSTEM_PROMPT_V2',
    'get_tool_guidelines',
    'SYSTEM_PROMPT_METADATA',
    
    # Validation
    'validate_tool_params',
    'ValidationError',
    'ParameterValidator',
    'ParameterType',
    'TOOL_SCHEMAS',
    
    # Metadata
    '__version__',
    '__author__',
    '__status__'
]

# Module-level convenience
def get_version() -> str:
    """Get ARIA version string"""
    return f"ARIA Core v{__version__} ({__status__})"


def print_info():
    """Print module information"""
    print("=" * 60)
    print(f"ARIA Core Module - Version {__version__}")
    print("=" * 60)
    print(f"Status: {__status__}")
    print(f"Author: {__author__}")
    print("\nComponents:")
    print("  • ARIA - Main chat engine with tool calling")
    print("  • System Prompt v2.0 - Professional prompt engineering")
    print("  • Parameter Validation - Robust input validation")
    print("\nImports available:")
    for item in __all__:
        print(f"  - {item}")
    print("=" * 60)


# Auto-check on import (optional, can be removed)
if __name__ != "__main__":
    # Silent import - no print
    pass
else:
    # Direct execution - show info
    print_info()