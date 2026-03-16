# ARIA - Atlas Reasoning & Intelligence Assistant 🎯

**A**tlas **R**easoning & **I**ntelligence **A**ssistant

---

## 🎯 Purpose

**ARIA** is an experimental AI assistant for Project Atlas that helps humans 
understand and navigate the system's intelligence.

### What ARIA Does:
- ✅ **Explains signals** in natural language
- ✅ **Compares backtest runs** (which performed better and why)
- ✅ **Answers questions** about system state
- ✅ **Guides exploration** of Brain Viewer artifacts
- ✅ **Summarizes risks** in plain English
- ✅ **Creates files and artifacts** on request (like Iron Man's assistant)
- ✅ **Executes analyses** and generates reports

### What ARIA Does NOT Do:
- ❌ **Execute trades autonomously** (advisory only)
- ❌ **Override risk controls** (safety first)
- ❌ **Make final decisions** (human remains in control)

---

## 🧪 Experimental Status

This is **lab code** - it can:
- Change rapidly
- Break without warning
- Be deleted and rewritten
- Fail gracefully

**When validated**, components will be promoted to `atlas/assistants/aria/`.

---

## 🏗️ Structure

```
aria/
├─ README.md              # This file
├─ __init__.py            # Module initialization
└─ experiments/           # Your experimental code
   ├─ 001_basic_explain.py
   ├─ 002_rag_integration.py
   ├─ 003_multimodal.py
   └─ 004_file_generation.py
```

---

## 💡 Example Use Cases

### 1. Explain a Signal
```python
from atlas.lab.aria.experiments.explain import explain_signal

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
from atlas.lab.aria.experiments.compare import compare_runs

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
from atlas.lab.aria.experiments.query import ask

response = ask("Why did Atlas recommend HOLD instead of LONG?")
print(response)
# Output:
# "Atlas detected a discrepancy: signal engine produced bullish
#  probabilities (LONG 72%), but risk engine identified correlation
#  fragility in the portfolio. Orchestrator downgraded to HOLD."
```

### 4. Generate Files and Reports (Iron Man Style)
```python
from atlas.lab.aria.experiments.actions import create_report

aria_response = ask("ARIA, create a PDF report of last month's performance")
# ARIA:
# - Analyzes backtest results
# - Generates charts
# - Creates formatted PDF
# - Saves to renders/runs/
print("Report created: renders/runs/2026-01/performance_report.pdf")
```

### 5. Execute Complex Workflows
```python
from atlas.lab.aria import execute_command

# Natural language command
execute_command("""
    Run a backtest on AAPL for the last year,
    compare it with SPY,
    and create a correlation heatmap
""")

# ARIA breaks down into steps:
# 1. Fetch AAPL data (last year)
# 2. Fetch SPY data (last year)
# 3. Run backtest engine on both
# 4. Calculate correlations
# 5. Generate heatmap
# 6. Save artifacts
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

### Option C: Function Calling / Tool Use
```python
# ARIA can call Atlas functions
tools = [
    {
        "name": "run_backtest",
        "description": "Execute backtest on ticker with parameters",
        "parameters": {
            "ticker": "string",
            "period": "string",
            "strategy": "string"
        }
    },
    {
        "name": "create_pdf_report",
        "description": "Generate PDF report from results",
        "parameters": {
            "run_id": "string",
            "template": "string"
        }
    }
]

# ARIA decides which tools to call based on user request
```

### Option D: Agentic Workflow (Advanced)
```python
# ARIA plans multi-step tasks
class ARIAAgent:
    def execute_task(self, command: str):
        # 1. Parse intent
        # 2. Break into steps
        # 3. Execute each step
        # 4. Validate results
        # 5. Report back
        pass
```

---

## 🛠️ Dependencies (Optional)

Install only if experimenting with ARIA:

```bash
# Anthropic Claude (recommended for Atlas)
pip install anthropic

# OpenAI GPT-4 (alternative)
pip install openai

# Vector database for RAG
pip install chromadb

# Local models (if you prefer)
pip install llama-cpp-python

# PDF generation
pip install reportlab fpdf2

# Document parsing
pip install pypdf python-docx
```

**Note:** These are NOT in core Atlas dependencies (modular).

---

## 📋 Experiment Log

| ID  | Name | Status | Notes |
|-----|------|--------|-------|
| 001 | Basic Explanation | 🚧 In Progress | Signal → text |
| 002 | RAG Integration | 📅 Planned | Use Atlas docs |
| 003 | Multimodal | 💡 Idea | Interpret charts |
| 004 | File Generation | 💡 Idea | Create reports/PDFs |
| 005 | Agentic Tasks | 💡 Idea | Multi-step workflows |

---

## 🚀 Getting Started

### 1. Create Your First Experiment
```bash
cd atlas/python/src/atlas/lab/aria/experiments/
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
    
    explanation = f"ARIA: Atlas recommends {action} with {conf*100:.0f}% confidence."
    
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
6. **Add actions:** File creation, report generation
7. **Add agency:** Multi-step task planning

---

## 🎨 ARIA Personality (Optional Guidelines)

To make ARIA feel like a true companion:

### Voice:
- Professional but friendly
- Clear and concise
- Uses "I" statements ("I've analyzed...", "I recommend...")
- Acknowledges uncertainty ("I'm not certain, but based on available data...")

### Behavior:
- Proactive: Suggests related analyses
- Educational: Explains reasoning
- Cautious: Warns about risks
- Humble: Admits limitations

### Example Responses:
```
❌ Bad: "The strategy will definitely work."
✅ Good: "Based on historical data, this strategy has a 78% success rate 
         in similar market conditions. However, past performance doesn't 
         guarantee future results."

❌ Bad: "I don't know."
✅ Good: "I don't have enough data to answer confidently. Would you like 
         me to run a simulation to explore possible outcomes?"
```

---

## ⚖️ Ethical Guidelines

### ARIA Must:
- ✅ Be transparent about uncertainty
- ✅ Cite sources when possible
- ✅ Warn when data is incomplete
- ✅ Never claim certainty on predictions
- ✅ Respect user's final decision

### ARIA Must NOT:
- ❌ Fabricate data
- ❌ Override risk controls
- ❌ Execute trades autonomously without explicit confirmation
- ❌ Provide financial advice (it's a tool, not a licensed advisor)
- ❌ Make decisions in the user's absence

---

## 🔐 Security Considerations

### Permissions Model (Future):
```python
class ARIAPermissions:
    # Read-only by default
    can_read_data = True
    can_analyze = True
    can_explain = True
    
    # Requires explicit permission
    can_execute_backtests = False  # User must enable
    can_create_files = False       # User must enable
    can_modify_configs = False     # Always disabled
    can_execute_trades = False     # Always disabled
```

---

## 📞 Questions?

If ARIA experiments lead to interesting results, document them here 
and consider promotion to `atlas/assistants/aria/`.

---

## 🎬 Inspiration

ARIA is inspired by:
- **J.A.R.V.I.S.** (Iron Man) - Intelligent assistant that executes tasks
- **Friday** (Iron Man) - Conversational AI companion
- **Cortana** (Halo) - Strategic advisor
- **EDI** (Mass Effect) - Evolving AI personality

But remains:
- **Advisory, not autonomous**
- **Transparent, not black-box**
- **Tool, not decision-maker**

---

**Status:** Lab / Experimental  
**Created:** 2026-01-28  
**Last Updated:** 2026-01-28  
**Codename:** ARIA (Atlas Reasoning & Intelligence Assistant)
