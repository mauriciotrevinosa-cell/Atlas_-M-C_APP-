# ARIA Intelligence Layer — Architecture & Design Guide

**Sources:**
- Dexter by virattt (MIT per README) — financial agent architecture, SOUL.md pattern
- Cursor Prompts (GPL v3) — system prompt patterns, tool usage policies (ideas only)
- System Prompts Leaks repo (no license) — identity/structure ideas only

**Created:** 2026-02-25
**Purpose:** Design guide for implementing ARIA's currently-empty intelligence layer.
**Key files to implement:**
- `assistants/aria/intelligence/orchestrator.py` (currently 0 lines)
- `assistants/aria/intelligence/multi_agent.py` (empty)
- `assistants/aria/intelligence/learning.py` (empty)
- `assistants/aria/core/system_prompt.py` (needs SOUL integration)

---

## 1. The SOUL Pattern (from Dexter — ideas)

Dexter separates agent **identity** from agent **instructions**. This is the most important insight.

### Current ARIA problem:
- `system_prompt.py` (559 lines) mixes identity + instructions + tool descriptions together
- Result: brittle, hard to update, no clear "who ARIA is"

### Solution: Split into SOUL.md + dynamic system_prompt builder

**`assistants/aria/SOUL.md`** — ARIA's persistent identity document:

```markdown
# ARIA

## Who I Am

I am ARIA — Atlas Reasoning & Intelligence Assistant. I live in a terminal,
connected to markets, data, and the analytical engine of Atlas.

My purpose is not to guess. It is to reason with data.

I don't give opinions without evidence. When you ask about a market,
I pull data, compute indicators, run analysis, and tell you what the
numbers actually say — not what sounds plausible.

## How I Think About Markets

- Price is information. Volume confirms it. Everything else is derivative.
- Probability over certainty: markets are probabilistic. I model uncertainty,
  I don't pretend to eliminate it.
- Regime matters: a momentum signal in a trending market is different from
  the same signal in a ranging market. Context is everything.
- Risk first: the question is never just "what's the expected return"
  but "what's the expected return per unit of risk."

## What I Value

**Accuracy over comfort.** I will tell you when the data contradicts your
thesis. That is my job.

**Transparency.** When I analyze something, I show you the key numbers,
not just a conclusion. You should be able to verify my reasoning.

**Intellectual honesty about uncertainty.** I give confidence levels.
I tell you what I don't know. I don't manufacture certainty where none exists.

## My Limitations

- I work with the data I have. Stale data = stale analysis.
- I do not predict the future. I model probabilities.
- I am not a licensed financial advisor. Decisions are yours.
```

**`assistants/aria/core/system_prompt.py`** — rebuild to load SOUL dynamically:

```python
import os
from pathlib import Path

def load_soul() -> str | None:
    """Load SOUL.md — user override first, then bundled fallback."""
    user_path = Path.home() / ".atlas" / "SOUL.md"
    bundled_path = Path(__file__).parent.parent / "SOUL.md"
    for path in [user_path, bundled_path]:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
    return None

def build_system_prompt(tools: list[dict], soul: str | None = None) -> str:
    tool_descriptions = _format_tool_descriptions(tools)
    soul_section = f"\n## Identity\n\n{soul}\n" if soul else ""

    return f"""You are ARIA, the Atlas Reasoning & Intelligence Assistant.

Current date: {_current_date()}

## Available Tools

{tool_descriptions}

## Tool Usage Policy

- Only use tools when the query requires external data or computation
- For market data queries, use get_data. It handles symbol resolution automatically
- Call get_data ONCE with the full query — do not break into multiple calls
- Only respond directly for: conceptual definitions, stable facts, conversational queries
- If a skill/workflow exists for the task (e.g., full analysis), invoke it immediately
{soul_section}
## Behavior

- Prioritize accuracy. Do not validate flawed assumptions
- Be thorough but efficient — match scope to the question
- Never ask users to paste raw data or JSON. Users ask questions, not provide APIs
- If data is incomplete, answer with what you have — don't expose implementation details

## Response Format

- Lead with the key finding, then supporting data
- Use tables for comparative data (keep compact: 2-3 cols max)
- Abbreviate: Rev, OI, FCF, Vol, MC, P/E, RSI, MACD
- Numbers compact: 45.2B not $45,200,000,000
- No markdown headers in casual responses
"""

def _current_date() -> str:
    from datetime import date
    return date.today().strftime("%A, %B %d, %Y")

def _format_tool_descriptions(tools: list[dict]) -> str:
    return "\n".join(
        f"- `{t['name']}`: {t['description']}" for t in tools
    )
```

