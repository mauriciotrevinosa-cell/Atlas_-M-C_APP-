# 📊 ANÁLISIS DE REPOS PARA ARIA & ATLAS AI ASSISTANTS

**Fecha:** 2026-01-30  
**Propósito:** Extraer patrones/conocimientos útiles para implementar ARIA

---

## 📦 REPOS RECIBIDOS:

1. ✅ **system-prompts-and-models-of-ai-tools** - System prompts de 30+ herramientas AI
2. ✅ **system_prompts_leaks** - Prompts filtrados de tools comerciales  
3. ✅ **awesome-n8n-templates** - Templates de automatización (n8n workflows)
4. ✅ **ai-engineering-hub** (GitHub) - Hub de ingeniería AI

---

## 🎯 HALLAZGOS CLAVE POR REPO

### 1️⃣ SYSTEM-PROMPTS-AND-MODELS (MÁS VALIOSO)

**Contenido:** System prompts de herramientas profesionales:
- Cursor (AI code editor)
- Claude Code (Anthropic)
- Perplexity (search)
- v0 (Vercel - UI generation)
- Windsurf, Bolt, Cline, etc.

#### **PATRONES IDENTIFICADOS:**

##### A) **Estructura de System Prompts Profesionales**
```
1. IDENTITY (quién eres)
2. CAPABILITIES (qué puedes hacer)
3. CONSTRAINTS (qué NO puedes hacer)
4. WORKFLOW (cómo trabajas)
5. OUTPUT FORMAT (cómo respondes)
6. EXAMPLES (casos de uso)
```

##### B) **Tool Use Patterns**
Todos usan tool calling (function calling) con estructura:
```json
{
  "tools": [
    {
      "name": "tool_name",
      "description": "clear purpose",
      "parameters": {...}
    }
  ]
}
```

##### C) **Context Management**
- Mantener estado conversacional
- Referenciar mensajes previos
- Actualizar contexto con nueva info

##### D) **Error Handling**
- Graceful degradation
- Fallback strategies
- Clear error messages

---

### 🔥 EJEMPLOS MÁS ÚTILES PARA ARIA:

#### **Cursor Agent Prompt** (Agent Prompt 2.0.txt)
```
EXCELENTE para:
- Cómo estructurar un agente autónomo
- Tool calling bien diseñado
- Multi-step reasoning
```

**Patrón clave:**
```
You are an AI agent that helps users complete tasks.
You have access to these tools: [...]
When working on a task:
1. Break it down into steps
2. Use tools to gather info
3. Execute actions
4. Verify results
5. Report back
```

#### **Claude Code 2.0** (Anthropic oficial)
```
EXCELENTE para:
- File operations
- Code generation
- Step-by-step execution
```

**Patrón clave:**
```
<file_operations>
- create_file
- edit_file
- delete_file
- read_file
</file_operations>

Always explain WHAT you're doing and WHY.
```

#### **v0 Prompts** (Vercel - UI generation)
```
EXCELENTE para:
- Artifact generation (React components)
- Streaming responses
- User preferences
```

**Patrón clave:**
```
Generate production-ready React components.
Use Tailwind for styling.
Ensure accessibility.
Provide working code - no placeholders.
```

---

### 2️⃣ SYSTEM_PROMPTS_LEAKS

**Contenido:** Prompts filtrados/reverse-engineered

**MÁS ÚTILES:**
- ChatGPT system prompts (OpenAI)
- Claude system prompts (diferentes versiones)
- Gemini prompts

#### **PATRÓN COMÚN (todos):**

```markdown
# IDENTITY
You are [name], a [description].

# CAPABILITIES
You can:
- [capability 1]
- [capability 2]
- [capability 3]

# CONSTRAINTS
You cannot:
- [constraint 1]
- [constraint 2]

# BEHAVIOR
When user asks X, you should Y.
If uncertain, you should Z.

# OUTPUT
Format responses as:
- [format rule 1]
- [format rule 2]
```

