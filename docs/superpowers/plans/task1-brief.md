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
