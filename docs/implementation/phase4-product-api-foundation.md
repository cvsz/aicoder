# Phase 4 Product API Foundation

**Status:** Foundation implemented; phase remains in progress.

## Delivered

- framework-independent versioned Product API application boundary;
- `/v1/health`, `/v1/live`, `/v1/ready`, `/v1/version`, and `/v1/models` routes;
- provider-neutral model serialization;
- typed Product API error envelopes;
- request and correlation ID propagation;
- typed high-level client methods for health, readiness, version, and models;
- deterministic in-process end-to-end tests.

## Architectural result

This is the first complete Product API/client vertical slice using the shared Phase 2 domain contracts and Phase 3 transport. No provider SDK or provider credential is present in the public boundary.

## Remaining work

- production HTTP framework adapter and middleware;
- authentication and authorization;
- OpenAPI generation and drift checks;
- dependency-aware readiness probes;
- model catalog service/provider adapter;
- pagination and compatibility negotiation;
- CLI migration for health and model listing.

The repository is not production-ready until those paths and the repository-wide validation matrix pass.
