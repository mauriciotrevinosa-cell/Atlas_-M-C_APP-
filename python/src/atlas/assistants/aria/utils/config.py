"""
Configuration management for ARIA - AUTONOMOUS EDITION

Copyright (c) 2026 M&C. All rights reserved.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Config:
    """ARIA configuration - Autonomous Edition"""
    
    # LLM Backend
    LLM_BACKEND = os.getenv("ARIA_LLM_BACKEND", "ollama")  # ollama, anthropic, openai
    
    # Ollama settings (LOCAL)
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
    
    # Optional cloud APIs (only if user wants)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", None)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
    
    # Model settings
    MAX_TOKENS = int(os.getenv("ARIA_MAX_TOKENS", "4096"))
    TEMPERATURE = float(os.getenv("ARIA_TEMPERATURE", "0.7"))
    
    # Voice settings
    VOICE_MODE = os.getenv("ARIA_VOICE_MODE", "basic")
    
    # Memory settings
    MEMORY_TYPE = os.getenv("ARIA_MEMORY_TYPE", "local")
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    CACHE_DIR = DATA_DIR / "cache"
    MEMORY_DIR = DATA_DIR / "memory"
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if cls.LLM_BACKEND == "ollama":
            # No API key needed for Ollama!
            print("✅ Using Ollama (local, no API key needed)")
            return True
        
        elif cls.LLM_BACKEND == "anthropic":
            if not cls.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not found for Anthropic backend")
        
        elif cls.LLM_BACKEND == "openai":
            if not cls.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not found for OpenAI backend")
        
        return True
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories"""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.CACHE_DIR.mkdir(exist_ok=True)
        cls.MEMORY_DIR.mkdir(exist_ok=True)


# Validate on import
Config.validate()
Config.ensure_directories()