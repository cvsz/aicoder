# Feature Matrix

| Capability | CLI | TUI/Web | Product API | Persistence | Tests | Status |
|---|---|---|---|---|---|---|
| Direct model requests | Implemented | Implemented | Missing canonical boundary | Local only | Present | Provider-coupled |
| Streaming | Implemented | TUI reliability slice complete | Missing canonical events | Partial/local | Present | Partial |
| Model catalog | Implemented | Partial | Missing canonical route | Local metadata | Present | Partial |
| Authentication | Provider key | Provider key | Product auth missing | Missing | Limited | Missing |
| Conversations | Local/session paths | Partial | Missing | Non-durable | Partial | Partial |
| File handling | Multiple modules | Partial | Upload boundary missing | Local/provider-specific | Partial | Partial/unsafe until policy audit |
| Tool execution | Implemented locally | Limited | Grants/approval API missing | Audit incomplete | Partial | Unsafe by target standard |
| Jobs/queue | Feature-specific | Missing | Missing | Missing durable job store | Missing | Missing |
| Audit events | Logging-oriented | Missing | Missing | Missing | Missing | Missing |
| Observability | Several local modules | Limited | Cross-layer IDs missing | N/A | Partial | Partial |
| Typed Product API client | Missing | Missing | N/A | N/A | Missing | Next foundation |
| Provider adapter | Missing canonical interface | Missing | Missing | N/A | Missing | Planned |
| OpenAPI contract | Missing canonical source | Missing | Missing | N/A | Missing | Planned |
| Production deployment | Build assets exist | Web assets exist | Platform deployment missing | Platform stores missing | CI failing | Not ready |

Status means verified production path, not presence of a module or flag.
