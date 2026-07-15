# Changelog

Full per-version detail lives in `docs/*_upgrade_*.md` — this file is a
high-level index. Two project lineages (`zai-coder-cli-v1`, the modular
`claude_*.py`-per-feature codebase, and `zai-coder-cli-v2`, a smaller
single-`coder.py` CLI with its own PyInstaller packaging) were merged into
this release; see "v1.12.0" below for exactly what came from where.

## Unreleased

**Primary CLI simple streaming migration**: plain `main.py --stream` prompt
calls that use only `--model` and `--max-tokens` now render canonical Product
API stream events. File, thinking, tool, and richer stream modes retain their
existing legacy behavior until their dedicated migration slices land.

**Primary CLI simple prompt migration**: plain `main.py -p/--prompt` calls
that use only `--model`, `--max-tokens`, and `--output` now use the canonical
Product API client. Richer or provider-specific prompt modes retain their
existing legacy behavior until their dedicated migration slices land.

**Primary CLI model catalog migration**: `main.py --list-models` now uses the
canonical Product API client and Product API runtime configuration, before any
legacy provider-key lookup. The explicitly named `--list-models-legacy` path
is retained while the legacy catalog is still needed.

**Product API CLI operational controls**: `zai-coder-api` now accepts
`--api-version`, `--api-timeout`, `--api-max-retries`, `--request-id`, and
`--correlation-id`. The canonical client preserves supplied request context
for JSON and SSE calls. `--debug` reports only request metadata; it never
prints Product API access tokens or provider credentials.

## v1.23.0 — Deep Web Research Cycle (18 gaps closed)

Seven-pass deep web research against docs.anthropic.com, anthropic.com/news,
anthropic.com/engineering, the Anthropic Python SDK changelog (41 versions),
the live SDK client, and the Anthropic Cookbook. Eighteen API gaps found and
closed; full detail in `docs/36_research_claude_updates_2026q2.md`.

**Thinking display control** (new): `--thinking-display omitted|summarized`
controls whether thinking blocks are streamed or suppressed for lower
latency. `display: "omitted"` is the default on Fable 5, Mythos 5, Sonnet 5,
Opus 4.8/4.7 — reduces time-to-first-text-token while still billing full
thinking tokens. Added `display` parameter to `ThinkingCoder` methods and
`signature_delta` event handling in streaming. 16 new tests.

**Adaptive-only model gate** (new): `THINKING_ADAPTIVE_ONLY` set identifies
models that require `type: "adaptive"` thinking (Sonnet 5, Opus 4.8, Fable 5,
Mythos 5, Mythos Preview). `_resolve_thinking_type()` auto-upgrades from
`"enabled"` to `"adaptive"` with a stderr warning. `--thinking-allow-manual`
flag bypasses the gate for explicit `"enabled"` thinking (use with caution).
Added `allow_manual` parameter to `generate_with_thinking()`,
`stream_with_thinking()`, and `cmd_thinking()`.

**`effort: "xhigh"`** (new): fifth effort level mapping to 24,000 thinking
tokens (between high=16k and max=32k). `--effort` choices now include
`xhigh`. Also: `--effort` is now sent as `output_config.effort` on the
Messages API request (previously only affected thinking budgets in
`claude_thinking.py`, silently dropped for non-thinking code paths — a P1
wiring bug).

**Server tool version drift** (fix): `web_search` bumped from `20260209`
→ `20260318`, `web_fetch` bumped from `20250124` → `20260318` across both
`claude_search.py` and `claude_tools.py`. New helper functions
`build_web_search_tool(response_inclusion=)` and
`build_web_fetch_tool(use_cache=, response_inclusion=)` for opt-in
configuration. New CLI flags: `--search-response-inclusion full|excluded`,
`--fetch-no-cache`. `RETIRED_TOOL_VERSIONS` expanded with 4 new advisory
entries.

**`output_tokens_details` / thinking tokens** (new): streaming and thinking
modules now capture and display `output_tokens_details.thinking_tokens`
from the usage response (SDK v0.105.0+), plus `cache_creation_input_tokens`
and `cache_read_input_tokens`. Fixed incorrect `thinking_input_tokens` field
reference that was never populated by the API.

