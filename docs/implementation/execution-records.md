# Migration Execution Records

## 2026-07-15: Phase 6.2b primary CLI simple streaming

- Scope: one complete `main.py --stream -p/--prompt` vertical slice only.
- Delivered: simple stream invocations now use `ProductAPIClient.stream_message()`,
  render Product API content deltas, require exactly one terminal event, and
  return cancellation exit code `130`.
- Compatibility: file, thinking, tools, and other stream-specific legacy
  options remain on their existing provider path until separately migrated.
- Security: the migrated adapter imports no provider SDK and reads no
  provider credential.

## 2026-07-15: Phase 6.2b primary CLI simple prompt

- Scope: one complete `main.py -p/--prompt` vertical slice only.
- Delivered: invocations using only prompt, model, maximum tokens, and output
  now call `ProductAPIClient.create_message()` before legacy provider-key
  resolution and preserve text output-file behavior.
- Compatibility: any prompt invocation using provider-specific or unmigrated
  options remains on its existing legacy path. Streaming, interactive chat,
  files, skills, agents, temperature, and provider-key input are deferred.
- Security: the migrated adapter imports no provider SDK and reads no
  provider credential.

## 2026-07-15: Phase 6.2b primary CLI model catalog

- Scope: one complete `main.py --list-models` vertical slice only.
- Delivered: the default primary CLI model catalog now dispatches to
  `ProductAPIClient.list_models()` before legacy provider-key resolution and
  retains the established human-readable table.
- Architecture: `main.py --list-models` -> `zaicoder.main_cli` ->
  `ProductAPIClient` -> Product API -> server-only provider adapter.
- Compatibility: `--list-models-legacy` continues through the explicitly
  named legacy catalog branch; prompt, streaming, interactive chat, and
  model-info remain deferred to following Phase 6.2b slices.
- Security: the migrated adapter imports no provider SDK and reads no
  provider credential. It uses only Product API runtime configuration.

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
