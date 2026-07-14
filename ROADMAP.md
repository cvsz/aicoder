# ZAI Coder Roadmap

> Strategic roadmap for evolving ZAI Coder from a provider-coupled local CLI into a production-grade, API-mediated coding platform.

**Repository:** `cvsz/aicoder`  
**Document status:** Active source of truth  
**Last updated:** 2026-07-15  
**Source baseline verified:** `main.py` reports `v1.22.0` on the current `main` branch  
**Execution details:** [`docs/migration/execution-plan.md`](docs/migration/execution-plan.md)

---

## 1. Purpose

This document defines product direction, architectural outcomes, release priorities, production-readiness criteria, and long-term milestones.

It intentionally does not duplicate detailed implementation tasks. File-level sequencing, acceptance tests, rollback requirements, and phase gates belong in `docs/migration/execution-plan.md`.

The roadmap distinguishes three states:

- **Verified complete** — implemented in the repository and supported by relevant tests or build evidence.
- **In progress** — implementation exists but one or more production gates remain open.
- **Planned** — approved direction with no claim of completion.

No feature may be marked complete solely because a module, CLI flag, test stub, or document exists.

---

## 2. Product Vision

ZAI Coder will provide one secure and consistent experience across CLI, TUI, web, automation, and API clients.

The target request path is:

```text
CLI / TUI / Web / Automation
            |
            v
Canonical Typed Product API Client
            |
            v
Versioned Product API
            |
            v
Authentication -> Authorization -> Validation
            |
            v
Application Services
            |
            +--> Conversation and Job Persistence
            +--> Tool Policy and Approval Engine
            +--> Audit and Observability
            |
            v
Provider-Neutral Model Gateway
            |
            v
Anthropic and Future Provider Adapters
```

Provider credentials remain server-side. User-facing clients receive product credentials and product-domain responses, not raw provider credentials or provider SDK objects.

---

## 3. Guiding Principles

1. **Product API first** — every user-facing client uses the same versioned API contract.
2. **Provider isolation** — provider-specific SDKs and schemas remain behind adapters.
3. **Secure by default** — dangerous tool access is denied unless explicitly granted.
4. **Tenant-aware ownership** — every durable record has explicit actor, organization, and workspace ownership where multi-user operation is enabled.
5. **Contract-driven implementation** — runtime behavior, OpenAPI, typed clients, and tests remain synchronized.
6. **Deterministic failure semantics** — retries, cancellation, idempotency, and terminal stream states are explicit.
7. **Observable operation** — logs, metrics, traces, request IDs, audit events, and redaction are built in.
8. **Evidence-based completion** — production readiness requires command output and test evidence.
9. **Backward compatibility by policy** — breaking changes require migration notes and a supported transition window.
10. **One canonical abstraction per concern** — no duplicate HTTP clients, retry implementations, auth flows, or security validators.

---

## 4. Verified Current State

The repository currently provides a broad local CLI and supporting modules for model interaction, streaming, tools, agent workflows, files, document generation, administration, compliance, evaluation, observability, TUI, and a lightweight web application.

The current source remains primarily a direct-provider application:

- CLI modules can load provider credentials.
- Multiple modules import or invoke provider-specific behavior directly.
- The TUI and web backend are not yet fully mediated by a canonical product API.
- API, authentication, persistence, approval, and tenant boundaries are not yet one cohesive production platform boundary.

This is a valid local-tool architecture, but it does not yet satisfy the target hosted-platform architecture.

### 4.1 Existing strengths

- Large CLI feature surface with established commands and documentation.
- Provider functionality covering messages, streaming, files, tools, batches, model metadata, administration, compliance, and agent workflows.
- Retry and resilience utilities.
- Cross-platform packaging and Windows build support.
- Test coverage across many modules.
- TUI streaming reliability work with bounded rendering and final flush behavior.
- Native document-generation capabilities.
- Security utility modules and sandbox concepts that can be consolidated into enforceable product policies.

### 4.2 Principal architectural gaps

- No single canonical product API client used by all clients.
- Provider SDK and provider credential coupling remains in client-facing code.
- No unified provider-neutral domain model.
- No complete product authentication and refresh-token lifecycle.
- Authorization and ownership boundaries are not consistently enforced across durable resources.
- Tool permission modes are not yet a complete policy/state machine.
- Local filesystem and shell tools require stronger default isolation and approval controls.
- OpenAPI is not yet the canonical runtime contract.
- Audit events, request correlation, metrics, and tracing are not yet end-to-end.
- Documentation version and inventory drift must be continuously detected.

