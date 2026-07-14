# File Implementation Plan

| Order | Path | Action | Outcome |
|---:|---|---|---|
| 1 | `scripts/repository_inventory.py` | Added | Reproducible static inventory and drift evidence |
| 2 | `tests/test_repository_inventory.py` | Added | Deterministic generator coverage |
| 3 | `docs/implementation/*` | Added | Phase 0 architecture/security/test evidence |
| 4 | `zaicoder/domain/*` | Create | Provider-neutral content, usage, errors, streams, jobs, approvals |
| 5 | `tests/domain/*` | Create | Serialization, redaction, state and terminal-event invariants |
| 6 | `zaicoder/client/*` | Create | Canonical Product API client transport/auth/retry/stream/upload |
| 7 | `tests/client/*` | Create | Fragmentation, retry, timeout, cancellation and redaction |
| 8 | Product API application | Create/refactor | Versioned health/version/models routes and middleware |
| 9 | Provider gateway/adapter | Create/refactor | Server-only Anthropic conversion and credential loading |
| 10 | `main.py`, `tui.py` | Migrate incrementally | Remove provider keys/imports from user-facing clients |
| 11 | File/tool/job modules | Replace boundaries | Authorized storage and sandboxed durable execution |
| 12 | Web frontend/backend | Migrate | Product auth and canonical API/stream consumption |

Each implementation PR must update this table with exact paths once package conventions are established.