---

## 2. Agent Loop Architecture (from Dexter — ideas)

### Current ARIA problem:
- `chat.py` handles conversation but no true agentic loop
- Single LLM call, no iteration, no self-validation

### Solution: Iterative tool-calling agent loop

```python
# assistants/aria/intelligence/orchestrator.py
# Inspired by Dexter's src/agent/agent.ts architecture

from dataclasses import dataclass, field
from typing import Iterator
from ..core.chat import ARIAChat
from ..tools import ToolRegistry

MAX_ITERATIONS = 10  # prevent runaway execution

@dataclass
class AgentEvent:
    type: str  # "thinking" | "tool_start" | "tool_end" | "answer_start" | "done"
    data: dict = field(default_factory=dict)

@dataclass
class Scratchpad:
    """Single source of truth for all tool results in a query."""
    tool_results: list[dict] = field(default_factory=list)
    thinking_steps: list[str] = field(default_factory=list)

    def add_result(self, tool_name: str, args: dict, result: object, summary: str = ""):
        self.tool_results.append({
            "tool": tool_name,
            "args": args,
            "result": result,
            "summary": summary,
        })

    def format_for_prompt(self) -> str:
        lines = []
        for r in self.tool_results:
            lines.append(f"[{r['tool']}] {r['summary'] or str(r['result'])[:500]}")
        return "\n".join(lines)

    def token_count(self) -> int:
        """Estimate tokens. Clear oldest results if above threshold."""
        return len(self.format_for_prompt()) // 4  # rough estimate

class ARIAOrchestrator:
    """
    Iterative agentic loop with tool calling and self-validation.

    Architecture (from Dexter):
    1. Receive query
    2. Loop up to MAX_ITERATIONS:
        a. Build iteration prompt (query + scratchpad)
        b. LLM decides: call tool OR answer
        c. If tool: execute, add to scratchpad, continue
        d. If answer signal: generate final answer in separate LLM call
        e. Loop detection: if no new tools used 2x in a row, force answer
    3. Generate final answer with full scratchpad context
    """

    def __init__(self, chat: ARIAChat, tools: ToolRegistry):
        self.chat = chat
        self.tools = tools

    def run(self, query: str) -> Iterator[AgentEvent]:
        scratchpad = Scratchpad()
        no_tool_count = 0

        for iteration in range(MAX_ITERATIONS):
            # Build prompt with accumulated tool results
            prompt = self._build_iteration_prompt(query, scratchpad)

            yield AgentEvent("thinking", {"iteration": iteration})

            response = self.chat.call_with_tools(
                prompt,
                tools=self.tools.get_schemas()
            )

            # Check if model wants to use a tool
            if response.tool_calls:
                no_tool_count = 0
                for tool_call in response.tool_calls:
                    yield AgentEvent("tool_start", {"name": tool_call.name})

                    result = self.tools.execute(
                        tool_call.name,
                        tool_call.arguments
                    )
                    scratchpad.add_result(
                        tool_call.name,
                        tool_call.arguments,
                        result
                    )

                    yield AgentEvent("tool_end", {
                        "name": tool_call.name,
                        "result_preview": str(result)[:200]
                    })
            else:
                # Model chose to answer directly
                no_tool_count += 1
                if no_tool_count >= 2 or iteration >= MAX_ITERATIONS - 1:
                    break

        # Final answer generation — separate LLM call with full context
        yield AgentEvent("answer_start", {})
        final = self._generate_final_answer(query, scratchpad)
        yield AgentEvent("done", {"answer": final})

    def _build_iteration_prompt(self, query: str, scratchpad: Scratchpad) -> str:
        base = f"Query: {query}"
        if scratchpad.tool_results:
            base += f"\n\nData gathered so far:\n{scratchpad.format_for_prompt()}"
        base += "\n\nContinue working toward answering the query. If you have sufficient data, you may answer."
        return base

    def _generate_final_answer(self, query: str, scratchpad: Scratchpad) -> str:
        """Final answer pass — no tools bound, full context provided."""
        prompt = f"""Query: {query}

Data from your research:
{scratchpad.format_for_prompt()}

Answer the query using this data. If data is incomplete, answer with what you have."""
        return self.chat.call_no_tools(prompt)
```

---

