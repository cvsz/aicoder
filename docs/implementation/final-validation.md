# Final Validation Report

## Phase 6.2b primary CLI file prompt

**Status:** Focused slice checks pass. Repository-wide baseline remains tracked
separately and is not represented as production-ready.

| Gate | Command | Result |
|---|---|---|
| Focused format | `black --check zaicoder/main_cli.py tests/test_main_product_api_model_listing.py` | Pass |
| Focused lint | `ruff check zaicoder/main_cli.py tests/test_main_product_api_model_listing.py` | Pass |
| Focused type check | `mypy zaicoder/main_cli.py` | Pass |
| Focused tests | `pytest -q tests/test_main_product_api_model_listing.py` | Pass: 14 tests |
| Main CLI syntax | `python -m py_compile main.py` | Pass |
| Format | `make format` | Pass with the repository toolchain; unrelated legacy formatting output restored from the narrow branch |
| Lint | `make lint` | Baseline red: 910 violations outside this slice |
| Type check | `make typecheck` | Baseline red: missing PyYAML stubs and virtualenv discovery |
| Tests | `make test` | Baseline red: 31 stale TUI API-contract failures; 370 tests pass |

The migrated plain file-prompt path creates a Product API text message with
the legacy fenced file-content format. Streaming file input remains legacy.

## Phase 6.2b primary CLI model info

**Status:** Focused slice checks pass. Repository-wide baseline remains tracked
separately and is not represented as production-ready.

| Gate | Command | Result |
|---|---|---|
| Focused format | `black --check zaicoder/main_cli.py tests/test_main_product_api_model_listing.py` | Pass |
| Focused lint | `ruff check zaicoder/main_cli.py tests/test_main_product_api_model_listing.py` | Pass |
| Focused type check | `mypy zaicoder/main_cli.py` | Pass |
| Focused tests | `pytest -q tests/test_main_product_api_model_listing.py` | Pass: 11 tests |
| Main CLI syntax | `python -m py_compile main.py` | Pass |
| Format | `make format` | Pass with the repository toolchain; unrelated legacy formatting output restored from the narrow branch |
| Lint | `make lint` | Baseline red: 910 violations outside this slice |
| Type check | `make typecheck` | Baseline red: missing PyYAML stubs and virtualenv discovery |
| Tests | `make test` | Baseline red: 31 stale TUI API-contract failures; 367 tests pass |

The default `main.py --model-info` path uses only `ProductAPIClient`; the
explicit `--model-info-legacy` option preserves provider-specific detail lookup
until all legacy catalog fields are represented by the Product API.

## CI Product API HTTP contract recovery

**Status:** Focused slice checks pass. Repository-wide baseline remains red
and is not represented as production-ready.

| Gate | Command | Result |
|---|---|---|
| Focused format | `black --check zaicoder/api/wsgi.py tests/test_product_api_http_openapi.py` | Pass |
| Focused lint | `ruff check zaicoder/api/wsgi.py tests/test_product_api_http_openapi.py` | Pass |
| Focused type check | `mypy zaicoder/api/wsgi.py` | Pass |
| Focused tests | `pytest -q tests/test_product_api_http_openapi.py` | Pass: 4 tests |
| Format | `make format` | Pass with the repository toolchain; unrelated legacy formatting output restored from the narrow branch |
| Lint | `make lint` | Baseline red: 910 violations outside this slice |
| Type check | `make typecheck` | Baseline red: missing PyYAML stubs and virtualenv discovery |
| Tests | `make test` | Baseline red: 31 stale TUI API-contract failures |

This slice restores canonical `X-Request-ID` and `X-Correlation-ID` forwarding
through WSGI and aligns the Product API OpenAPI route contract. No provider
credential or provider SDK is introduced into the CLI.

## Phase 6.2b primary CLI request context

**Status:** Focused slice checks pass. Repository-wide baseline remains red
and is not represented as production-ready.

Focused coverage verifies supplied request/correlation context and token-free
debug diagnostics in the migrated Product API adapter.

Repository gates were executed: `make format` passed (unrelated legacy
formatting was restored), while the established baseline remains red for
lint, type checking, and tests.

