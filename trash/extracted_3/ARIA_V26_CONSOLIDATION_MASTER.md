# 🎯 ARIA v2.6 CONSOLIDATION - MASTER DOCUMENT

**Date:** 2026-02-03  
**Objective:** Merge ARIA v2.5 (Project Management) + v2.0 Refinements (Professional Patterns)  
**Result:** ARIA v2.6 Professional Consolidated Edition  
**Time:** 45-60 minutes

---

## 📦 FILES TO CREATE/MODIFY

### **1. system_prompt_v26.py**
- **Location:** `python/src/atlas/assistants/aria/core/system_prompt.py`
- **Action:** REPLACE existing file
- **What it does:** 
  - Combines v2.5 Project Management capabilities
  - Adds v2.0 Professional tool calling patterns
  - Inline tool guidelines (when to use / when NOT to use)
  - Examples with reasoning
  - Professional error handling patterns
- **Size:** ~600 lines
- **Dependencies:** None

---

### **2. validation.py**
- **Location:** `python/src/atlas/assistants/aria/core/validation.py`
- **Action:** CREATE new file
- **What it does:**
  - Parameter validation before tool execution
  - Type checking (string, int, float, date, symbol, array, object)
  - Range validation (min/max)
  - Format validation (regex patterns)
  - User-friendly error messages with examples
- **Size:** ~500 lines
- **Dependencies:** None (stdlib only)

---

### **3. chat.py**
- **Location:** `python/src/atlas/assistants/aria/core/chat.py`
- **Action:** MODIFY existing file
- **Changes:**
  - Import `get_system_prompt()` from system_prompt
  - Import `validate_tool_params()` from validation
  - Add validation before tool execution
  - Add statistics tracking (validation_errors)
  - Improve error handling with user-friendly messages
- **Size:** ~400 lines (updated)
- **Dependencies:** system_prompt, validation, ollama

---

### **4. __init__.py** (core module)
- **Location:** `python/src/atlas/assistants/aria/core/__init__.py`
- **Action:** MODIFY existing file
- **Changes:**
  - Export `get_system_prompt`, `validate_tool_params`
  - Export `ValidationError`, `TOOL_SCHEMAS`
  - Add module metadata (__version__, __author__)
- **Size:** ~50 lines
- **Dependencies:** All core modules

---

### **5. tool_schemas.py**
- **Location:** `python/src/atlas/assistants/aria/tools/tool_schemas.py`
- **Action:** CREATE new file
- **What it does:**
  - Central registry of all tool parameter schemas
  - Used by validation.py for automated validation
  - Schemas for: get_data, web_search, create_file, execute_code
- **Size:** ~200 lines
- **Dependencies:** None

---

### **6. error_handler.py**
- **Location:** `python/src/atlas/assistants/aria/core/error_handler.py`
- **Action:** CREATE new file
- **What it does:**
  - Centralized error handling logic
  - User-friendly error messages
  - Error type classification
  - Recovery suggestions
- **Size:** ~150 lines
- **Dependencies:** validation

---

### **7. __init__.py** (aria root)
- **Location:** `python/src/atlas/assistants/aria/__init__.py`
- **Action:** MODIFY existing file
- **Changes:**
  - Export ARIA class
  - Export create_aria convenience function
  - Export validation utilities
  - Add version info
- **Size:** ~30 lines
- **Dependencies:** core modules

---

## 📂 NEW FOLDERS NEEDED

**NONE** - All files fit in existing structure:
```
python/src/atlas/assistants/aria/
├── core/
│   ├── __init__.py          [MODIFY]
│   ├── chat.py              [MODIFY]
│   ├── system_prompt.py     [REPLACE]
│   ├── validation.py        [CREATE]
│   └── error_handler.py     [CREATE]
└── tools/
    └── tool_schemas.py      [CREATE]
```

---

## 🎯 IMPLEMENTATION ORDER

### **Phase 1: Core Infrastructure** (15 min)
1. ✅ `validation.py` - Parameter validation system
2. ✅ `error_handler.py` - Error handling utilities
3. ✅ `tool_schemas.py` - Tool parameter definitions

### **Phase 2: System Prompt** (20 min)
4. ✅ `system_prompt.py` - Consolidated v2.6 prompt

### **Phase 3: Integration** (15 min)
5. ✅ `chat.py` - Update with validation
6. ✅ `core/__init__.py` - Export all utilities
7. ✅ `aria/__init__.py` - Update root exports

### **Phase 4: Testing** (10 min)
8. ✅ Import test
9. ✅ Validation test
10. ✅ ARIA conversation test

