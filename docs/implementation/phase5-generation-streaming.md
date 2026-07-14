# Phase 5 Provider-Neutral Generation and Streaming

**Status:** Server-side generation and canonical streaming boundary implemented; live incremental HTTP client adoption remains pending.

## Delivered

- provider-neutral `GenerationRequest`, `ProviderDelta`, and `GenerationProvider` contracts;
- cancellation signal and mutable cancellation token;
- canonical generation service producing monotonic Product API stream events;
- exactly-one-terminal-event enforcement;
- `POST /v1/messages` non-streaming generation;
- `POST /v1/messages:stream` canonical SSE serialization;
- `messages:write` authorization policy;
- WSGI request-body forwarding and 422/502 status support;
- OpenAPI request, response, security, and stream declarations;
- deterministic tests without provider SDK, credentials, or network.

## Reliability and security

- cancellation becomes `stream.cancelled`;
- provider failures become `stream.failed` with normalized codes;
- unexpected provider exceptions are replaced with a generic retryable failure;
- a provider stream ending without completion becomes a non-retryable invalid-response failure;
- provider credentials and raw exceptions are not exposed through the public contract;
- request and correlation IDs are present on every stream event.

## Remaining work

- production Anthropic streaming SDK mapping;
- true incremental WSGI/ASGI response resource ownership rather than buffered SSE serialization;
- typed client streaming method and Ctrl+C cancellation propagation;
- conversation/message persistence and partial-state recovery;
- tool-use and tool-result stream mapping;
- rate-limit metadata, observability, and audit events;
- CLI and TUI migration away from direct provider SDK calls;
- repository-wide CI baseline remediation.
