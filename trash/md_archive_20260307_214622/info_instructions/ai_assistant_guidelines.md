# ATLAS AI Collaboration Guidelines

This document outlines the specific roles and expected workflows for the different AI assistants (Antigravity, Claude, and ChatGPT) contributing to the Atlas project. 

By understanding these specializations, you can route tasks more effectively and maintain a clean, high-quality codebase.

## 1. Antigravity (Google) - The Architect & Integrator
**Primary Role:** Project structuration, architectural planning, and system integration.

*   **Focus Areas:** 
    *   Organizing the repository structure and ensuring files are in the right place.
    *   Designing how different modules (engines, data layers, UI) connect to each other.
    *   Reviewing constraints, planning workflows, and setting up the environment.
    *   Writing "glue code" to connect disparate systems and making sure the overarching "Atlas Philosophy" is maintained.
*   **When to deploy:** When starting a new phase, moving large amounts of files, integrating a new feature across the stack, or mapping out complex logic that requires reading the entire project context.

## 2. Claude (Anthropic) - The Builder & Scripter
**Primary Role:** Brute-force code generation and heavy lifting.

*   **Focus Areas:**
    *   Writing the bulk of the modules, scripts, and algorithms.
    *   Fleshing out large files (e.g., implementing 50+ technical indicators in a single go).
    *   Generating vast amounts of boilerplate or repetitive logic.
    *   Translating mathematical concepts (like from the `ALGORITHMS_LIBRARY.md`) into dense Python or JavaScript code.
*   **When to deploy:** When the architecture is already planned by Antigravity, and you need a massive chunk of logic built quickly and accurately based on specific constraints.

## 3. ChatGPT (OpenAI) - The Auditor & Debugger
**Primary Role:** Code auditing, bug fixing, and localized problem solving.

*   **Focus Areas:**
    *   Reviewing code sections that are failing or throwing errors.
    *   Refactoring messy, legacy, or orphaned code (utilizing Codex/advanced reasoning).
    *   Acting as a QA tester to ensure scripts follow the rules and don't break the build.
    *   Providing explanations for erratic system behavior or logical flaws in the mathematical models.
*   **When to deploy:** When a specific script is broken, a test is failing, or you need a second pair of 'eyes' to audit a complex function built by Claude.

---

### General Interaction Workflow

1.  **Antigravity** sets the plan, creates the folders, and defines the API/module contracts.
2.  **Claude** generates the heavy modules based on Antigravity's blueprint.
3.  **Antigravity** integrates Claude's modules into the main `run_atlas.py` or UI.
4.  **ChatGPT** audits the final integration, fixing any syntax bugs or runtime errors that emerge during the tests.
