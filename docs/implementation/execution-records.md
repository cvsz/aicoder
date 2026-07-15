# Migration Execution Records

## 2026-07-15: Phase 6.2 Product API CLI operational controls

- Scope: one API-native CLI vertical slice only.
- Delivered: CLI overrides for API version, timeout, and retry count;
  explicit request/correlation IDs for JSON and SSE; token-free debug output.
- Architecture: `zai-coder-api` -> `ProductAPIClient` -> Product API ->
  server-only provider adapter.
- Compatibility: existing environment configuration and default request ID
  generation remain unchanged. No legacy `main.py` path was altered.
- Security: no provider SDK or provider credential was added to the CLI.
- Deferred: primary legacy CLI convergence remains the next active slice.

## 2026-07-15: Phase 6.2 review follow-up

- Mapped Product API SSE `HTTPError` responses with valid error envelopes to
  `ProductAPIError`, preserving typed CLI exit-code behavior.
- Added validation for non-positive `--api-timeout` and negative
  `--api-max-retries` values before client construction.