---

## 5. Production Readiness Dashboard

| Area | Status | Target outcome |
|---|---|---|
| CLI command coverage | In progress | All supported commands use one typed product API client |
| TUI streaming | Verified complete for reliability slice | Product-API streaming, cancellation, terminal event guarantees |
| Web frontend | In progress | Authenticated, CSP-hardened, reconnectable streaming client |
| Product API | Planned | Versioned API with typed errors, OpenAPI, health, readiness, and idempotency |
| Authentication | Planned | Product tokens, refresh rotation, revocation, secure local storage |
| Authorization | Planned | Explicit actor/org/workspace policy enforcement |
| Provider abstraction | Planned | Provider-neutral domain and adapter interfaces |
| Conversations | Planned | Durable scoped conversations, messages, attachments, usage |
| Files | In progress | Authorized upload/download, validation, object storage, lifecycle |
| Tool execution | In progress | Grants, approvals, isolation, resource limits, cancellation, audit |
| Jobs and queues | Planned | Durable idempotent jobs with recovery and valid state transitions |
| Security | In progress | Central validators integrated into every sensitive path |
| Observability | In progress | Structured logs plus metrics, traces, and correlated audit events |
| Testing | In progress | Unit, contract, integration, security, migration, and E2E gates |
| CI/CD | In progress | Reproducible builds, schema drift, migration, image, and smoke gates |
| Deployment | In progress | Hardened containers, managed secrets, rollback and backup procedures |
| Documentation | In progress | Generated inventories and continuously verified implementation records |

---

## 6. Completed Milestones

These milestones are retained as delivered product capabilities. Their presence does not imply completion of the platform migration.

### 6.1 Core CLI evolution

- Broad Anthropic API and product-feature command surface.
- Model catalog and capability metadata.
- Interactive and non-interactive workflows.
- Files, tools, streaming, batches, structured output, thinking, caching, administration, compliance, evaluations, and agent workflows.

### 6.2 Cross-platform delivery

- Windows executable and installer build infrastructure.
- Linux executable build path.
- Container build support.
- CI foundations for testing and packaging.

### 6.3 Native artifacts and documents

- Spreadsheet and presentation workflows.
- Native DOCX and PDF workflows in later release snapshots.
- Artifact and project abstractions for local operation.

### 6.4 TUI streaming reliability

- Bounded render cadence.
- Immediate first-delta display.
- Threshold-based coalescing.
- Unconditional final partial-response flush.
- Deterministic framework-independent streaming tests.

---

## 7. Strategic Workstreams

## 7.1 Canonical Product API Client

**Priority:** P0  
**Outcome:** CLI, TUI, web, and automation clients share one typed client library.

Required capabilities:

- Product authentication and token refresh.
- Base URL and API-version negotiation.
- Request and correlation IDs.
- Idempotency keys.
- Safe bounded retries with jitter.
- Timeouts and cancellation.
- Pagination.
- Multipart and streaming upload.
- SSE or equivalent streaming protocol.
- Typed product errors.
- User-agent and client-version metadata.
- Debug logging with secret redaction.

Completion requires removal of duplicated raw HTTP logic from client-facing commands.

## 7.2 Provider-Neutral Domain and Adapters

**Priority:** P0  
**Outcome:** application services do not depend on provider SDK types.

Domain types include:

- Model and capability metadata.
- Conversation and message content blocks.
- Tool calls and tool results.
- Stream events and terminal states.
- Usage and stop reasons.
- Provider errors and retry metadata.

The Anthropic implementation becomes the first adapter. Additional providers can be added without modifying CLI or core application logic.

## 7.3 Versioned Product API

**Priority:** P0  
**Outcome:** one stable server boundary for every product surface.

Initial API domains:

- health, liveness, readiness, and version;
- auth and sessions;
- users, organizations, and workspaces;
- model catalog and capabilities;
- conversations and messages;
- streaming generation;
- files and attachments;
- tools, grants, and approvals;
- jobs, events, cancellation, and retry;
- usage and audit.

OpenAPI must be generated or validated against runtime schemas in CI.

## 7.4 CLI and TUI Migration

**Priority:** P0  
**Outcome:** no provider SDK or provider secret is required on the client.

Migration will proceed in vertical slices:

1. model catalog and health;
2. non-streaming prompt execution;
3. streaming chat and cancellation;
4. conversation continuity;
5. files and attachments;
6. tools and approvals;
7. asynchronous jobs;
8. administration and usage.

Compatibility aliases may remain temporarily, but all active paths must converge on the typed product API client.

