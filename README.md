# 🤖 ARIA - Atlas Reasoning & Intelligence Assistant

**Version:** 5.0.0  
**Status:** In Development  
**License:** Proprietary (M&C)

---

## 🎯 What is ARIA?

ARIA is the most advanced AI assistant for quantitative finance and trading. Built with recursive memory, multi-agent architecture, and voice capabilities.

## ✨ Features

### Core Capabilities
- 💬 **Advanced Chat** - Powered by Claude Sonnet 4
- 🎤 **Voice Assistant** - Basic (FREE) & Advanced (Premium)
- 🧠 **Recursive Memory** - Infinite context via vector DB
- 🤖 **Multi-Agent System** - Specialized agents working together

### Intelligence
- 🔮 **Proactive Suggestions** - Anticipates your needs
- 📚 **Learning from You** - Adapts to your style
- 😊 **Emotional Intelligence** - Understands context and tone
- 📝 **Conversation Summarizer** - Meeting notes & key points

### Tools
- 🌐 **Web Search** - Real-time information
- 🎨 **Image Generation** - DALL-E & Gemini
- 💻 **Code Interpreter** - Execute Python code
- 📊 **Backtesting** - Automated strategy testing
- 📈 **Portfolio Tracking** - Monitor your positions

### Integrations
- 💬 **Telegram/Discord** - Use ARIA anywhere
- 📓 **Jupyter** - Generate analysis notebooks
- 📄 **Document Analysis** - Read PDFs/earnings reports
- 🔔 **Sentiment Analysis** - News & social media

---

## 🚀 Quick Start
```python
from aria import ARIA

# Create ARIA instance
aria = ARIA()

# Chat
response = aria.ask("What's the latest news on AAPL?")
print(response)

# Voice mode
aria.voice_mode()  # Start speaking with ARIA

# With memory
aria = ARIA(recursive=True)
aria.ask("Remember: I prefer tech stocks")
# ... days later ...
aria.ask("Recommend me something")
# ARIA remembers your preference
```

---

## 📦 Installation
```bash
pip install aria-assistant
```

**Requirements:**
- Python 3.10+
- Anthropic API key
- (Optional) OpenAI API key for advanced features
- (Optional) ElevenLabs API key for premium voice

---

## 🔑 API Keys

Create `.env` file:
```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...      # Optional
ELEVENLABS_API_KEY=...          # Optional
```

---

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API_REFERENCE.md)
- [System Prompt](docs/SYSTEM_PROMPT.md)
- [Tool Development](docs/TOOL_DEVELOPMENT.md)

---

## 🎓 Examples

See [examples/](examples/) directory for:
- Basic chat
- Voice assistant
- Code interpreter
- Multi-agent system
- Integration with trading systems

---

## 🏗️ Architecture
```
ARIA v5.0
├─ Core (Chat + Multi-Agent)
├─ Tools (Web, Code, Images)
├─ Voice (Basic + Advanced)
├─ Memory (Recursive + Vector DB)
├─ Intelligence (Learning + Emotional)
└─ Integrations (Telegram, Discord, etc.)
```

---

## 🤝 Integration with Atlas

ARIA is designed to work seamlessly with Atlas trading system:
```python
from atlas.lab.aria_integration import create_atlas_aria

aria = create_atlas_aria()
aria.ask("Analyze AAPL and suggest entry point")
# ARIA uses Atlas data layer and backtesting engine
```

---

## 📝 License

Copyright (c) 2026 M&C. All rights reserved.

This is proprietary software. Unauthorized copying, distribution, or modification is prohibited.

---

## 🔥 What Makes ARIA Special?

1. **Recursive Memory** - Never forgets important information
2. **Multi-Agent** - Team of specialized agents
3. **Proactive** - Suggests before you ask
4. **Multi-Modal** - Text, voice, images, code
5. **Self-Improving** - Learns from every interaction

---

**Built with ❤️ by M&C**