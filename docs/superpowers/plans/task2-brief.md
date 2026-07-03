### Task 2: Import Resolution

**Files:**
- Modify: All files with import statements
- Test: Smoke test by running help command `python main.py --help`

- [ ] **Step 1: Update imports across the project**
(Find/replace script: update `import claude_models` to `import api.claude_models`, `import claude_fable5` to `import agents.claude_fable5`, etc., based on new directory structure.)

- [ ] **Step 2: Smoke test**
```bash
python main.py --help
```
Expected: Help message displays without `ImportError`.

- [ ] **Step 3: Commit**
```bash
git commit -m "refactor: update imports for new structure"
```