## 7.5 Authentication and Authorization

**Priority:** P0  
**Outcome:** explicit product identity, scoped access, and revocation.

- Secure login and logout.
- Short-lived access tokens.
- Rotating refresh tokens.
- Revocation and session inventory.
- Secure OS credential storage for CLI clients.
- Role- or policy-based access control.
- Organization and workspace isolation.
- Authorization on every mutating operation.
- Audit records for auth and policy decisions.

## 7.6 Conversations, Persistence, and Jobs

**Priority:** P1  
**Outcome:** durable, recoverable workflows.

- Scoped conversation and message storage.
- Partial, final, failed, and cancelled message states.
- Attachment metadata and lifecycle.
- Durable job queue.
- Validated job state machine.
- Idempotent submission and retry.
- Cancellation propagation.
- Worker recovery after process restart.
- Transactional state transitions.

## 7.7 Tool Policy, Approval, and Sandbox

**Priority:** P0  
**Outcome:** tools cannot execute outside explicit policy.

Every tool execution must validate:

- registry membership and schema;
- user authorization;
- workspace policy;
- explicit grants;
- approval requirement and expiry;
- filesystem, network, and command policy;
- CPU, memory, timeout, and output limits.

Default policy is deny. File and shell operations require path containment, symlink handling, command policy, cancellation, redaction, and auditable outcomes.

## 7.8 Files and Attachments

**Priority:** P1  
**Outcome:** secure authorized file lifecycle.

- Multipart and streaming upload.
- Configurable size limits through one canonical validator.
- MIME and extension validation.
- Filename sanitization.
- Content hashing and optional deduplication.
- Authorized object storage.
- Signed download URLs where appropriate.
- Text extraction and supported document processing.
- Malware-scanning integration boundary.
- Retention and cleanup policies.

## 7.9 Web Frontend

**Priority:** P1  
**Outcome:** production browser client using the same product API.

- Shared API contract and generated types.
- Secure authentication flow.
- No provider secrets in browser state or bundles.
- CSP and safe rendering.
- CSRF strategy where cookies are used.
- Streaming reconnect and cancellation.
- File-upload progress and validation.
- Accessible keyboard and screen-reader behavior.
- Explicit loading, failure, retry, and terminal states.
- Frontend unit and browser E2E tests.

## 7.10 Security Hardening

**Priority:** P0  
**Outcome:** centralized controls are enforced, not merely defined.

- Integrate path, URL, identifier, secret, and file-size validators.
- Remove duplicated conflicting limits.
- Eliminate unsafe default shell execution.
- Enforce explicit approval semantics for every permission mode.
- Redact credentials and sensitive provider payloads.
- Apply rate limits and abuse controls.
- Protect against SSRF, path traversal, command injection, and malicious uploads.
- Use non-root containers and least-privilege runtime identities.
- Add dependency, secret, and container scanning.

## 7.11 Observability and Audit

**Priority:** P1  
**Outcome:** every request and execution can be traced safely.

- Structured logs.
- Request, correlation, trace, conversation, and job IDs.
- Metrics for API/provider latency, tokens, errors, retries, active streams, jobs, and queue depth.
- Distributed tracing across API, provider, database, queue, and workers.
- Immutable or append-oriented audit events.
- Secret and sensitive-content redaction.
- Operational dashboards and alert guidance.

## 7.12 Testing and Release Engineering

**Priority:** P0  
**Outcome:** every supported path is reproducible and gated.

Required suites:

- unit;
- CLI;
- API contract;
- provider adapter;
- persistence and migration;
- authorization and tenant isolation;
- deterministic streaming;
- file security;
- tool approval and sandbox;
- job idempotency, retry, recovery, and cancellation;
- frontend and browser E2E;
- container and deployment smoke tests.

CI must reject schema drift, migration failures, leaked secrets, disabled tests without justification, and packaging regressions.

---

## 8. Release Milestones

### Milestone A — Architecture Foundation

- Canonical domain models.
- Typed error contract.
- Product API client foundation.
- Provider adapter interface.
- Initial versioned API skeleton.
- Health, readiness, version, and model catalog.

**Exit criterion:** CLI can query product health and models without provider credentials.

### Milestone B — Core Chat Through Product API

- Non-streaming messages.
- Streaming events.
- Cancellation.
- Usage and stop reasons.
- Conversation persistence.
- CLI and TUI migration for chat paths.

**Exit criterion:** prompt and interactive chat use only the product API.

### Milestone C — Secure Files and Tools