**`output_config.effort` wiring** (fix, P1): `Coder.__init__()` now accepts
`effort` parameter and sends `output_config: {"effort": ...}` in the request
payload. `main.py` wires `--effort` through to the `Coder` constructor for
all non-thinking code paths.

**`anthropic-user-profile-id` header** (new): `Coder.__init__()` accepts
`user_profile_id` and sends the `anthropic-user-profile-id` header with the
`user-profiles` beta header. New CLI flag: `--user-profile PROFILE_ID`.

**User profiles CRUD** (new): `ManagedAgentsClient` gains
`create_user_profile()`, `list_user_profiles()`, `get_user_profile()`
methods. CLI flags: `--agent-user-profile-list`,
`--agent-user-profile-create NAME`, `--agent-user-profile-external-id ID`.

**Deployment runs history** (new): `ManagedAgentsClient` gains
`list_deployment_runs(deployment_id=, has_error=)` and
`get_deployment_run(run_id)` for viewing scheduled deployment execution
history. CLI flags: `--agent-deployment-runs`,
`--agent-deployment-run-filter ID`, `--agent-deployment-run-id ID`,
`--agent-deployment-run-errors`.

**Model catalog** (update): `claude-mythos-preview` added to
`MODEL_CATALOG`. Opus 4.1 (`claude-opus-4-1-20250514`) added to
`RETIRED_MODELS` with `upcoming: true` flag (scheduled retirement
2026-08-05). `cmd_model_info()` and `cmd_check_deprecated()` updated to
display upcoming retirements differently from already-retired models.

**Embeddings** (update): `DEFAULT_MODEL` updated from `voyage-3.5` to
`voyage-4` (Voyage 4 series, released 2026-01-15). `main.py` `--embed-model`
default updated. Module docstring lists all available Voyage 4 models.

**Refusal categories** (update): `handle_refusal()` docstring updated to
document all four categories: `cyber`, `bio`, `frontier_llm`,
`reasoning_extraction`. `claude_fable5.py` `REFUSAL_CATEGORIES` already
covered all four.

**Streaming** (update): `system_message` event handler added for SDK
v0.112.0 compatibility.

**Test infrastructure** (fix): Removed stale `utils/` directory (empty
`__init__.py`) that was shadowing `utils.py`, breaking imports in
`test_coder.py` and `test_utils.py` (42 tests recovered). Fixed
`injection_location` assertion in `test_claude_agents_sdk.py` (1 pre-existing
failure resolved). Added `--thinking-allow-manual` CLI flag wiring.

**Strategic analysis** (new): `docs/37_strategic_analysis_v1.23.md` —
synthesizes all research findings into architecture observations, feature
maturity assessment, testing gaps, API surface coverage map, risk register,
and v1.24.0 candidates.

Total test count: **279** (up from 186 in v1.22.0) — 17 new tests covering
deployment runs, user profiles, xhigh effort, display omitted/summarized,
adaptive-only gate, tool versions, response_inclusion, use_cache, embeddings
default, model catalog, and Opus 4.1 retirement. Plus 42 recovered tests and
1 pre-existing failure fixed. All 279 tests passing.

**Dependencies** (update): `requirements.txt` `anthropic` pin bumped from
`>=0.75.0` to `>=0.116.0` — required for `client.beta.deployment_runs`,
`client.beta.user_profiles`, and `agent-memory-2026-07-22` beta header.

## v1.22.0 — Agent Overrides, Injection Locations, Event Deltas, Tool Upgrade

Re-ran the `ROADMAP.md` gap-audit methodology against the live docs
(previous audit: 2026-07-08; this one: 2026-07-09). Four findings, all
closed in this release — full detail in `docs/35_upgrade_v1.22.0.md`.

**Session-Level Agent Overrides** (new): `ManagedAgentsClient.create_session()`
now accepts an optional `agent_id_override` parameter. When given, the
session is created with a different agent than the default — enabling
dynamic agent routing (switching agents per-session based on context)
without changing the workspace-level agent configuration. Added
`agent_id_override` param to `create_session()`, plumbing it through to
the `agent` field in the session creation payload.

