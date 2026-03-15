"""
Atlas Signal Terminal
=====================
Modular market signal ingestion, classification, matching, and alerting.

Architecture:
  collectors  →  pipeline  →  storage  →  services  →  api

Quick start:
    from atlas.signal_terminal import SignalTerminal
    terminal = SignalTerminal()
    await terminal.start()
"""

from .scheduler import SignalScheduler as SignalTerminal

__all__ = ["SignalTerminal"]
__version__ = "1.0.0"