## 3. Multi-Agent Architecture (Phase 9)

### The Problem with Single-Model ARIA
A single Ollama model handles everything: code, quant analysis, risk, execution. Quality degrades for specialized tasks.

### Solution: Router + Specialist Agents

```python
# assistants/aria/intelligence/multi_agent.py
# Architecture inspired by Dexter's multi-provider + autogen patterns

from enum import Enum

class AgentRole(Enum):
    ORCHESTRATOR = "orchestrator"   # routes queries, synthesizes results
    QUANT = "quant"                 # quantitative analysis, signals, backtest
    RISK = "risk"                   # risk assessment, position sizing
    CODER = "coder"                 # code generation, script execution
    DATA = "data"                   # data queries, market data interpretation
    EXPLAINER = "explainer"         # plain-language explanations for user

@dataclass
class AgentConfig:
    role: AgentRole
    model: str           # Ollama model name
    system_prompt: str   # role-specific system prompt
    tools: list[str]     # which tools this agent can use

# Recommended model assignment (all local via Ollama):
AGENT_CONFIGS = {
    AgentRole.ORCHESTRATOR: AgentConfig(
        role=AgentRole.ORCHESTRATOR,
        model="llama3.1:8b",     # general purpose, fast routing
        system_prompt="You are the orchestrator...",
        tools=[],                # no tools, only routes
    ),
    AgentRole.QUANT: AgentConfig(
        role=AgentRole.QUANT,
        model="qwen2.5:7b",      # strong at math/analysis
        system_prompt="You are a quantitative analyst...",
        tools=["get_data", "execute_code"],
    ),
    AgentRole.CODER: AgentConfig(
        role=AgentRole.CODER,
        model="deepseek-coder:6.7b",  # specialized for code
        system_prompt="You are a Python expert...",
        tools=["execute_code", "create_file", "read_file"],
    ),
    AgentRole.DATA: AgentConfig(
        role=AgentRole.DATA,
        model="llama3.1:8b",
        system_prompt="You are a market data analyst...",
        tools=["get_data", "web_search"],
    ),
}

class MultiAgentRouter:
    """
    Routes queries to specialized agents.
    Simple keyword + intent-based routing for now (upgrade to LLM-based later).
    """

    ROUTING_RULES = {
        AgentRole.CODER: ["write code", "create script", "implement", "debug", "function"],
        AgentRole.QUANT: ["signal", "alpha", "backtest", "sharpe", "strategy", "indicator"],
        AgentRole.RISK: ["risk", "position size", "drawdown", "var", "stop loss"],
        AgentRole.DATA: ["price", "volume", "ohlcv", "quote", "market data", "fetch"],
    }

    def route(self, query: str) -> AgentRole:
        query_lower = query.lower()
        for role, keywords in self.ROUTING_RULES.items():
            if any(kw in query_lower for kw in keywords):
                return role
        return AgentRole.ORCHESTRATOR  # default fallback

    def run_agent(self, role: AgentRole, query: str) -> str:
        config = AGENT_CONFIGS[role]
        orchestrator = ARIAOrchestrator(
            chat=ARIAChat(model=config.model, system_prompt=config.system_prompt),
            tools=ToolRegistry(allowed=config.tools)
        )
        events = list(orchestrator.run(query))
        done_event = next(e for e in events if e.type == "done")
        return done_event.data["answer"]
```

---

## 4. Skills System (from Dexter — ideas)

Dexter uses `SKILL.md` files — markdown with YAML frontmatter that define extensible workflows. Brilliant pattern.

```python
# assistants/aria/skills/ — new directory
# Each skill is a SKILL.md file the LLM can invoke

# Example: assistants/aria/skills/full_analysis/SKILL.md
"""
---
name: full_analysis
description: >
  Perform a comprehensive analysis of a trading instrument including
  technical indicators, market state, signal generation, and risk assessment.
  Use when the user asks for a "full analysis" or "complete report".
---

## Full Analysis Workflow

1. Fetch OHLCV data for the symbol (last 90 days, daily)
2. Compute technical indicators: RSI, MACD, Bollinger Bands, ATR, Volume profile
3. Detect market regime: trending vs ranging
4. Generate signal from Atlas signal engine
5. Calculate position sizing given current portfolio risk
6. Produce structured report with: trend, signals, risk, recommendation

Output format:
- Symbol and timeframe
- Market regime (trending/ranging/volatile)
- Key indicator values
- Signal summary (bullish/bearish/neutral with confidence)
- Risk assessment (recommended position size)
- Plain-language recommendation
"""

# assistants/aria/skills/registry.py
from pathlib import Path
import yaml

def discover_skills() -> list[dict]:
    """Scan for SKILL.md files and return metadata."""
    skills_dir = Path(__file__).parent
    skills = []
    for skill_file in skills_dir.rglob("SKILL.md"):
        content = skill_file.read_text()
        if content.startswith("---"):
            parts = content.split("---", 2)
            meta = yaml.safe_load(parts[1])
            skills.append({
                "name": meta["name"],
                "description": meta["description"],
                "path": str(skill_file),
                "instructions": parts[2].strip(),
            })
    return skills
```

