# API Gap Analysis

## Current state

The repository exposes provider capabilities primarily through CLI modules and a lightweight web backend. There is no single versioned Product API contract consumed by CLI, TUI, web, tests, and automation.

| Required contract | Current evidence | Gap |
|---|---|---|
| `/v1/health`, `/live`, `/ready` | Local health helpers/backend behavior | No canonical semantics or dependency readiness |
| `/v1/version` | CLI version constant | No negotiated API/client compatibility contract |
| `/v1/models` | Local/provider model modules | No provider-neutral Product API schema |
| Product login/refresh/logout | Provider API key | Product identity and refresh flow absent |
| Conversations/messages | Local interactive/session modules | No durable scoped REST contract |
| Streaming messages | Provider/TUI-specific streams | No canonical SSE/event vocabulary |
| Files/attachments | Feature-specific APIs/local paths | No centralized validation, metadata, authorization, lifecycle |
| Tools/grants/approvals | Local permission modes | No explicit grant/approval state machine API |
| Jobs/cancel/retry/events | Feature-specific execution | No durable idempotent job contract |
| Errors | Module-specific exceptions/prints | No shared typed error envelope |
| Pagination | Feature-specific | No shared cursor/page contract |
| OpenAPI | None as canonical source | Runtime/schema drift cannot be checked |

## First contract slice

1. Shared provider-neutral identifiers, content blocks, usage, errors, and stream events.
2. Typed client transport with IDs, timeout, retry classification, and redaction.
3. Product API health/version/models routes.
4. Anthropic adapter behind server-only provider gateway.
5. Migrate CLI health and model listing before chat/message paths.