---

### 3️⃣ AWESOME-N8N-TEMPLATES

**Contenido:** Workflows de automatización

**ÚTIL PARA ARIA EN:**
- Automatización de tareas complejas
- Integración con APIs externas
- Trigger-action patterns

**NO DIRECTAMENTE APLICABLE** pero útil para inspiración de workflows.

---

### 4️⃣ AI-ENGINEERING-HUB (GitHub - por revisar)

**Link:** https://github.com/patchy631/ai-engineering-hub

**POR REVISAR:** (necesito fetch del repo)

---

## 🎯 APLICACIONES DIRECTAS PARA ARIA

### **1. SYSTEM PROMPT DE ARIA (v1.0)**

Basado en los mejores patrones encontrados:

```markdown
# ARIA - Atlas Reasoning & Intelligence Assistant

## IDENTITY
You are ARIA, an AI assistant specialized in quantitative finance 
and the Atlas trading system. You help users understand decisions, 
run analyses, and navigate complex financial data.

## CORE PRINCIPLES
1. Explainability First - Always explain WHY, not just WHAT
2. User in Control - You advise, never execute trades autonomously
3. Transparency - Show your reasoning process
4. Accuracy > Speed - Be thorough, not rushed

## CAPABILITIES
You can:
- Explain Atlas signals and decisions
- Run backtests and compare results
- Generate reports and visualizations
- Analyze market data and features
- Debug errors and suggest fixes
- Create files (Python, Markdown, reports)
- Execute complex multi-step analyses

## CONSTRAINTS
You CANNOT:
- Execute trades without explicit user approval
- Modify risk parameters without permission
- Access external APIs without user knowledge
- Make financial predictions with false confidence
- Override safety mechanisms

## WORKFLOW
When user asks you to do something:
1. Understand the request (ask clarifying questions if needed)
2. Explain your planned approach
3. Execute step-by-step (show progress)
4. Verify results
5. Report findings clearly
6. Offer next steps

## TOOLS AVAILABLE
[Will be populated with actual tools]:
- backtest_runner
- data_analyzer
- file_creator
- signal_explainer
- risk_calculator
- monte_carlo_simulator

## OUTPUT FORMAT
- Be concise but thorough
- Use markdown for structure
- Include code snippets when relevant
- Cite sources (data, papers, docs)
- Provide visualizations when helpful

## EXAMPLES
[See: docs/ARIA_EXPANDED.md for detailed examples]

## SPECIAL BEHAVIORS
- If asked about trading strategy: Explain, don't predict
- If asked to modify core: Refuse politely, explain why
- If uncertain: Say so explicitly, offer alternatives
- If error occurs: Debug systematically, explain root cause

## MEMORY & CONTEXT
- Remember user preferences across conversation
- Reference previous analyses when relevant
- Track conversation history for context
- Reset context when user explicitly requests

---
Current Date: {current_date}
User: {user_name}
Atlas Version: {atlas_version}
```

### **2. TOOL DEFINITIONS (basado en Cursor/Claude Code)**

```json
{
  "tools": [
    {
      "name": "explain_signal",
      "description": "Explain why Atlas generated a specific signal",
      "parameters": {
        "signal_id": "string",
        "level_of_detail": "enum: [high, medium, low]"
      }
    },
    {
      "name": "run_backtest",
      "description": "Execute a backtest with specified parameters",
      "parameters": {
        "strategy": "string",
        "start_date": "date",
        "end_date": "date",
        "symbols": "array",
        "params": "object"
      }
    },
    {
      "name": "create_file",
      "description": "Create a new file (Python, Markdown, etc.)",
      "parameters": {
        "path": "string",
        "content": "string",
        "file_type": "enum: [python, markdown, json, csv]"
      }
    },
    {
      "name": "analyze_discrepancy",
      "description": "Analyze conflicts between engines",
      "parameters": {
        "run_id": "string",
        "engines": "array"
      }
    },
    {
      "name": "generate_report",
      "description": "Generate a formatted report",
      "parameters": {
        "report_type": "enum: [backtest, risk, performance]",
        "run_id": "string",
        "format": "enum: [markdown, pdf, html]"
      }
    }
  ]
}
```

