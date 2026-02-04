"""
API Key Configuration for ARIA

This file acts as a central place to manage your API keys.
For security, it is recommended to use Environment Variables, but you can also set them here locally.

HOW TO GET KEYS:
See Project_Governance/NEEDED_KEYS.md for full instructions.
"""

import os

# Voice Services
# ----------------
# Required only for "Advanced" voice mode. 
# "Basic" mode uses free Google services (no key required).
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Integrations
# ----------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")

# Search
# ----------------
# DuckDuckGo is free and requires no key.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

def get_key(service_name: str) -> str:
    """Get API key for service"""
    keys = {
        "elevenlabs": ELEVENLABS_API_KEY,
        "openai": OPENAI_API_KEY,
        "telegram": TELEGRAM_BOT_TOKEN,
        "discord": DISCORD_BOT_TOKEN,
        "notion": NOTION_API_KEY
    }
    return keys.get(service_name.lower(), "")
