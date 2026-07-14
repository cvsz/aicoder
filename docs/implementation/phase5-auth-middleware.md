# Phase 5 Product API Authentication Middleware

**Status:** Authentication and route-scope foundation implemented; broader identity phase remains in progress.

## Delivered

- strict bearer-token parsing;
- token validation using SHA-256 digests and constant-time comparison;
- public route allowlist for health, liveness, readiness, and version;
- `models:read` scope requirement for the model catalog;
- typed `401 authentication_required`, `401 invalid_token`, and `403 insufficient_scope` errors;
- `WWW-Authenticate` challenge on authentication failures;
- request and correlation ID preservation;
- WSGI support for authenticated middleware and 401/403 status text;
- deterministic tests with no network or provider credential.

## Security properties

Raw tokens are not persisted by the static validator, returned in errors, or logged. Authentication and authorization failures are non-retryable. Protected routes default to authentication even when no explicit scope is configured.

## Remaining work

- production identity-provider/JWT or opaque-token adapter;
- token expiration and revocation;
- refresh-token rotation;
- organization/workspace policy enforcement;
- actor propagation into application services and audit events;
- OpenAPI security schemes and per-route security declarations;
- authorization tests for future mutating routes.
