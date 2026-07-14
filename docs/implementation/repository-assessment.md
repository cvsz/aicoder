# Repository Assessment

**Baseline ref:** `docs/production-roadmap-execution-plan`  
**Assessment date:** 2026-07-15  
**Status:** Phase 0 evidence; not a production-readiness declaration

## Executive assessment

ZAI Coder is currently a broad Python CLI and optional TUI/web surface that exposes many Anthropic-oriented capabilities. The current code is provider-coupled: client-facing modules read provider credentials and multiple modules import provider SDKs directly. The lightweight web backend is not yet the canonical Product API described by the target architecture.

The next migration dependency is a provider-neutral contract plus one typed Product API client. Moving commands individually before those foundations exist would create a second fragmented transport layer.

## Verified entry surfaces

| Surface | Current role | Migration status |
|---|---|---|
| `main.py` | Primary argparse CLI and dispatch chain | Provider-coupled |
| `coder.py` | Core synchronous provider request facade | Provider-specific |
| `tui.py` | Interactive terminal UI | Streaming reliability improved; still provider-mediated locally |
| `webapp/backend/server.py` | Lightweight web backend | Not canonical Product API |
| `claude_*.py` | Feature-specific command/provider modules | Mixed transport and business logic |
| `.github/workflows/*` | CI/build automation | Baseline currently failing |

## Packaging and runtime

- Language: Python, with a small static web frontend.
- Package/build metadata: `pyproject.toml`, requirements files, Docker/build scripts.
- Supported CI Python matrix observed: 3.9–3.12.
- Current source version and historical documentation metadata have drifted in prior revisions.
- Repository-wide analysis must avoid importing provider SDKs; `scripts/repository_inventory.py` provides that path.

## Current architectural flow

```text
CLI / TUI / web backend
  -> feature module or Coder
  -> provider SDK / provider HTTP API
  -> local output and local state
```

Target flow:

```text
CLI / TUI / web
  -> typed Product API client
  -> versioned Product API
  -> authn/authz/validation
  -> application service
  -> provider adapter / repository / worker
```

## Baseline CI evidence

PR workflow run `29365716292` failed in:

- Ruff lint
- Bandit security scan
- Pytest on Python 3.9, 3.10, 3.11, and 3.12

Build jobs were skipped because their dependencies failed. These failures existed on the documentation merge ref and must be classified before Phase 0 can be marked complete. Documentation-only changes are not evidence that the repository is green.

## Principal gaps

1. No canonical provider-neutral domain contract.
2. No single typed Product API client.
3. Provider credentials remain in client-facing configuration paths.
4. Provider SDK imports remain distributed across feature modules.
5. API routes, business rules, and provider conversion are not cleanly separated.
6. Tool/filesystem/shell policy requires enforceable default-deny controls.
7. Documentation and source version claims require automated drift checks.
8. CI baseline failures prevent reliable regression attribution.

## Phase 0 commands

```bash
python scripts/repository_inventory.py --root . --output build/repository-inventory.json --check
python -m compileall -q .
python -m ruff check .
python -m black --check .
python -m mypy .
python -m pytest -ra
python -m pytest --collect-only -q
python -m build
```

Results must be recorded without converting failures into ignores or weaker assertions.
