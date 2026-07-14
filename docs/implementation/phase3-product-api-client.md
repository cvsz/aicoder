# Phase 3 Product API Client Foundation

**Status:** Foundation implemented; phase remains in progress.

## Delivered

- canonical provider-independent `zaicoder.client` package;
- validated Product API base URL, API version, timeout, retries, and user agent;
- product bearer token, request ID, correlation ID, API-version, and idempotency headers;
- injectable transport for deterministic tests;
- typed Product API error-envelope handling;
- bounded retry policy limited to safe/idempotent operations;
- incremental SSE parsing across partial frames and split UTF-8 sequences;
- malformed and incomplete stream detection.

## Security and compatibility

The client accepts only Product API credentials and imports no provider SDK. It does not log headers or tokens. Existing CLI behavior remains unchanged until individual commands are migrated.

## Validation

`tests/test_product_api_client.py` covers configuration validation, headers, connection retry, non-retryable auth errors, idempotency requirements, typed errors, fragmented UTF-8, multiple events per chunk, malformed JSON, incomplete frames, and canonical terminal-sequence validation.

## Remaining Phase 3 work

- refresh-once authentication flow;
- cancellation token propagation;
- `Retry-After` parsing and bounded jitter source;
- pagination helpers;
- multipart/streaming uploads;
- streaming HTTP response ownership and closure;
- API compatibility negotiation;
- adoption by health/version/model CLI commands and the versioned Product API.

Phase 3 is complete only after the client is used by an end-to-end Product API vertical slice and duplicate raw HTTP logic is removed from migrated commands.
