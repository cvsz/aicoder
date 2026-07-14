# Phase 4 Authentication and Authorization Middleware

**Status:** Implemented as a deterministic Product API boundary slice; production identity integration remains pending.

## Delivered

- bearer-token parsing with constant-time token comparison;
- inactive and unknown tokens treated identically;
- explicit public-route policy for health, liveness, readiness, and version;
- protected model catalog requiring `models:read`;
- typed `401 unauthenticated` and `403 forbidden` error envelopes;
- `WWW-Authenticate` challenge on authentication failure;
- request/correlation ID preservation through rejected requests;
- OpenAPI bearer scheme and protected-route security metadata;
- deterministic tests requiring no network, provider SDK, or credential.

## Security properties

- provider credentials are not accepted at this boundary;
- access tokens are never serialized or logged;
- authentication and authorization failures are non-retryable;
- responses do not reveal whether a submitted token is inactive or unknown;
- authorization failures expose required scopes, not the caller's granted scopes.

## Remaining work

- production identity-provider/JWT or opaque-token introspection adapter;
- token expiration, refresh rotation, revocation persistence, and key rotation;
- organization/workspace policy enforcement;
- authenticated principal propagation into application services and audit events;
- rate limiting and abuse controls;
- repository-wide CI baseline remediation.
