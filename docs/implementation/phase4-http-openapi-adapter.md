# Phase 4 HTTP Adapter and OpenAPI Validation

**Status:** Implemented as an additive Product API slice; Phase 4 remains in progress.

## Delivered

- standard-library WSGI adapter for the canonical `ProductAPIApplication`;
- HTTP status lines, response headers, and `Content-Length` handling;
- request and correlation ID propagation from HTTP headers;
- deterministic OpenAPI 3.0.3 generator;
- checked-in `docs/api/openapi.json` contract;
- schema-drift test comparing the checked-in contract with runtime generation;
- WSGI tests for successful and typed-error responses.

## Security and compatibility

- the adapter exposes only the versioned Product API routes already implemented;
- provider credentials and provider SDK types are absent from the public boundary;
- request headers are normalized without logging their values;
- typed error envelopes remain unchanged through the HTTP adapter;
- implementation uses the Python standard library and supports Python 3.9+.

## Remaining Phase 4 work

- authentication and authorization middleware;
- dependency-specific readiness contributors;
- production process/server configuration and graceful shutdown;
- richer OpenAPI component schemas and automated generation command;
- pagination and model service integration;
- CLI migration to the Product API;
- resolution of the repository-wide CI baseline failures recorded in Phase 0.