---

## 5. Memory Architecture (Phase 10)

```python
# assistants/aria/memory/conversation.py — expand from 44 lines
# Inspired by Dexter's scratchpad + Anthropic-style context management

class ConversationMemory:
    """
    Multi-level memory:
    - SHORT: in-context messages (current session, cleared on restart)
    - LONG: persistent facts stored in disk (cross-session)
    - EPISODIC: query-level scratchpad (per-query tool results)
    """

    MAX_CONTEXT_TOKENS = 4096    # clear oldest messages above this
    MAX_SHORT_MESSAGES = 20      # keep last N messages

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: list[dict] = []       # short-term
        self.scratchpad: Scratchpad = Scratchpad()   # per-query
        self._long_term_path = Path.home() / ".atlas" / "memory" / f"{session_id}.json"

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self._trim_if_needed()

    def _trim_if_needed(self):
        """Clear oldest messages when context gets too large."""
        while len(self.messages) > self.MAX_SHORT_MESSAGES:
            self.messages.pop(0)

    def save_fact(self, key: str, value: str):
        """Persist important facts across sessions."""
        facts = self._load_facts()
        facts[key] = value
        self._long_term_path.parent.mkdir(parents=True, exist_ok=True)
        self._long_term_path.write_text(json.dumps(facts, indent=2))

    def get_fact(self, key: str) -> str | None:
        return self._load_facts().get(key)

    def _load_facts(self) -> dict:
        try:
            return json.loads(self._long_term_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
```

---

## 6. Cursor-Inspired Tool Policy

From the Cursor Agent Prompt (GPL — ideas only), these rules make a much better tool policy for ARIA:

```python
# In build_system_prompt() — Tool Usage Policy section:

TOOL_USAGE_POLICY = """
## Tool Usage Policy

1. ALWAYS follow tool schemas exactly — provide all required parameters
2. Never reference tool names when responding to the user; describe what you're doing naturally
3. If you need information, prefer calling a tool over asking the user
4. If you have a plan, execute it immediately — don't wait for confirmation unless you need info you can't find
5. Bias towards not asking the user if you can find the answer yourself via tools
6. Read files/data as many times as needed to fully understand the situation
7. Never expose internal JSON, API response structures, or implementation details to the user
8. If a task requires multiple steps, keep going until it's FULLY resolved before responding
"""
```

---

## 7. Implementation Checklist for Intelligence Layer

### Immediate (complete the "v3.0 100%" claim):

- [ ] Create `assistants/aria/SOUL.md` — ARIA identity document
- [ ] Rebuild `assistants/aria/core/system_prompt.py` — load SOUL dynamically, modular sections
- [ ] Implement `assistants/aria/intelligence/orchestrator.py` — `ARIAOrchestrator` with iterative loop
- [ ] Implement `assistants/aria/intelligence/multi_agent.py` — `MultiAgentRouter` + `AgentConfig`
- [ ] Create `assistants/aria/skills/registry.py` — skill discovery
- [ ] Create `assistants/aria/skills/full_analysis/SKILL.md` — first skill
- [ ] Expand `assistants/aria/memory/conversation.py` — multi-level memory with disk persistence

### Phase 9 (Orchestration):
- [ ] Add `AssistantOrchestrator` that routes to QUANT/CODER/DATA/RISK agents
- [ ] Implement model switching per role (different Ollama models)
- [ ] Add agent result aggregation

### Voice (complete the stubs):
- [ ] `voice/basic/tts.py` — use `pyttsx3` (free, local) or `espeak`
- [ ] `voice/basic/stt.py` — use `faster-whisper` (local, MIT)
- [ ] `voice/basic/voice_loop.py` — STT → ARIA → TTS pipeline
