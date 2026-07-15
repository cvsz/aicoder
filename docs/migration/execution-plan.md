# ZAI Coder Production Migration Execution Plan

> Dependency-ordered source of truth for migrating ZAI Coder from provider-coupled client surfaces to a production-grade Product API platform.

**Status:** Active  
**Last updated:** 2026-07-15  
**Target branch:** `main` through reviewed pull requests  
**Strategic source:** [`../../ROADMAP.md`](../../ROADMAP.md)

---

## 1. Operating Rules

A phase or vertical slice is complete only when production code is connected end-to-end, relevant failure paths are tested, focused validation passes, API documentation matches runtime behavior, and evidence is recorded.

1. Work on dependency-scoped branches.
2. Do not push implementation directly to `main`.
3. Prefer one architectural outcome per pull request.
4. Keep provider credentials server-side.
5. Do not report repository-wide production readiness while baseline CI remains red.
6. Do not weaken tests, lint, typing, or security checks to manufacture a pass.
7. Update this plan after every merged vertical slice.

---

## 2. Target Architecture

```text
CLI / TUI / Web / Automation
            |
            v
Canonical Typed Product API Client
            |
            v
Versioned Product API
            |
 Authentication -> Authorization -> Validation
            |
            v
Application Services
     |          |          |
     v          v          v
Persistence  Provider   Jobs/Tools
                |
                v
       Server-only Adapters
```

### Architectural invariants

1. CLI and browser code import no provider SDK.
2. CLI and browser configuration contains no provider credential.
3. All user-facing clients use the canonical Product API client.
4. Provider-specific code remains behind server-only adapters.
5. API errors are typed and preserve request/correlation IDs.
6. Every stream reaches exactly one terminal event.
7. Cancellation propagates through all active layers.
8. Every mutating operation is authenticated, authorized, and auditable.
9. Tenant-owned records are scoped by actor, organization, and workspace.
10. OpenAPI and runtime behavior remain synchronized.
11. Secrets are redacted from errors, logs, traces, metrics, and audit events.
12. Dangerous tools default to denied and execute within enforceable policy.

---

## 3. Current Verified State

### Merged foundations

- Repository inventory tooling and implementation artifacts.
- TUI streaming reliability and unconditional final flush.
- Provider-neutral content, message, usage, error, model, pagination, job, approval, and stream contracts.
- Canonical Product API JSON transport, retry classification, typed errors, and SSE parser.
- Versioned Product API health, readiness, version, model, message, and stream routes.
- WSGI adapter and checked-in OpenAPI drift guard.
- Bearer authentication and route-scope authorization foundation.
- Server-only provider model gateway and Anthropic model adapter.
- Provider-neutral generation service and canonical terminal stream events.
- Anthropic generation stream adapter with injected SDK boundary.
- Incremental Product API stream client with resource closure.
- TUI chat migration to `ProductAPIClient` for streaming and non-streaming paths.

### Still incomplete

- Important plain argparse CLI generation paths remain provider-coupled.
- Product API client refresh, uploads, pagination, and production transport are incomplete.
- Product API server streaming is not yet a production incremental ASGI path.
- Conversation/message persistence is not implemented end-to-end.
- Tool grants, approvals, sandbox workers, durable jobs, and audit events are incomplete.
- Organization/workspace authorization is incomplete.
- Web and automation surfaces are not fully migrated.
- Observability, rate limiting, quotas, deployment, and rollback gates remain incomplete.
- Repository-wide CI baseline is not yet proven green.

---

## 4. Progress Dashboard

| Phase | Status | Remaining gate |
|---|---|---|
| 0. Baseline and drift control | Partial | CI baseline remains red |
| 1. TUI streaming reliability | Complete slice | Continue regression coverage |
| 2. Shared domain contracts | Foundation complete | Persistence/tool adoption remains |
| 3. Typed Product API client | Partial | Refresh/uploads/pagination pending |
| 4. Versioned Product API | Partial | Production server/runtime pending |
| 5. Provider gateway/generation | Partial | Production construction and tools pending |
| 6. Client-surface migration | In progress | TUI merged; plain CLI is next |
| 7. Conversations/persistence | Pending | Durable store and migrations |
| 8. Files/attachments | Pending | Secure storage lifecycle |
| 9. Tools/approvals/jobs | Pending | Execution boundary and audit |
| 10. Identity/tenancy | Partial | Static bearer auth only |
| 11. Web migration | Pending | Canonical client adoption |
| 12. Usage/audit/observability | Pending | Cross-layer telemetry |
| 13. CI/supply chain | Pending | All required checks green |
| 14. Deployment/release | Pending | Production and rollback validation |

