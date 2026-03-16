# Project Atlas 🧭

**Quantitative Intelligence System for Explainable Market Analysis**

---

## 🎯 What is Atlas?

Atlas is a **modular, multi-language quantitative system** focused on:
- ✅ **Explainability** over black-box predictions
- ✅ **Architecture** that evolves without breaking
- ✅ **Best tool for each job** (Python, C++, TypeScript, GPU)
- ✅ **Lab-to-Production workflow** (experiment → validate → deploy)

> ⚠️ **Important:** Atlas is NOT an autonomous trading bot. It's an **analytical intelligence system** that supports human decision-making.

---

## 🏗️ Project Structure

```
atlas/
├─ docs/                    # 📚 Documentation (single source of truth)
├─ configs/                 # ⚙️ Configuration files
├─ data/                    # 💾 Data (git-ignored)
├─ python/                  # 🐍 Python core
│  └─ src/atlas/
│     ├─ config/           # Configuration system
│     ├─ common/           # Shared utilities
│     └─ lab/              # 🧪 Experimental code
│        └─ quantum/       # Quantum finance experiments
└─ scratch/                 # 🗑️ Temporary code/experiments
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd python
pip install -e .
```

### 2. Run Your First Experiment
```bash
python -c "from atlas.lab.quantum import hello; hello()"
```

### 3. Read the Docs
```bash
cat docs/00_INDEX.md
```

---

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| `docs/00_INDEX.md` | Map of all documentation |
| `docs/03_WORKFLOW.md` | Canonical workflow (how Atlas thinks) |
| `docs/99_EVOLUTION_LOG.md` | History of structural changes |

---

## 🧪 Philosophy

### **"Grow, Don't Plan"**
- Start minimal, expand when needed
- Document intentions, not mandates
- Lab experiments → validated code → production

### **"Best Tool for the Job"**
- Python for orchestration & data science
- C++ for performance-critical paths
- TypeScript for modern UI
- GPU for massive parallel compute

### **"Explainability First"**
- Every signal must be auditable
- No black boxes in production
- If it can't be explained, it doesn't ship

---

## 🎓 Learning Path

1. **Start here:** Read `docs/00_INDEX.md`
2. **Understand the workflow:** `docs/03_WORKFLOW.md`
3. **Run experiments:** `python/src/atlas/lab/`
4. **Check evolution:** `docs/99_EVOLUTION_LOG.md`

---

## 🔧 Development

### Current Phase: **PHASE 0 - Foundation**
- ✅ Minimal skeleton created
- ✅ Documentation structure defined
- 🚧 Lab experiments (quantum finance)
- ⏳ Data layer (coming soon)

See `docs/99_EVOLUTION_LOG.md` for roadmap.

---

## 📜 License

[Add your license here]

---

## 🤝 Contributing

This is a personal research project in active development.

**Contribution guidelines coming soon.**

---

**Last Updated:** 2026-01-28  
**Version:** 0.1.0-alpha (Phase 0)