**Vault Credential Injection Location** (new): `ManagedAgentsClient.add_credential()`
now accepts an `injection_location` parameter for `environment_variable`
credentials — one of `"headers"`, `"body"`, or `"both"` — controlling
where the Egress Proxy substitutes the secret into the outbound request.
Defaults to `"headers"` for backward compatibility. New CLI flag:
`--agent-vault-injection-location`. Invalid values raise `ValueError`.

**Streamed Event Deltas** (new): `ManagedAgentsClient.run_task()` now
captures `event_delta` events from the managed agent stream — incremental
text fragments that arrive before the complete `agent.message` event,
enabling real-time preview of agent output. Returned as a new `"deltas"`
field in the result dict (None when no deltas occurred).

**Code Execution Version Upgrade** (fix): `claude_code_exec.py`'s
`CODE_EXEC_TOOL` type and `BETA_HEADER` updated from
`code_execution_20250522`/`code-execution-2025-05-22` to the GA version
`code_execution_20260120`/`code-execution-2026-01-20`, which supports
REPL state persistence across turns. All other modules were already using
this version — this closes the final drift point.

Total test count: 186 (up from 176 in v1.20.0) — 10 new tests covering
all four findings.

## v1.20.0 — Dreaming, Outcomes, Webhooks

Re-ran the `ROADMAP.md` gap-audit methodology against the live docs
(previous audit: 2026-07-08; this one: 2026-07-08). Three findings,
closed in this release; one further finding (native Multiagent
orchestration) confirmed real but deliberately deferred — full detail
in `docs/33_upgrade_v1.20.0.md`.

**Dreaming** (research preview, new): reviews a memory store alongside
past session transcripts and produces a new, curated output memory
store — duplicates merged, stale entries dropped, recurring patterns
promoted. The input store is never modified. Found by re-checking the
Managed Agents docs for what shipped alongside the memory-store feature
closed in v1.19.0. Added to `claude_agents_sdk.py`:
`ManagedAgentsClient.create_dream()`, `.get_dream()`, `.list_dreams()`,
`.cancel_dream()`, and CLI commands `cmd_agent_dream()`,
`cmd_agent_dream_get()`, `cmd_agent_dream_list()`. New flags:
`--agent-dream STORE_ID`, `--agent-dream-sessions IDS`,
`--agent-dream-instructions TEXT`, `--agent-dream-list`,
`--agent-dream-get DREAM_ID`.

**Outcomes** (public beta, new): define a rubric-graded self-correction
loop instead of a single plain task — a separate grader model evaluates
the agent's work in its own context window and the agent revises until
satisfied or `max_iterations` is hit. Added
`ManagedAgentsClient.define_outcome()` and `.wait_for_outcome()`;
`cmd_managed_agent_run()` now takes `outcome_description` /
`outcome_rubric` / `outcome_max_iterations` params, opt-in, falling
through to the pre-existing single-task path when unset. New flags:
`--agent-outcome DESC`, `--agent-outcome-rubric FILE`,
`--agent-outcome-max-iter N`.

**Webhooks** (public beta, new): register a URL to be notified of
session/outcome/dream lifecycle events instead of holding an SSE stream
open. Added `ManagedAgentsClient.register_webhook()` and
`cmd_agent_webhook_register()`. New flags: `--agent-webhook-register
URL`, `--agent-webhook-events LIST`.

**Deferred: native Multiagent orchestration** — a lead/specialist
coordinator topology configured on the Agent resource itself
(`multiagent: {type: "coordinator", agents: [...]}`), distinct from
`claude_agents_sdk.py`'s pre-existing client-side `--agent-orchestrate`
(which makes separate Messages API calls per subagent, no shared
Managed Agents session or filesystem). Confirmed real and absent, but
left undocumented-as-built pending a concrete use case — same pattern
as the Compliance API between v1.15.0 and v1.16.0. See
`docs/33_upgrade_v1.20.0.md` for the full reasoning and exit condition.

Total test count: 176 (up from 160 in v1.19.0) — 16 new tests in
`tests/test_claude_agents_sdk.py` covering Dreaming, Outcomes, and
Webhooks.

## v1.19.0 — Managed Agents memory stores

Re-ran the `ROADMAP.md` gap-audit methodology against the live docs
(previous audit: 2026-07-08; this one: 2026-07-08). One finding, closed
in this release — full detail in `docs/32_upgrade_v1.19.0.md`.