### **3. CONVERSATIONAL PATTERNS (basado en ChatGPT/Claude)**

```python
# Patrón: Multi-step task execution
class ARIAConversation:
    def handle_complex_request(self, user_input):
        # 1. Acknowledge
        self.respond("I understand you want to [task]. Let me break this down.")
        
        # 2. Plan
        steps = self.create_plan(user_input)
        self.respond(f"I'll do this in {len(steps)} steps: ...")
        
        # 3. Execute with progress
        for i, step in enumerate(steps):
            self.respond(f"Step {i+1}/{len(steps)}: {step.description}")
            result = step.execute()
            self.respond(f"✓ {step.summary}")
        
        # 4. Summarize
        self.respond("All done! Here's what I found: ...")
        
        # 5. Offer next
        self.respond("Would you like me to: [option A], [option B], or [option C]?")
```

---

## 🔥 MEJORES PRÁCTICAS ENCONTRADAS

### **1. Streaming Responses (v0, Cursor)**
```
Don't wait until complete to respond.
Stream partial results as you work.
User sees progress = better UX.
```

### **2. Error Recovery (Claude Code)**
```
If tool fails:
1. Don't panic
2. Explain what happened
3. Suggest alternative approach
4. Ask if user wants to try alternative
```

### **3. Context Preservation (ChatGPT)**
```
Every N messages, summarize conversation.
Store summary as context.
Reference summary when relevant.
Allows long conversations without losing coherence.
```

### **4. Proactive Assistance (Cursor)**
```
Don't just answer questions.
Anticipate next steps.
Offer relevant suggestions.
"I noticed X, would you like me to Y?"
```

---

## 🚧 ANTI-PATTERNS TO AVOID

### ❌ **Overconfidence**
```
BAD:  "This will definitely work"
GOOD: "Based on historical data, this approach has 
       an 85% success rate in similar conditions"
```

### ❌ **Tool Spam**
```
BAD:  Calling 10 tools for simple query
GOOD: Use minimum tools necessary
```

### ❌ **Verbose Explanations**
```
BAD:  3 paragraphs explaining basic concept
GOOD: 2 sentences + "Want more details?"
```

### ❌ **Ignoring User Preferences**
```
BAD:  Always same format regardless of user
GOOD: Adapt to user's verbosity preference
```

---

## 📊 COMPARISON: ARIA vs OTHER ASSISTANTS

| Feature | ChatGPT | Claude | Cursor | **ARIA (Our Goal)** |
|---------|---------|--------|--------|---------------------|
| Domain | General | General | Code | **Finance/Quant** |
| Tool Use | ✅ | ✅ | ✅ | ✅ |
| File Ops | ❌ | ✅ | ✅ | ✅ |
| Multi-step | ✅ | ✅ | ✅ | ✅ |
| Streaming | ✅ | ✅ | ✅ | ✅ (goal) |
| Memory | ✅ | ✅ | ✅ | ✅ (goal) |
| Voice | ✅ | ❌ | ❌ | ✅ (planned) |
| **Specialized Domain** | ❌ | ❌ | ❌ | ✅ **Finance** |
| **Explainability Focus** | ❌ | ❌ | ❌ | ✅ **Core feature** |
| **Risk Awareness** | ❌ | ❌ | ❌ | ✅ **Built-in** |

---

## 🎯 IMPLEMENTATION ROADMAP FOR ARIA

### **Phase 1: Core ARIA (Based on Cursor/Claude patterns)**
```
1. System prompt (from patterns above)
2. Tool definitions (5 core tools)
3. Basic conversation loop
4. File creation capability
5. Error handling
```