## Phase 6.2b primary CLI simple streaming

**Status:** Focused slice checks pass. Repository-wide baseline remains red
and is not represented as production-ready.

| Gate | Command | Result |
|---|---|---|
| Focused format | `black --check zaicoder/main_cli.py tests/test_main_product_api_model_listing.py` | Pass |
| Focused lint | `ruff check zaicoder/main_cli.py tests/test_main_product_api_model_listing.py` | Pass |
| Focused type check | `mypy zaicoder/main_cli.py` | Pass |
| Focused tests | `pytest tests/test_main_product_api_model_listing.py tests/test_product_api_cli.py` | Pass: 17 tests |
| Format | `make format` | Pass; unrelated legacy formatting output restored from the narrow branch |
| Lint | `make lint` | Baseline red: 918 pre-existing violations outside this slice |
| Type check | `make typecheck` | Baseline red: missing PyYAML stub and virtualenv discovery |
| Tests | `make test` | Baseline red: 33 stale Product API/TUI contract failures |

Focused coverage verifies content delta rendering, exactly one final newline,
canonical request context, and Product API-only stream dispatch before legacy
key resolution.

## Phase 6.2b primary CLI simple prompt

**Status:** Focused slice checks pass. Repository-wide baseline remains red
and is not represented as production-ready.

| Gate | Command | Result |
|---|---|---|
| Focused format | `black --check zaicoder/main_cli.py tests/test_main_product_api_model_listing.py` | Pass |
| Focused lint | `ruff check zaicoder/main_cli.py tests/test_main_product_api_model_listing.py` | Pass |
| Focused type check | `mypy zaicoder/main_cli.py` | Pass |
| Focused tests | `pytest tests/test_main_product_api_model_listing.py tests/test_product_api_cli.py` | Pass: 15 tests |
| Format | `make format` | Pass; unrelated legacy formatting output restored from the narrow branch |
| Lint | `make lint` | Baseline red: 918 pre-existing violations outside this slice |
| Type check | `make typecheck` | Baseline red: missing PyYAML stub and virtualenv discovery |
| Tests | `make test` | Baseline red: 33 stale Product API/TUI contract failures |

The focused suite covers canonical request construction, deterministic text
and output-file behavior, request context, and dispatch before legacy key
resolution. It also verifies the migrated adapter stays provider-neutral.

## Phase 6.2b primary CLI model catalog

**Status:** Focused slice checks pass. Repository-wide baseline remains red
and is not represented as production-ready.

| Gate | Command | Result |
|---|---|---|
| Focused format | `black --check zaicoder/main_cli.py tests/test_main_product_api_model_listing.py` | Pass |
| Focused lint | `ruff check zaicoder/main_cli.py tests/test_main_product_api_model_listing.py` | Pass |
| Focused type check | `mypy zaicoder/main_cli.py` | Pass |
| Focused tests | `pytest tests/test_main_product_api_model_listing.py tests/test_product_api_cli.py` | Pass: 13 tests |
| Format | `make format` | Pass; unrelated legacy formatting output restored from the narrow branch |
| Lint | `make lint` | Baseline red: 918 pre-existing violations outside this slice |
| Type check | `make typecheck` | Baseline red: missing PyYAML stub and virtualenv discovery |
| Tests | `make test` | Baseline red: 33 stale Product API/TUI contract failures |

Focused coverage verifies the default `main.py --list-models` dispatch reaches
the Product API before legacy key resolution, preserves tabular output and
request context, and keeps provider credentials and SDK imports out of the
migrated adapter.

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
| Focused tests | Product API CLI/client/stream tests | Pass: 24 tests |

Focused coverage verifies explicit request/correlation IDs for JSON and SSE,
token-free debug output, Product API-only CLI imports, streaming terminal
handling, and exit-code behavior. No live Product API, provider SDK, or
provider credential is required.

Review follow-up coverage verifies typed handling of SSE authentication errors
and validation exit codes for invalid runtime overrides.

The draft PR must not be treated as a repository-wide production readiness
signal until the recorded baseline failures are resolved in dedicated slices.
