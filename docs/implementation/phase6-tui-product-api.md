# Phase 6 TUI Product API Migration

**Status:** TUI chat and streaming paths migrated to the canonical Product API client.

## Delivered

- TUI no longer imports the Anthropic SDK;
- TUI no longer reads or requires `ANTHROPIC_API_KEY`;
- non-streaming generation uses `ProductAPIClient.create_message()`;
- streaming generation uses `ProductAPIClient.stream_message()`;
- runtime configuration uses `ZAICODER_API_URL`, `ZAICODER_ACCESS_TOKEN`, `ZAICODER_API_VERSION`, timeout, and retry settings;
- provider credentials remain server-side;
- the legacy `run_tui(api_key=...)` signature remains callable but intentionally discards the provider key;
- stream rendering retains bounded updates and unconditional final flush;
- deterministic static and configuration tests require no provider SDK, credential, network, or Textual runtime.

## Security and architecture

The TUI now crosses only the Product API boundary. Product bearer tokens are accepted solely by the typed transport. Provider-specific types, provider SDK construction, and provider secrets are absent from `tui.py`.

## Remaining work

- migrate the plain argparse CLI chat/generation paths;
- load model choices from `/v1/models` instead of the legacy local catalog;
- propagate Ctrl+C into the live stream cancellation signal and interrupt blocking reads;
- add conversation persistence and session restoration through Product API endpoints;
- migrate web client paths;
- complete organization/workspace authorization, audit, and observability;
- remediate repository-wide CI baseline failures.