**Managed Agents memory stores** (new, genuinely missing): a workspace-
scoped, persistent, versioned file directory (`memory_store`) that can
be mounted into a hosted Managed Agents session via `resources`, so an
agent's work survives past one session. Found by checking the
`anthropic` Python SDK's own changelog for drift (v0.116.0 added an
`agent-memory-2026-07-22` beta header) rather than the docs' feature
list directly. Added to `claude_agents_sdk.py`:
`ManagedAgentsClient.create_memory_store()`, a `memory_store_id` param
on `create_session()` that mounts the store as a `resources` entry,
and `cmd_agent_memory_store_create()`. New flags: `--agent-memory-store
NAME`, `--agent-memory-store-create`.

Also checked for drift in `claude_models.py`'s catalog against the live
Models overview — no stale entries found, nothing to fix.
`claude_agents_sdk.py` had zero test coverage before this release;
added `tests/test_claude_agents_sdk.py` (10 tests, all passing alongside
the 150 pre-existing tests — 160 total).

## v1.18.0 — Mid-conversation system messages + Cache diagnostics CLI wiring

Re-ran the `ROADMAP.md` gap-audit methodology against the live docs
(previous audit: 2026-07-04; this one: 2026-07-08). Two findings, both
closed in this release — full detail in `docs/31_upgrade_v1.18.0.md`.

**Mid-conversation system messages** (new, genuinely missing): Opus
4.8-only feature that lets you append a `role: "system"` message partway
through a conversation to update Claude's instructions without touching
the top-level `system` field — so the cached prefix that came before it
stays intact. Added to `claude_cache.py`: `build_mid_system_message()`,
`validate_system_message_placement()` (encodes all five documented
placement rules and raises a dedicated `SystemMessagePlacementError`
naming which one failed), a `MID_SYSTEM_SUPPORTED_MODELS` model gate, and
`mid_system` / `mid_system_updates` params on `generate_cached()` /
`multi_turn_cached()` respectively. New flags: `--cache-multi-turn`,
`--cache-mid-system`, `--cache-mid-system-after`.

**Cache diagnostics (beta) — CLI wiring** (narrower than it first looked):
grepping for `cache_diagnostic`/`cache.diagnostic` found nothing and read
like a fresh gap, but `claude_cache.py` already fully implemented this
feature (`diagnose=` param, the `cache-diagnosis-2026-04-07` beta header,
`cache_miss_reason` surfaced through `cache_stats()`) — the grep pattern
just didn't match the identifiers actually used. The real gap: nothing in
`main.py` ever set `diagnose=True`, so it was unreachable from the CLI.
Added `--cache-diagnose`.

Also checked for drift in `claude_models.py`'s catalog against the live
Models overview — no stale entries found, nothing to fix. `claude_cache.py`
had zero test coverage before this release; added `tests/test_claude_cache.py`
(18 tests, all passing alongside the 132 pre-existing tests — 150 total).

`ROADMAP.md` itself was also stale (header still read v1.15.0, and four
of the six gaps closed in v1.15.0/v1.16.0 were never marked done in Part
2 despite being fully implemented) — corrected as part of this cycle,
independent of the two feature gaps above.

## v1.17.0 — Resilience wired into every direct-HTTP module

Closes the gap `ARCHITECTURE.md` had flagged since it was written:
`resilience.retry()` / `CircuitBreaker` was only used by `coder.py`.
Audited every module for raw `urllib` calls (as opposed to going through
the `anthropic` SDK client, which already retries internally) and found
19, not the SDK-based `claude_batch.py`/`claude_rag.py` sometimes lumped
in with them, plus one the earlier audit missed entirely: `cowork.py`.

Added `raise_for_http_error()`, `urlopen_json()`, and `urlopen_text()` to
`resilience.py` — shared helpers that translate a raw `urllib` HTTP or
network exception into the `AICoderError` hierarchy `retry()` already
knows how to read, so each module no longer hand-rolls its own
`except HTTPError` translation. Every module now retries transient
failures (429/5xx/network) with exponential backoff and fails fast via a
`CircuitBreaker` once a downstream is clearly down, without changing any
external contract — callers that expected a `{"error": ...}` dict back,
or a `RuntimeError`, or a `[API ERROR N]` string, still get exactly that
shape; only what happens underneath changed.