---

# Phase 6.2 — Product API CLI Foundation

**Status:** Partial; API-native console entrypoint, operational controls, the
primary CLI model catalog/detail paths, and simple prompt path are delivered.
**Remaining gate:** converge the primary `main.py` prompt/chat paths without
reintroducing provider credentials to migrated commands.

## Objective

Migrate primary argparse CLI generation/chat paths from direct `Coder`, provider SDK, provider HTTP, and provider-key usage to the canonical `ProductAPIClient`.

## Required execution path

```text
argparse command
-> CLI command/service layer
-> ProductAPIClient
-> Product API
-> generation application service
-> server-only provider adapter
```

## Tasks

### 6.2.1 Trace and classify

1. Trace all generation-related argparse flags and branches in `main.py`.
2. Identify calls to `Coder`, direct `anthropic` clients, provider endpoints, and `ANTHROPIC_API_KEY`.
3. Classify each path as migrate now, explicit temporary legacy mode, server-only, or dead/duplicated.
4. Record compatibility behavior before editing.

### 6.2.2 Canonical CLI runtime

The delivered API-native CLI runtime:

- constructs `ProductAPIClient` from `ZAICODER_API_URL` and `ZAICODER_ACCESS_TOKEN`;
- supports API version, timeout, retry count, request IDs, and correlation IDs;
- exposes streaming and non-streaming generation;
- accepts no provider credential;
- centralizes typed error-to-exit-code mapping;
- redacts tokens from diagnostics.

### Remaining 6.2.3 Command migration

Migrate applicable paths:

- one-shot prompt/generate; **partially delivered:** simple `-p/--prompt`
  invocations with only model, maximum tokens, output, and plain `-f/--file`
  input use `ProductAPIClient`; provider-specific and richer prompt modes
  remain legacy;
- interactive chat;
- streaming output; **partially delivered:** simple `--stream -p/--prompt`
  invocations with only model and maximum tokens use `ProductAPIClient`;
  file, thinking, tools, and richer stream modes remain legacy;
- continuation/history input where currently supported;
- model listing exposed by the main CLI; **delivered:** `--list-models` now
  uses `ProductAPIClient`; `--list-models-legacy` remains the explicitly
  named temporary legacy catalog path. **Delivered:** `--model-info` now uses
  the typed Product API catalog; `--model-info-legacy` retains the prior
  provider-specific detail output until its additional fields are available;
- JSON output;
- quiet and debug modes.

No migrated command may instantiate `Coder`, import a provider SDK, or call a provider endpoint directly.

### Delivered 6.2.4 Streaming and cancellation

The CLI stream path must:

- consume canonical Product API events;
- render `content.delta` text;
- expose terminal failure codes safely;
- flush final output unconditionally;
- close network resources;
- convert Ctrl+C into cancellation intent;
- return exit code `130` on cancellation;
- avoid duplicate terminal output.

### Delivered 6.2.5 Standard exit codes

| Condition | Exit code |
|---|---:|
| Success | 0 |
| Usage or validation error | 2 |
| Authentication failure | 3 |
| Authorization failure | 4 |
| Provider/API unavailable | 5 |
| Timeout or transport failure | 6 |
| Protocol or malformed response | 7 |
| User cancellation | 130 |

### Delivered 6.2.6 Tests

Add deterministic tests without provider SDK, provider credential, network, or live Product API:

- non-streaming prompt success;
- streaming text and final flush;
- JSON output;
- missing Product API configuration;
- typed authentication and authorization failures;
- retryable provider/API failure;
- malformed response/event;
- timeout;
- cancellation and exit `130`;
- token redaction;
- source inspection proving migrated paths contain no provider SDK import or provider-key read.

### 6.2.7 Documentation

Update:

- `docs/cli/reference.md`;
- environment-variable examples;
- `docs/implementation/change-log.md`;
- `docs/implementation/final-validation.md`;
- this execution plan.

## Acceptance criteria

The slice is complete only when:

