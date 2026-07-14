# Phase 6.2 Product API CLI

**Status:** Product API-native console entrypoint implemented; legacy `main.py` convergence remains pending.

## Delivered

- `zai-coder-api` console script;
- Product API runtime configuration through the canonical client builder;
- one-shot generation;
- canonical streaming event rendering;
- model catalog listing;
- JSON and quiet output modes;
- stable exit-code mapping;
- cancellation exit code `130`;
- CLI overrides for Product API version, timeout, and retry policy;
- explicit request and correlation ID propagation for JSON and stream calls;
- token-free debug diagnostics;
- deterministic tests without provider SDK, provider credentials, or network.

## Exit codes

| Condition | Code |
|---|---:|
| success | 0 |
| validation/configuration | 2 |
| unauthenticated | 3 |
| forbidden | 4 |
| unavailable/retryable stream failure | 5 |
| timeout | 6 |
| protocol/non-retryable stream failure | 7 |
| cancelled / Ctrl+C | 130 |

## Security properties

- the CLI accepts only Product API configuration;
- provider credentials are not read or forwarded;
- no provider SDK or `Coder` dependency exists in `zaicoder/cli.py`;
- Product API errors are rendered without token values.

## Remaining gate

The legacy multi-feature `main.py` still owns many provider-specific commands. A follow-up convergence slice must route its primary prompt, stream, interactive, and model-list branches to this runtime while retaining explicitly classified legacy provider administration commands until matching Product API endpoints exist.