Two deliberate exceptions to a shared per-module breaker: `claude_github.py`
gets one breaker (all its call sites hit the GitHub API), while call sites
that fetch an arbitrary caller-supplied URL — `claude_chrome.py`'s page
fetch, `claude_research.py`'s source fetch, `claude_code.py`'s `WebFetch`
tool, `claude_plugins.py`'s marketplace fetch — retry transient failures
but skip the breaker, since a breaker tracking "this one dependency is
down" doesn't mean anything when every call targets a different host.

All 132 pre-existing tests still pass; verified end-to-end with a mocked
503 that retries twice then succeeds on the 3rd attempt.

## v1.16.0 — Compliance API

Closes the one gap v1.15.0 deliberately left open. New module
`claude_compliance_api.py` wraps `/v1/compliance/*`: the org-wide
Activity Feed, plus (with a Compliance Access Key) read/hard-delete
access to the chats, files, and projects those activities reference,
plus directory (orgs/users/roles/settings/groups) endpoints. Every
destructive op is dry-run by default and requires `--compliance-yes`.
Retry/backoff and pagination-cursor handling follow the documented
compliance-errors contract exactly (see `docs/30_upgrade_v1.16.0.md`).
28 new tests in `tests/test_claude_compliance_api.py`, all passing.

## v1.15.0 — Roadmap gap-audit implementation

Implements the five buildable items from `ROADMAP.md`'s gap audit against
platform.claude.com/docs (checked 2026-07-04); the sixth (Compliance API)
stays a documented gap per the roadmap's own recommendation. See
`docs/29_upgrade_v1.15.0.md` for the full write-up and `CHECKLIST.md` for
the itemized task list this release closes out.

