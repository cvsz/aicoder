# Phase 5 Provider Gateway and Model Catalog

**Status:** Server-only provider gateway foundation implemented; generation and streaming adoption remain pending.

## Delivered

- provider-neutral `ModelProvider` protocol;
- normalized provider error codes and retryability;
- server-only Anthropic model adapter with injected SDK/network boundary;
- provider-neutral model catalog application service;
- `/v1/models` integration through the application service;
- duplicate model-id validation and deterministic ordering;
- provider timeout, authentication, and malformed-response normalization;
- dynamic API-version routing rather than a hard-coded `/v1` prefix;
- deterministic tests requiring no provider SDK, credential, or network.

## Security properties

- provider credentials remain outside CLI, client, domain, and public API contracts;
- raw provider exceptions and credential details are not returned;
- provider authentication failures are non-retryable;
- transient provider failures are retryable typed errors;
- public model descriptors expose only canonical capability metadata.

## Remaining work

- production Anthropic SDK factory and secret-manager integration;
- provider-backed message generation and streaming;
- cancellation and timeout propagation;
- provider rate-limit metadata and bounded retries;
- provider readiness checks and observability;
- CLI/TUI migration to Product API chat and model routes;
- repository-wide CI baseline remediation.
