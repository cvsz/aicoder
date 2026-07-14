# Final Validation Report

## Phase 6.2 Product API CLI operational controls

**Status:** Focused slice checks pass. Repository-wide baseline remains red and
is not represented as production-ready.

| Gate | Command | Result |
|---|---|---|
| Format | `make format` | Pass after excluding local virtual environments |
| Lint | `make lint` | Baseline red: 932 pre-existing violations outside this slice |
| Type check | `make typecheck` | Baseline red: missing PyYAML stub and virtualenv discovery |
| Tests | `make test` | Baseline red: 33 stale TUI/Product API contract failures |
| Focused lint | `ruff check` on changed Python files | Pass |
| Focused type check | `mypy` on changed Product API client files | Pass |
| Focused tests | Product API CLI/client/stream tests | Pass: 22 tests |

Focused coverage verifies explicit request/correlation IDs for JSON and SSE,
token-free debug output, Product API-only CLI imports, streaming terminal
handling, and exit-code behavior. No live Product API, provider SDK, or
provider credential is required.

The draft PR must not be treated as a repository-wide production readiness
signal until the recorded baseline failures are resolved in dedicated slices.
