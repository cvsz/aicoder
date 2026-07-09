# Design Spec: Refactoring zai-coder-cli (v1 -> v2 Pattern)
Date: 2026-07-03

## 1. Goal
- **Modularity:** Reorganize the large collection of `claude_*.py` files into logical groups based on their responsibilities.
- **Centralization:** Simplify `main.py` by delegating core orchestration logic to `coder.py` (the `CoreEngine`).
- **Consistency:** Align configuration management with the v2 layered settings pattern (User/Project/Local precedence).

## 2. Target Structure
The codebase will be reorganized into the following structure:

- `/api/`: Anthropic API communication and low-level data handling.
- `/agents/`: Agent orchestration, subagents, workflows, and specialty model clients.
- `/core/`: Central engine, configuration, basic utilities, and execution runtime.
- `/utils/`: Metrics, token tracking, and observability tools.
- `/main.py`: Lean entry point, CLI argument parsing, delegation to `CoreEngine`.

## 3. Migration Strategy
1. **Phase 1: Structural Setup:** Create directories and move files using `git mv` to preserve history.
2. **Phase 2: Import Resolution:** Update all import statements throughout the codebase to reflect the new structure.
3. **Phase 3: Core Orchestration:** Refactor `main.py` to delegate business logic to `coder.py`'s `CoreEngine`.
4. **Phase 4: Config Modernization:** Implement layered configuration (User/Project/Local) in `config.py`.

## 4. Risks & Mitigations
- **Import Collisions/Errors:** Automated script will be used to verify imports post-move before commit.
- **Breaking Changes:** Maintain existing `main.py` CLI flag signatures to ensure backward compatibility for users.
- **Testing:** Perform smoke tests (`main.py --help`, basic API call) after each phase to ensure no regression.