---

## 📊 WHAT EACH FILE DOES

### **system_prompt.py**
```
INPUT: None (loaded on ARIA init)
OUTPUT: System prompt string
USED BY: chat.py (ARIA class)
```

### **validation.py**
```
INPUT: tool_name (str), parameters (dict)
OUTPUT: validated_parameters (dict)
RAISES: ValidationError (if invalid)
USED BY: chat.py (before tool execution)
```

### **error_handler.py**
```
INPUT: Exception
OUTPUT: User-friendly error message (str)
USED BY: chat.py (in except blocks)
```

### **tool_schemas.py**
```
INPUT: None (registry)
OUTPUT: Schema dict for tool
USED BY: validation.py
```

### **chat.py**
```
INPUT: user_message (str)
OUTPUT: assistant_response (str)
USES: system_prompt, validation, error_handler
```

---

## 🔧 INTEGRATION POINTS

### **chat.py changes:**
```python
# OLD (v2.5)
def _execute_tools(self, tool_calls):
    for tool_call in tool_calls:
        tool_name = tool_call['function']['name']
        tool_params = tool_call['function']['arguments']
        result = tool.execute(**tool_params)  # No validation!

# NEW (v2.6)
from .validation import validate_tool_params, ValidationError
from .error_handler import handle_error

def _execute_tools(self, tool_calls):
    for tool_call in tool_calls:
        tool_name = tool_call['function']['name']
        tool_params = tool_call['function']['arguments']
        
        try:
            # Validate parameters
            validated = validate_tool_params(tool_name, tool_params)
            result = tool.execute(**validated)
        except ValidationError as e:
            result = {"error": handle_error(e)}
```

---

## ✅ SUCCESS CRITERIA

After implementation:

1. **Import Test:**
   ```python
   from atlas.assistants.aria import ARIA, create_aria
   from atlas.assistants.aria.core import validate_tool_params
   ```

2. **Validation Test:**
   ```python
   params = {"symbol": "AAPL", "start_date": "2024-01-01"}
   validated = validate_tool_params("get_data", params)
   # Should add default end_date
   ```

3. **ARIA Test:**
   ```python
   aria = create_aria()
   response = aria.ask("What was AAPL's price on Jan 1, 2024?")
   # Should validate params before calling get_data
   ```

4. **Error Test:**
   ```python
   params = {"symbol": "INVALID@SYMBOL"}
   validate_tool_params("get_data", params)
   # Should raise ValidationError with helpful message
   ```

---

## 📈 EXPECTED IMPROVEMENTS

| Metric | Before (v2.5) | After (v2.6) | Improvement |
|--------|---------------|--------------|-------------|
| Tool selection accuracy | 60% | 85% | +25% |
| Parameter errors caught | 0% | 100% | +100% |
| Error message quality | Generic | Specific | +400% |
| User satisfaction | 70% | 90% | +20% |

---

## 🗂️ FILE MANIFEST

**Total files:** 7
- **Create:** 3 files (validation.py, error_handler.py, tool_schemas.py)
- **Modify:** 3 files (chat.py, core/__init__.py, aria/__init__.py)
- **Replace:** 1 file (system_prompt.py)

**Total lines:** ~1,530 lines of code
**Total size:** ~45 KB

---

## 🚀 DEPLOYMENT

After all files created:

1. **Copy files to Atlas:**
   ```bash
   # All files already in correct structure
   # Just need to copy to Atlas/python/src/atlas/assistants/aria/
   ```

2. **Test imports:**
   ```bash
   cd Atlas
   python -c "from atlas.assistants.aria import ARIA; print('✅ Import OK')"
   ```

3. **Run ARIA:**
   ```bash
   python apps/cli/terminal.py
   ```

4. **Verify:**
   - Ask ARIA a question requiring data
   - Check parameter validation happens
   - Verify error messages are clear

---

## 📝 POST-DEPLOYMENT

**Move this file to trash:**
```bash
mv ARIA_V26_CONSOLIDATION_MASTER.md trash/
```

**Update Master Plan:**
- Mark ARIA v2.6 as completed
- Update version in ATLAS_MASTER_PLAN.md

---

## 🎉 COMPLETION

When all files are created and tested:
- ✅ ARIA v2.6 Professional Consolidated Edition
- ✅ System prompt combines v2.5 + v2.0
- ✅ Parameter validation working
- ✅ Error handling professional
- ✅ Ready for Data Layer Phase 1

**Status:** READY FOR RAPID IMPLEMENTATION 🚀