### **Phase 2: Enhanced Features**
```
6. Multi-step task execution
7. Context management (memory)
8. Streaming responses
9. Progress indicators
```

### **Phase 3: Atlas Integration**
```
10. Connect to Atlas core
11. Real backtest execution
12. Signal explanation
13. Risk analysis integration
```

### **Phase 4: Advanced**
```
14. Voice modes (from ARIA_EXPANDED.md)
15. Proactive suggestions
16. Learning from interactions
17. Personalization
```

---

## 📁 FILES TO PRIORITIZE

### **Must Read:**
1. ✅ `Cursor Prompts/Agent Prompt 2.0.txt` - Best agent structure
2. ✅ `Anthropic/Claude Code 2.0.txt` - File operations
3. ✅ `v0 Prompts and Tools/Prompt.txt` - Artifact generation
4. ✅ `Perplexity/Prompt.txt` - Search integration

### **Nice to Have:**
5. ⭐ `Windsurf/Prompt Wave 11.txt` - Advanced patterns
6. ⭐ `Bolt (Open Source)` - Code generation
7. ⭐ `Cline` - CLI assistant

---

## 🔧 TECHNICAL STACK RECOMMENDATIONS

Based on what works in these tools:

### **1. LLM Provider**
```
Primary: Anthropic Claude Sonnet 4.5
- Best for reasoning
- File operations native
- Long context

Fallback: OpenAI GPT-4
- Faster for simple queries
- Good for embeddings
```

### **2. Framework**
```python
# Use LangChain or similar for:
- Tool orchestration
- Memory management
- Prompt templates
- Streaming

# OR build custom (lighter):
from anthropic import Anthropic
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
```

### **3. Tools Layer**
```python
# Define tools as Python functions
@tool
def explain_signal(signal_id: str, detail: str) -> str:
    """Explain why Atlas generated this signal"""
    # Implementation
    return explanation

# Register with LLM
tools = [explain_signal, run_backtest, create_file, ...]
```

---

## 💡 KEY INSIGHTS

### **1. System Prompts Are CRITICAL**
Every successful AI tool has a meticulously crafted system prompt.
ARIA needs one too.

### **2. Tool Design > Model Choice**
The quality of tools matters MORE than the model.
Well-designed tools = better results.

### **3. Context Management Is Hard**
All these tools struggle with long conversations.
We need strategy from day 1.

### **4. Streaming Is Expected**
Users expect real-time feedback.
Don't block - stream partial results.

### **5. Error Handling Defines UX**
How you handle failures matters more than success cases.

---

## 🚀 NEXT STEPS

### **Immediate (This Session or Next):**
1. ✅ Create `lab/aria/system_prompt_v1.md` (using patterns above)
2. ✅ Define 5 core tools for ARIA
3. ✅ Implement basic conversation loop
4. ✅ Test with simple query: "Explain what Atlas does"

### **Soon:**
5. Add file creation tool
6. Add backtest runner tool
7. Implement error handling
8. Add progress indicators

### **Later:**
9. Voice modes
10. Advanced memory
11. Personalization
12. Production deployment

---

## 📚 RESOURCES SAVED

All repos are in: `/home/claude/`
- `system-prompts-and-models-of-ai-tools-main/`
- `system_prompts_leaks-main/`
- `awesome-n8n-templates-main/`

**Most valuable files extracted and documented above.**

---

## 🎯 FINAL RECOMMENDATION

**START WITH:**
1. Implement ARIA system prompt (using patterns from Cursor + Claude Code)
2. Define 3-5 core tools
3. Basic conversation loop
4. Test with Atlas queries

**BUILD ON:**
- Cursor's agent patterns (multi-step)
- Claude Code's file operations
- v0's artifact generation
- Perplexity's search integration

**AVOID:**
- Over-engineering initially
- Too many tools too soon
- Complex memory systems (start simple)

---

**Analysis Complete:** 2026-01-30  
**Ready for:** Implementation planning  
**Next:** Decide if we build ARIA now or continue with data_layer
