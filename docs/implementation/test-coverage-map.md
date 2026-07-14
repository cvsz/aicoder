# Test Coverage Map

| Area | Existing evidence | Missing production-grade coverage |
|---|---|---|
| CLI wiring | Argparse/dispatch tests exist | Generated full execution-path inventory and compatibility aliases |
| Provider calls | Mocked feature tests | Provider-neutral adapter contract and normalized failures |
| Streaming | TUI and stream tests | Fragmented Product API frames, cancellation, exactly one terminal event |
| Files | Feature tests | MIME/content mismatch, traversal, symlink escape, lifecycle authorization |
| Tools | Agent/tool tests | Approval expiry, grants, resource limits, worker crash/cancel/retry |
| Web backend | Route-oriented tests | Authn/authz, CORS, rate limits, typed errors, OpenAPI drift |
| Persistence | Local/session tests | Durable transactions, concurrency, restart recovery, tenant isolation |
| Security | Unit-level helpers/scans | End-to-end negative tests at every external boundary |
| Packaging | CI/build jobs | Current jobs are skipped because lint/security/tests fail |

## Deterministic baseline

`scripts/repository_inventory.py` and `tests/test_repository_inventory.py` require only the standard library. They validate inventory generation without importing provider SDKs or requiring network credentials.

## Collection accounting

Test counts must come from `pytest --collect-only -q`, not raw `def test_` counts, because parametrized tests expand into multiple cases.

## Release gate

A new slice must pass focused tests and must not worsen the repository-wide baseline. Existing failures must be listed separately from newly introduced failures.