- Authorized attachments.
- Tool registry and schema validation.
- Grants and approval state machine.
- Sandboxed workers and resource limits.
- Audit events.

**Exit criterion:** mutating tools cannot run without valid policy and approval.

### Milestone D — Durable Jobs and Operations

- Job queue and workers.
- Idempotency and retries.
- Recovery and cancellation.
- Metrics and tracing.
- Hardened deployment topology.

**Exit criterion:** jobs survive process restarts and remain auditable.

### Milestone E — Unified Web Product

- Authenticated browser experience.
- Shared generated types.
- Streaming and uploads.
- Administration and usage views.
- Browser security and E2E tests.

**Exit criterion:** web and CLI expose consistent product semantics.

### Milestone F — Production General Availability

- Full security review.
- Capacity and failure testing.
- Backup and restore validation.
- Upgrade and rollback rehearsal.
- Release artifacts and support policy.

**Exit criterion:** every production definition-of-done item is evidenced in CI or release records.

---

## 9. Technical Debt Register

The following debt must be tracked until removed or explicitly accepted:

- Flat module layout and very large CLI dispatch surface.
- Provider-specific imports distributed across client-facing modules.
- Multiple request-construction and retry implementations.
- Documentation inventory and version drift.
- Security helpers that are not universally integrated.
- Conflicting file-size and path-validation behavior.
- Permission modes whose runtime semantics require explicit verification.
- Shell execution relying on optional or best-effort filtering.
- Local state formats without durable migration policy.
- Framework route handlers and feature flags not represented in a generated dependency map.
- Tests that validate wiring but not complete runtime behavior.

Debt entries are closed only when implementation, regression tests, and documentation land together.

---

## 10. Breaking-Change Policy

A breaking change requires:

1. documented motivation;
2. affected commands, API routes, schemas, and configuration keys;
3. migration procedure;
4. deprecation or compatibility window where practical;
5. rollback plan;
6. automated compatibility tests;
7. release-note entry.

Provider-specific flags may be retained as deprecated aliases while clients migrate to provider-neutral product fields.

---

## 11. Progress Reporting

Progress is reported by completed acceptance criteria, not estimated percentages.

### Verified complete

- Cross-platform build foundations.
- Broad local CLI capability surface.
- TUI streaming reliability slice.

### Active priority

- Canonical product API client.
- Provider-neutral domain boundary.
- Versioned product API foundation.
- Security integration for local tools and filesystem operations.

### Planned next

- CLI/TUI chat migration.
- Conversations and durable persistence.
- Files and attachments.
- Tool grants and approvals.
- Durable jobs and workers.
- Unified web frontend.
- Full observability and production operations.

---

## 12. Production Definition of Done

ZAI Coder is production-ready only when all applicable statements are true:

- [ ] CLI, TUI, and web clients use only the product API.
- [ ] Client packages do not import provider SDKs.
- [ ] Provider secrets are server-side and managed through an approved secret store.
- [ ] Runtime schemas and OpenAPI pass drift validation.
- [ ] Access-token refresh, rotation, revocation, and secure client storage are tested.
- [ ] Every durable record is correctly scoped and authorized.
- [ ] Every mutating operation is authorized and audited.
- [ ] Every stream emits exactly one terminal event.
- [ ] Cancellation propagates through client, API, provider or worker, and persistence.
- [ ] Idempotent operations do not create duplicate side effects.
- [ ] File paths, URLs, names, sizes, and content types are validated centrally.
- [ ] Tool grants and approvals are explicit, expiring, and tested.
- [ ] Shell and filesystem tools run under enforceable isolation and resource limits.
- [ ] Logs, traces, metrics, errors, and audit events redact secrets.
- [ ] Database migrations pass from empty and supported previous versions.
- [ ] Unit, contract, integration, security, frontend, and E2E tests pass.
- [ ] CLI, server, frontend, and container production builds pass.
- [ ] Health and readiness checks verify real dependencies.
- [ ] Backup, restore, upgrade, and rollback procedures are rehearsed.
- [ ] Documentation reflects the shipped behavior and current source version.
- [ ] No material production TODO, placeholder, mock-only path, or unexplained disabled test remains.

---

## 13. Governance

- `ROADMAP.md` owns product direction and milestone status.
- `docs/migration/execution-plan.md` owns implementation order and acceptance gates.
- Architecture decision records own irreversible or cross-cutting decisions.
- OpenAPI and generated clients own external API contracts.
- CI and release records own verification evidence.

Changes that alter the target architecture, security model, persistence model, or public API require corresponding updates to both this roadmap and the execution plan.
