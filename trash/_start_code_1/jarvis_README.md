# Jarvis - AI Assistant Lab 🤖

---

## 🎯 Purpose

**Jarvis** is an experimental AI assistant for Project Atlas that helps humans 
understand and navigate the system's intelligence.

### What Jarvis Does:
- ✅ **Explains signals** in natural language
- ✅ **Compares backtest runs** (which performed better and why)
- ✅ **Answers questions** about system state
- ✅ **Guides exploration** of Brain Viewer artifacts
- ✅ **Summarizes risks** in plain English

### What Jarvis Does NOT Do:
- ❌ **Execute trades** (read-only by default)
- ❌ **Alter core logic** (cannot modify engines)
- ❌ **Make autonomous decisions** (always advisory)

---

## 🧪 Experimental Status

This is **lab code** - it can:
- Change rapidly
- Break without warning
- Be deleted and rewritten
- Fail gracefully

**When validated**, components will be promoted to `atlas/assistants/`.

---

## 🏗️ Structure

```
jarvis/
├─ README.md              # This file
├─ __init__.py            # Module initialization
└─ experiments/           # Your experimental code
   ├─ 001_basic_explain.py
   ├─ 002_rag_integration.py
   └─ 003_multimodal.py
```

---

## 💡 Example Use Cases

### 1. Explain a Signal
```python
from atlas.lab.jarvis.experiments.explain import explain_signal

signal = {
    "type": "LONG",
    "confidence": 0.78,
    "reasons": ["RSI oversold", "MACD crossover", "Memory hit rate 82%"]
}

explanation = explain_signal(signal)
print(explanation)
# Output:
# "Atlas recommends LONG with 78% confidence because:
#  1. RSI(14) = 28 indicates oversold conditions
#  2. MACD crossed above signal line (bullish)
#  3. Historical memory shows 82% accuracy in similar setups"
```

### 2. Compare Two Backtest Runs
```python
from atlas.lab.jarvis.experiments.compare import compare_runs

comparison = compare_runs(
    run_id_1="abc123_momentum",
    run_id_2="def456_meanrevert"
)

print(comparison)
# Output:
# "Momentum strategy (abc123) outperformed with Sharpe 1.8 vs 1.2,
#  but had 15% larger max drawdown. Mean reversion was more stable
#  during volatile periods..."
```

### 3. Ask Natural Language Questions
```python
from atlas.lab.jarvis.experiments.query import ask

response = ask("Why did Atlas recommend HOLD instead of LONG?")
print(response)
# Output:
# "Atlas detected a discrepancy: signal engine produced bullish
#  probabilities (LONG 72%), but risk engine identified correlation
#  fragility in the portfolio. Orchestrator downgraded to HOLD."
```

---

## 🔧 Technical Approaches

### Option A: Direct LLM API
```python
# Call Anthropic Claude, OpenAI GPT-4, etc.
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
response = client.messages.create(...)
```

### Option B: RAG (Retrieval-Augmented Generation)
```python
# Load Atlas documentation into vector DB
# Query relevant docs before answering
from chromadb import Client

db = Client()
docs = db.query("How does discrepancy analysis work?")
# Feed docs to LLM for grounded answers
```

### Option C: Function Calling
```python
# LLM decides which Atlas function to call
tools = [
    {
        "name": "get_signal_history",
        "description": "Retrieve past signals for a ticker",
        "parameters": {...}
    }
]
# LLM can inspect actual data, not just guess
```

---

## 🛠️ Dependencies (Optional)

Install only if experimenting with Jarvis:

```bash
# Anthropic Claude
pip install anthropic

# OpenAI GPT-4
pip install openai

# Vector database for RAG
pip install chromadb

# Local models (if you prefer)
pip install llama-cpp-python
```

**Note:** These are NOT in core Atlas dependencies (modular).

---

## 📋 Experiment Log

| ID  | Name | Status | Notes |
|-----|------|--------|-------|
| 001 | Basic Explanation | 🚧 In Progress | Simple signal → text |
| 002 | RAG Integration | 📅 Planned | Use Atlas docs |
| 003 | Multimodal | 💡 Idea | Interpret charts |

---

## 🚀 Getting Started

### 1. Create Your First Experiment
```bash
cd atlas/python/src/atlas/lab/jarvis/experiments/
touch 001_my_first_assistant.py
```

### 2. Write Basic Code
```python
# experiments/001_my_first_assistant.py
"""
Experiment 001: Basic signal explanation
Goal: Convert Atlas signal dict to natural language
"""

def explain_signal(signal: dict) -> str:
    """Convert signal to human-readable text."""
    action = signal.get("type", "UNKNOWN")
    conf = signal.get("confidence", 0.0)
    reasons = signal.get("reasons", [])
    
    explanation = f"Atlas recommends {action} with {conf*100:.0f}% confidence."
    
    if reasons:
        explanation += "\n\nReasons:"
        for i, reason in enumerate(reasons, 1):
            explanation += f"\n{i}. {reason}"
    
    return explanation

if __name__ == "__main__":
    # Test
    test_signal = {
        "type": "LONG",
        "confidence": 0.78,
        "reasons": ["RSI oversold", "MACD crossover"]
    }
    print(explain_signal(test_signal))
```

### 3. Run It
```bash
python experiments/001_my_first_assistant.py
```

---

## 🎓 Learning Path

1. **Start simple:** Text templates (no AI yet)
2. **Add AI:** Call Claude/GPT for dynamic responses
3. **Add context:** RAG over Atlas docs
4. **Add tools:** Function calling to inspect real data
5. **Add multimodal:** Interpret charts, graphs

---

## ⚖️ Ethical Guidelines

### Jarvis Must:
- ✅ Be transparent about uncertainty
- ✅ Cite sources when possible
- ✅ Warn when data is incomplete
- ✅ Never claim certainty on predictions

### Jarvis Must NOT:
- ❌ Fabricate data
- ❌ Override risk controls
- ❌ Execute trades autonomously
- ❌ Provide financial advice (it's a tool, not an advisor)

---

## 📞 Questions?

If Jarvis experiments lead to interesting results, document them here 
and consider promotion to `atlas/assistants/`.

---

**Status:** Lab / Experimental  
**Created:** 2026-01-28  
**Last Updated:** 2026-01-28
