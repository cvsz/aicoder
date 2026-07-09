# Codebase Refactoring Implementation Plan (v1 -> v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the `zai-coder-cli` codebase into a modular structure (`/api`, `/agents`, `/core`, `/utils`) while maintaining backward compatibility and simplifying `main.py`.

**Architecture:** Moving from a flat directory structure with many `claude_*.py` files to a grouped directory structure. `coder.py` will become the central orchestrator, delegating to the new folder structure.

**Tech Stack:** Python

## Global Constraints

- Talk Thai, coding in English.
- Maintain existing functionality; `main.py` interfaces must remain the same to avoid breaking CLI usage.
- Preservation of git history using `git mv` is required.

---

### Task 1: Structural Setup (Directories and Git Move)

**Files:**
- Create: Directories `api`, `agents`, `core`, `utils`
- Modify: Move all files according to the design spec using `git mv`

- [ ] **Step 1: Create directories**
```bash
mkdir -p api agents core utils
```

- [ ] **Step 2: Move API files**
```bash
git mv claude_models.py claude_batch.py claude_files.py claude_stream.py claude_structured.py api/
```

- [ ] **Step 3: Move Agent files**
```bash
git mv claude_agents_sdk.py claude_fable5.py claude_mythos5.py cowork.py claude_workflow.py agents/
```

- [ ] **Step 4: Move Core/Utils files**
```bash
git mv coder.py config.py utils.py claude_settings.py claude_code_exec.py claude_tools.py core/
git mv claude_metrics.py claude_tokens.py claude_observability.py utils/
```

- [ ] **Step 5: Commit**
```bash
git commit -m "refactor: reorganize codebase structure"
```

### Task 2: Import Resolution

**Files:**
- Modify: All files with import statements
- Test: Smoke test by running help command `python main.py --help`

- [ ] **Step 1: Update imports across the project**
(This involves running a find/replace script to update `import claude_models` to `import api.claude_models`, etc.)

- [ ] **Step 2: Smoke test**
```bash
python main.py --help
```
Expected: Help message displays without `ImportError`.

- [ ] **Step 3: Commit**
```bash
git commit -m "refactor: update imports for new structure"
```

### Task 3: Centralize Core Orchestration (`main.py` -> `coder.py`)

**Files:**
- Modify: `main.py`, `core/coder.py`

- [ ] **Step 1: Refactor `main.py`**
Move CLI parsing and logic delegation to `core/coder.py`. `main.py` should only handle argument parsing and `CoreEngine` initialization.

- [ ] **Step 2: Test basic API call**
```bash
python main.py -p "Hello"
```

- [ ] **Step 3: Commit**
```bash
git commit -m "refactor: centralize orchestration in CoreEngine"
```
