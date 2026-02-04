"""
ARIA (Atlas Reasoning & Intelligence Assistant)

AI-powered assistant for Atlas quantitative trading system

Version: 3.0.0 - Complete Edition (100%)
"""

from .core import (
    ARIA,
    create_aria,
    get_system_prompt,
    validate_tool_params,
    ValidationError,
    get_version
)

# Core Components
from .core import ARIA, create_aria

# Version
__version__ = "3.0.0"
__author__ = "M&C"

__all__ = [
    'ARIA',
    'create_aria',
    'get_system_prompt',
    'validate_tool_params',
    'ValidationError',
    'get_version',
    '__version__'
]


def quick_start():
    """
    Quick start guide for ARIA
    """
    print("=" * 60)
    print(f"ARIA v{__version__} - Complete Edition")
    print("=" * 60)
    print("\n1. Create ARIA instance:")
    print("   from atlas.assistants.aria import create_aria")
    print("   aria = create_aria()")
    print("\n2. Ask questions (with Memory & Tools):")
    print("   response = aria.ask('Research AI stocks and save a report')")
    print("\n3. Voice Mode (New):")
    print("   from atlas.assistants.aria.voice.basic import start_voice_chat")
    print("   start_voice_chat()")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    quick_start()
