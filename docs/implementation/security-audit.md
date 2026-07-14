# Security Audit Baseline

## Scope

Static repository assessment only. Findings are classified as verified architecture facts, high-confidence code risks, or hypotheses requiring an executable proof. No claim of exploitability is made solely from a filename or grep hit.

| Finding | Severity | Confidence | Evidence class | Required remediation |
|---|---|---:|---|---|
| Provider credentials in client-facing paths | High | High | Direct environment/config references | Move to server-only secret resolver |
| Provider SDK imports distributed across client modules | High | High | AST import inventory | Introduce provider gateway and adapter |
| Shell execution paths using `shell=True` | Critical where model/user-controlled | High | Static call-site inventory | Default deny, structured argv, sandbox worker, approvals |
| Filesystem paths accepted by local tools | High | Medium | Static tool/path review | Resolve under allowed roots; reject traversal/symlink escape |
| Permission modes not represented as explicit state machine | High | High | Current local permission design | Typed grants, approval expiry, actor/audit binding |
| Security helpers may not be uniformly adopted | Medium | Medium | Reference inventory | Enforce canonical validation at boundaries |
| Logs/errors may contain provider material | High | Medium | Distributed exception rendering | Central redaction before logging/serialization |
| Web trust boundary is ambiguous | High | High | Lightweight backend used as convenience surface | Product auth, CORS, rate limits, typed errors |

## Adversarial tests required

- path traversal and absolute paths;
- symlink escape;
- shell metacharacters and command substitution;
- expired/denied/missing approval;
- provider error containing secret-looking values;
- oversized and mismatched-MIME upload;
- SSRF to loopback, link-local, metadata, and private ranges;
- cancellation during provider stream and tool execution;
- duplicate mutating request with and without idempotency key.

## Immediate policy

Dangerous tool execution must remain local-development-only until an enforceable default-deny worker boundary exists. Documentation warnings and regex-only command inspection are not production controls.