1. primary plain CLI prompt/chat paths use `ProductAPIClient`;
2. migrated paths contain no provider SDK import, direct provider HTTP call, or `Coder` construction;
3. migrated paths do not read `ANTHROPIC_API_KEY`;
4. streaming and non-streaming use the same canonical client abstraction;
5. JSON and text output are deterministic;
6. cancellation and exit codes are tested;
7. focused formatter, lint, type, and tests pass;
8. no new repository-wide failure is introduced;
9. compatibility and deferred legacy paths are documented.

## Rollback

Revert the CLI migration commits while retaining Product API client/server foundations. Any temporary legacy path must be explicit, disabled by default, documented, and scheduled for removal. Do not restore provider credentials to new client configuration.

---

# NEXT ACTIVE SLICE — Phase 6.2b Primary CLI Convergence

**Priority:** P0
**Recommended branch:** `feat/phase6-main-cli-convergence`

Migrate the primary `main.py` prompt, streaming, interactive, and model-list branches to `ProductAPIClient`. Retain only explicitly documented legacy provider administration paths until equivalent Product API endpoints exist. This is the next vertical slice; do not combine it with web or automation migration.

---

# Phase 6.3 — Remaining Client-Surface Migration

After Phase 6.2:

1. Replace TUI static/local model selection with `/v1/models` where appropriate.
2. Migrate web backend/frontend generation paths.
3. Migrate automation and scripting entry points.
4. Remove or isolate remaining client-facing provider imports.
5. Add a CI invariant rejecting provider SDK imports and provider-key reads in client surfaces.

Acceptance gate: CLI, TUI, web, and automation use Product API boundaries only.

---

# Phase 7 — Conversations and Persistence

Implement conversation/message repositories, durable stream state, usage/model metadata, CRUD/continue endpoints, transaction boundaries, optimistic concurrency, organization/workspace scoping, and clean migration/upgrade tests.

Acceptance gate: a conversation survives process restart and resumes without duplicate messages.

---

# Phase 8 — Files and Attachments

Implement multipart/streaming upload, size/MIME validation, filename sanitization, hashes, object-storage abstraction, authorized downloads, extraction boundaries, cleanup, and malware-scanning integration.

Acceptance gate: uploads are tenant-scoped, validated, auditable, and usable without exposing storage credentials.

---

# Phase 9 — Tools, Approvals, and Durable Jobs

Implement canonical tool schemas, grants, workspace policy, approval expiry/revocation, durable job store/queue, sandboxed workers, cancellation, idempotent retry, crash recovery, structured results, and mandatory audit events.

Acceptance gate: a mutating tool cannot execute without authorization, grant, valid approval, resource policy, and audit evidence.

---

# Phase 10 — Identity and Multi-tenancy

Implement access-token expiry, refresh rotation, revocation persistence, identity-provider integration, actor/org/workspace propagation, RBAC or policy authorization, isolation tests, and token/session audit events.

Acceptance gate: tenant isolation and authorization failure paths pass integration tests.

---

# Phase 11 — Usage, Audit, and Observability

Implement structured redacted logs, request/correlation/trace IDs, API/provider latency, token/rate-limit metrics, active stream/job gauges, audit schemas/export, dashboards, alerting, and retention policy.

Acceptance gate: every protected mutation/tool execution is auditable and failures are diagnosable without exposing secrets.

---

# Phase 12 — CI, Supply Chain, Deployment, and Release

Required gates:

1. clean dependency install;
2. formatter, lint, and type checking;
3. unit, integration, security, and end-to-end tests;
4. OpenAPI drift check;
5. database migration from empty and previous versions;
6. package and container builds;
7. non-root container execution;
8. health/readiness/startup smoke tests;
9. secret and dependency scanning;
10. provenance/SBOM where supported;
11. deployment and rollback runbooks.

Acceptance gate: all required checks are green on the release commit.

---

## Final Production Completion Gate

The repository is production-ready only when:

- CLI, TUI, web, and automation use Product API boundaries only;
- provider credentials exist only in server-side secret configuration;
- streaming and cancellation work end-to-end;
- conversations, files, approvals, jobs, usage, and audit are durable;
- authentication, authorization, and tenant isolation pass tests;
- OpenAPI matches runtime behavior;
- database migrations and rollback are validated;
- containers build and run as non-root with health checks;
- CI, security scans, and end-to-end smoke tests pass;
- documentation matches the delivered release.

Until every gate is satisfied, report the repository as **not production-ready**.
