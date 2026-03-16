# 🚀 ARIA v2.6 - INSTALLATION GUIDE

## 📦 Files Included

### Core Module (`core/`)
1. `system_prompt.py` - Professional system prompt v2.6
2. `validation.py` - Parameter validation system
3. `error_handler.py` - Error handling utilities
4. `chat.py` - Updated ARIA engine
5. `__init__.py` - Core module exports

### Tools Module (`tools/`)
6. `tool_schemas.py` - Tool parameter schemas

### Root (`aria/`)
7. `__init__.py` - ARIA package exports

## 📍 Installation

### Step 1: Backup Current Files
```bash
cd Atlas/python/src/atlas/assistants/aria
cp -r core core_backup_v25
```

### Step 2: Copy New Files
```bash
# Copy all files from this package to:
# Atlas/python/src/atlas/assistants/aria/

cp core/* Atlas/python/src/atlas/assistants/aria/core/
cp tools/* Atlas/python/src/atlas/assistants/aria/tools/
cp __init__.py Atlas/python/src/atlas/assistants/aria/
```

### Step 3: Test
```bash
cd Atlas
python -c "from atlas.assistants.aria import ARIA; print('✅ OK')"
```

### Step 4: Run ARIA
```bash
python apps/cli/terminal.py
```

## ✅ Verification

Ask ARIA: "What was AAPL's price on January 1, 2024?"

Expected:
- ✅ Parameter validation happens
- ✅ Clear error messages if invalid
- ✅ Professional responses

## 📊 What's New in v2.6

- ✅ Professional system prompt (combines v2.5 + v2.0)
- ✅ Parameter validation before tool execution
- ✅ User-friendly error messages
- ✅ Tool guidelines inline (when to use / not use)
- ✅ Examples with reasoning
- ✅ Statistics tracking

## 🎉 Completion

After installation:
- Move `ARIA_V26_CONSOLIDATION_MASTER.md` to `trash/`
- Update `ATLAS_MASTER_PLAN.md` with v2.6 completion