- **P0 — Server-side `fallbacks` param** (`claude_fable5.py`): new
  `--fable5-fallback-chain MODEL1,MODEL2` lets the platform itself retry a
  refused Fable 5 call against up to 3 models in one round trip, instead
  of the existing client-side manual retry (`--fallback-model`, still
  supported, now the fallback path only when a chain isn't given).
- **P1 — Context editing** (new `claude_context_editing.py` is not
  needed — `claude_tools.py` already had a complete
  `build_context_management()`; the actual gap was that
  `claude_code.py`'s `--code-agent` loop never called it). New
  `--agent-context-editing` flag wires `clear_tool_uses` into the agent
  loop, complementary to the existing Compaction support. See
  `docs/29_upgrade_v1.15.0.md` for a worked example combining both.
- **P1 — Agent Skills API** (new `claude_skills_api.py`): `skill_id`-based
  platform Skills, distinct from `claude_code.py`'s local
  `.claude/skills/*/SKILL.md` loader. New `--skills-list` / `--skills-info
  ID` flags. Routing `claude_excel.py`/`claude_powerpoint.py` through this
  instead of their existing hand-rolled implementation is an intentional
  follow-up, not part of this release.
- **P2 — Usage and Cost API + API key management** (new
  `claude_admin_api.py`, combined per the roadmap's own suggested
  grouping): new `--usage-report` and `--admin-list-keys` /
  `--admin-revoke-key` flags. Both require an Admin API key
  (`--admin-api-key` or `ANTHROPIC_ADMIN_API_KEY`), not a regular one.
  `--admin-create-key` intentionally explains why key creation isn't
  exposed via the API rather than faking it — Anthropic doesn't document a
  create-key endpoint (Console-only, secret shown once).
- **P2 — Compliance API**: left as a documented gap, not built, per the
  roadmap's recommendation (enterprise-only surface, no concrete use case
  yet).

## v1.14.0 — Chat & Excel

Two new user-facing features, both additive: `-i`/`--interactive` (a bare,
dead argparse flag since v1.7.0) now runs a real persistent chat REPL, and
a new `--excel` conversational spreadsheet assistant builds financial
models, cleans messy data, and creates tables/charts against a live
`.xlsx` workbook. No existing flags changed. See
`docs/28_upgrade_v1.14.0.md`.

## v1.13.0 — Enterprise hardening

Structured logging with secret redaction, retry + circuit breaking around
the core API call, path/URL/input security controls, a `--health-check`
for orchestrators, and a full test/CI/Docker setup. No CLI flags removed
or renamed. See `docs/27_upgrade_v1.13.0.md`.

## v1.12.1 — 2026-07-03

Deep-dive bug pass against v1.12.0, plus a new bulk model-upgrade feature.
See `docs/26_upgrade_v1.12.1.md` for full detail.

- Fixed `coder.py`'s `Coder.generate()` silently mishandling responses from
  thinking-capable models (Sonnet 5, Opus 4.8, Fable 5/Mythos 5) and any
  multi-text-block response — was reading only `content[0]["text"]`.
- Wired three previously dead-on-arrival CLI flags: `--skill`, `--agent`
  (accepted, never read anywhere), and `--cache-stats` (accepted, but
  `--cache` always showed stats regardless of it).
- Added `--personality` / `--list-personalities`, exposing `personalities.py`'s
  `PersonalityManager`, which was fully implemented and already wired into
  `Coder.__init__` but unreachable from the CLI.
- **New:** `--upgrade-all PATH [--upgrade-target fable5|opus] [--upgrade-yes]
  [--upgrade-no-backup]` — bulk-rewrites every known Claude model ID under a
  file or directory to Claude Fable 5 or Claude Opus 4.8. Dry-run by
  default; writes `.bak` backups on apply. Distinct from the existing
  `--check-deprecated` (report-only, retired IDs only).

## v1.12.0 "Release" — 2026-07-03

Packaging-only release. No API/functional changes from v1.11.1.


- Merged in `zai-coder-cli-v2`'s standalone-executable packaging: `build.sh`
  / `build.bat` (PyInstaller, produces a single `dist/zai-coder` binary with
  no local Python required), `setup.sh` / `setup.bat` (venv + `.env` setup
  for running from source), `zai-coder.spec`, `LICENSE` (MIT).
- Added `.env.example` (referenced by `setup.sh`/`setup.bat` but missing
  from both source projects) documenting `ANTHROPIC_API_KEY` (required),
  `VOYAGE_API_KEY` (optional, `claude_embeddings.py`), `GITHUB_TOKEN`
  (optional, `claude_github.py`).
- `requirements.txt`: bumped minimum `anthropic` SDK to `>=0.75.0`,
  required for `client.beta.agents/.environments/.sessions`
  (`--agent-managed-run`, see `claude_agents_sdk.ManagedAgentsClient`).
- Everything else in `zai-coder-cli-v2` (`coder.py`, `config.py`, `utils.py`,
  `skills.py`, `agents.py`, `multi_agent_core.py`, `workflow_examples.py`,
  `batches.py`, its own `managed_agents.py`) was **not** merged — v1 already
  has a mature, independently-audited implementation of the same ground
  (`coder.py`/`config.py`/`utils.py`/`skills.py` under the same names but a
  different, already-integrated implementation; `claude_agents_sdk.py`'s
  `ManagedAgentsClient` already wraps the real Managed Agents API that
  v2's `managed_agents.py` also wrapped). Merging both would have meant two
  competing implementations behind the same CLI flags and import names —
  picked the one already wired into 900+ lines of `main.py` and this
  project's own audit history rather than replacing it. See
  `docs/25_merge_v2_into_release.md` for the full reasoning.

## v1.11.1 and earlier

See `docs/*_upgrade_*.md` for the full per-release history, starting from
`docs/17_projects_and_artifacts.md`. Highlights:

- **v1.11.1**: MCP tunnels (`claude_agents_sdk.McpTunnel`), retired
  tool-version tracking (`claude_tools.RETIRED_TOOL_VERSIONS`), refusal
  billing exemption in the cost optimizer, a Sonnet-5 sampling-parameter
  fix.
- **v1.11.0**: Advisor tool (`claude_advisor.py`), Programmatic Tool
  Calling (real implementation), Tool Use Examples, task budgets,
  compaction, embeddings (`claude_embeddings.py`, via Voyage AI),
  fine-grained tool streaming, `stop_details` on refusals.
- **v1.10.x**: native memory tool, context editing, tool search tool,
  full model catalog + retired-model registry, verified pricing.
- **v1.9.x – v1.0**: Claude Code / Agent SDK, Cowork, plugins, output
  styles, sandbox, RAG, evals, batch API, prompt caching, vision, and the
  rest of the modular `claude_*.py` feature set.
