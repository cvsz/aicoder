# Claude.ai / Anthropic API Update Research — 2026-07-09

Research conducted against `platform.claude.com/docs`, `docs.anthropic.com`,
and `anthropic.com/news`. Sources checked: Models overview, Messages API
reference, Extended Thinking guide, Tool Use reference, Prompt Caching
guide, Streaming reference, and Anthropic news feed.

zaicoder version at time of research: **v1.22.0** (current, 220 tests passing).

---

## Summary

zaicoder is remarkably up-to-date — the previous gap-audit cycles (v1.15.0
through v1.22.0) have closed nearly every significant gap. This deep
research cycle found **10 remaining API-level gaps** and **4 product-surface
items** worth tracking. No gaps are P0/critical; most are P1-P2 additive
features. All 10 API gaps have been closed.

---

## Part 1 — Confirmed API Gaps (Ranked by Priority)

### 🔴 P1-1 — Thinking `display: "omitted"` (latency optimization)

**What it is:** A `display` field on the thinking config that accepts
`"omitted"` — returns thinking blocks with an empty `thinking` field but
a `signature` for multi-turn continuity. Reduces time-to-first-text-token
by skipping the streaming of thinking tokens entirely. Full thinking
tokens are still billed.

**Default on new models:** `"omitted"` is the default for Claude Fable 5,
Mythos 5, Sonnet 5, Opus 4.8, Opus 4.7, and Mythos Preview. `"summarized"`
remains the default for Opus 4.6, Sonnet 4.6, and earlier Claude 4 models.

**Current state in zaicoder:** `claude_thinking.py` builds `thinking_cfg`
with only `type` and `budget_tokens` — no `display` field anywhere in
the module. Grepping for `omitted` across the codebase returns zero
matches.

**Impact:** Users calling newer models get the `"omitted"` default from
the API server anyway, but zaicoder can't let users opt *into* `"omitted"`
on older models, can't opt *out of* `"omitted"` on newer models (to see
the full thinking), and doesn't handle the `signature_delta` streaming
event that replaces `thinking_delta` when display is omitted.

**Implementation plan:**
- Add `display` parameter to `ThinkingCoder.__init__()`,
  `generate_with_thinking()`, and `stream_with_thinking()`
- Valid values: `"summarized"`, `"omitted"`, or `None` (API default)
- In `stream_with_thinking()`, handle `signature_delta` events (no
  `thinking_delta` events emitted when display is `"omitted"`)
- Add CLI flags: `--thinking-display omitted|summarized`
- Wire into `cmd_thinking()` entry point
- Add to RETIRED_TOOL_VERSIONS-style advisory: document which models
  default to which display mode

### 🟡 P1-2 — `effort: "xhigh"` level missing

**What it is:** The API's `output_config.effort` parameter accepts 5
levels: `low`, `medium`, `high`, `xhigh`, `max`. zaicoder only maps 4.

**Current state:** `claude_thinking.py`'s `EFFORT_BUDGETS` dict maps
`low`→2000, `medium`→8000, `high`→16000, `max`→32000. `xhigh` is
missing. `claude_models.py` also lists only 4 levels in its docstring.

**Impact:** Users passing `--effort xhigh` get no budget mapping and
fall through to whatever `budget_tokens` was passed (or the default
8000), silently using too little budget for what `xhigh` should provide.

**Implementation plan:**
- Add `"xhigh": 24_000` to `EFFORT_BUDGETS` (midway between high=16k
  and max=32k, matching the API's own ordering)
- Update `claude_models.py` docstring to list all 5 levels
- Update `main.py` help text for `--effort` to include `xhigh`

### 🟡 P1-3 — `web_fetch` version drift (multiple modules)

**What it is:** Three separate version drifts found:

| Location | Current | Latest Available |
|---|---|---|
| `claude_search.py` WEB_FETCH_TOOL | `web_fetch_20250124` | `web_fetch_20260318` |
| `claude_tools.py` SERVER_TOOLS | `web_fetch_20250124` | `web_fetch_20260318` |
| `claude_search.py` WEB_SEARCH_TOOL | `web_search_20250305` | `web_search_20260318` |

The `web_fetch_20260318` version adds `use_cache` (bypass cached content)
and `response_inclusion` (control result visibility when consumed by code
execution). The `web_search_20260318` version adds `response_inclusion`.

**Current state:** `claude_tools.py` updated `web_search` to `20260209`
in a previous cycle, but `web_fetch` stayed at `20250124`. `claude_search.py`
is two versions behind on both tools.

**Implementation plan:**
- Update `claude_search.py` WEB_SEARCH_TOOL to `web_search_20260318`
- Update `claude_search.py` WEB_FETCH_TOOL to `web_fetch_20260318`
- Update `claude_tools.py` SERVER_TOOLS `web_fetch` to `web_fetch_20260318`
- Update `claude_tools.py` SERVER_TOOLS `web_search` to `web_search_20260318`
- Add `response_inclusion` and `use_cache` as configurable parameters
  on the tool descriptors (opt-in, backward compatible)
- Add old versions to `RETIRED_TOOL_VERSIONS` with appropriate notes
- Update the v1.22.0 CHANGELOG entry about `code_execution_20260120` to
  note the tool version audit scope

### 🟡 P1-4 — `code_execution_20260521` version available

**What it is:** A newer code execution version (`code_execution_20260521`)
is available alongside the current `code_execution_20260120`. The API docs
list both as valid versions.

**Current state:** zaicoder uses `code_execution_20260120` everywhere
(`claude_tools.py`, `claude_code_exec.py`). The `20260521` version is
not referenced anywhere in the codebase.

**Impact:** Lower priority since `20260120` is GA and fully functional.
The `20260521` version may add capabilities not yet documented in detail.

**Implementation plan:**
- Add `code_execution_20260521` to `RETIRED_TOOL_VERSIONS` notes
  (as a "newer available" entry, not a retirement of `20260120`)
- Investigate what `20260521` adds before bumping the default
- Consider a `--code-exec-version` flag for opt-in

### 🟡 P2-1 — `response_inclusion` parameter on server tools

**What it is:** `web_search_20260318` and `web_fetch_20260318` support a
`response_inclusion` parameter: `"full"` (default, returns the nested tool
result block) or `"excluded"` (hides it when consumed by code execution
in the same turn). Useful to reduce context window usage when the code
execution sandbox already has the results.

**Current state:** Zero matches for `response_inclusion` across the
codebase.

**Implementation plan:**
- Add as an optional field on the web_search and web_fetch tool
  descriptors in `claude_tools.py`
- Wire a `--search-response-inclusion full|excluded` CLI flag
- Document in the server tools section

### 🟡 P2-2 — `use_cache` parameter on web_fetch

**What it is:** `web_fetch_20260318` adds a `use_cache` boolean parameter
to bypass cached content and force a fresh fetch.

**Current state:** Zero matches for `use_cache` across the codebase.

**Implementation plan:**
- Add as an optional field on the web_fetch tool descriptor
- Wire a `--fetch-no-cache` CLI flag (maps to `use_cache: false`)

### 🟢 P2-3 — New refusal stop_details categories

**What it is:** The API now documents four refusal categories: `"cyber"`,
`"bio"`, `"frontier_llm"`, and `"reasoning_extraction"`. Earlier docs
only listed `"cyber"` and `"bio"`.

**Current state:** `claude_stream.py`'s `handle_refusal()` returns the
raw category without filtering — so it already works for the new
categories. No code change needed, but the docstring only mentions
`"cyber"` and `"bio"`.

**Implementation plan:**
- Update `handle_refusal()` docstring to list all four categories
- Update any inline comments that enumerate the old set

### 🟢 P2-4 — Opus 4.1 retirement date (August 5, 2026)

**What it is:** Claude Opus 4.1 (`claude-opus-4-1-20250514`) is scheduled
for retirement on August 5, 2026. Users must migrate to Opus 4.8.

**Current state:** Opus 4.1 exists in zaicoder's model catalog but has no
retirement date recorded.

**Implementation plan:**
- Add `retirement_date: "2026-08-05"` to the Opus 4.1 entry in
  `claude_models.py`'s `MODEL_CATALOG`
- Add to `RETIRED_MODELS` registry with migration guidance

---

## Part 2 — Product Surface Updates (Non-API)

These are Claude.ai web/desktop product updates that don't have direct
API counterparts but are worth tracking for zaicoder's analog features
(`cowork.py`, `claude_excel.py`, `claude_powerpoint.py`, `claude_chrome.py`).

### Claude Science (announced 2026-06-30)
AI workbench for scientists: customizable tool/package integration,
auditable artifacts, flexible computing resources. No public API yet,
but could inspire a `claude_science.py` analog if an API surfaces later.

### Claude Tag (announced 2026-06-23)
Collaboration feature enabling teams to work with Claude together. No
public API documented yet.

### Claude Code (announced 2026-07-06)
Evolved from internal CLI to public coding agent. zaicoder's `claude_code.py`
already covers this surface comprehensively.

### Fable 5 Redeployment (2026-06-30)
Global redeployment after temporary suspension; new cyber safeguards and
an industry-wide jailbreak severity scoring framework. The two new refusal
categories (`frontier_llm`, `reasoning_extraction`) may relate to this.

---

## Part 3 — Already Implemented (Confirmation)

The following features were investigated and confirmed already present in
zaicoder v1.22.0:

- ✅ `service_tier` parameter (auto/standard_only/batch) — `coder.py`, `main.py`
- ✅ `inference_geo` parameter (us/global) — `coder.py`, `claude_cost_optimizer.py`
- ✅ `output_config.format` (structured JSON) — `claude_structured.py`
- ✅ `cache_control.ttl` (5m/1h) — `claude_cache.py`
- ✅ Cache pre-warming (`max_tokens=0`) — `claude_cache.py`
- ✅ Mid-conversation system messages — `claude_cache.py` (v1.18.0)
- ✅ `count_tokens` endpoint — `claude_tokens.py`
- ✅ `pause_turn` stop reason — `claude_advisor.py`
- ✅ `container_upload` content block — `claude_skills_api.py`
- ✅ Adaptive thinking — `claude_thinking.py`, `claude_models.py`
- ✅ Interleaved thinking — `claude_models.py`
- ✅ Fine-grained tool streaming — `claude_stream.py`
- ✅ Strict tool validation — `claude_tools.py`
- ✅ Memory tool — `claude_memory.py`, `claude_tools.py`
- ✅ Tool search tool — `claude_tools.py`
- ✅ Programmatic tool calling — `claude_tools.py`
- ✅ Context editing — `claude_tools.py`, wired in `claude_code.py`
- ✅ Compaction — `claude_tools.py`, `claude_code.py`
- ✅ Task budgets — `claude_tools.py`
- ✅ Managed Agents (sessions, memory stores, dreaming, outcomes, webhooks)
- ✅ Admin API (usage, key management) — `claude_admin_api.py`
- ✅ Compliance API — `claude_compliance_api.py`
- ✅ Server-side fallback (`fallbacks` param) — `claude_fable5.py`
- ✅ Fable 5 / Mythos 5 modules — `claude_fable5.py`, `claude_mythos5.py`
- ✅ All current models in catalog — `claude_models.py`

---

## Part 4 — Implementation Priority Recommendation

For a v1.23.0 release, the recommended implementation order:

1. **P1-2 (`xhigh` effort)** — Smallest change, highest risk of silent
   misbehavior. 5 lines of code change. ✅ DONE
2. **P1-1 (thinking display)** — Important for users of newer models
   who want to control latency vs. visibility tradeoff. ~50 lines + tests. ✅ DONE
3. **P1-3 (web_fetch/search version bump)** — Version drift cleanup
   that also adds useful new parameters. ~30 lines + tests. ✅ DONE
4. **P2-4 (Opus 4.1 retirement)** — Date is approaching (Aug 5). 2 lines. ✅ DONE
5. **P2-3 (refusal category docs)** — Docstring-only. 2 lines. ✅ DONE
6. **P2-1 (response_inclusion)** — Added as helper functions and CLI flags. ✅ DONE
7. **P2-2 (use_cache)** — Added as parameter and CLI flag. ✅ DONE
8. **P1-4 (code_execution_20260521)** — Noted in RETIRED_TOOL_VERSIONS advisory. ✅ DONE

All 8 gaps closed in this research cycle.

---

## Part 5 — Deep Research Additions (2026-07-09, second pass)

Two additional gaps found in the deeper research pass:

### 🟡 P2-5 — `anthropic-user-profile-id` header (multi-tenant attribution) ✅ DONE

**What it is:** An optional request header that attributes an API call to a
specific user profile for multi-tenant billing/usage tracking. Requires the
`user-profiles` beta header alongside the `anthropic-user-profile-id`
header value.

**Current state:** Not implemented anywhere in the codebase before this
research.

**Implementation:** Added `user_profile_id` parameter to `Coder.__init__()`,
header injection in `Coder.generate()`, and `--user-profile PROFILE_ID`
CLI flag in `main.py`. Files: `coder.py`, `main.py`.

### 🟢 P2-6 — `claude-mythos-preview` missing from model catalog ✅ DONE

**What it is:** The Mythos Preview model (invitation-only, Project Glasswing)
was referenced in `SERVICE_TIER_UNSUPPORTED` and `INFERENCE_GEO_SUPPORTED`
sets but not present in the `MODEL_CATALOG` dict. `--model-info` and
`--list-models` couldn't report on it.

**Implementation:** Added full catalog entry for `claude-mythos-preview`
with mythos tier, 1M context, 128k output, adaptive thinking, and
Glasswing-only notes. File: `claude_models.py`.

---

## Part 6 — Product Surfaces Investigated But Not Gaps

Features confirmed as Claude Code product-specific (not API-level):
- **Teleport** (`claude --teleport`) — session transfer, no API endpoint
- **Channels** (Telegram/Discord/iMessage) — MCP plugin system, not API
- **Remote Control** — session continuation from mobile, no API endpoint
- **Background Agents** — parallel sessions, already covered by Managed Agents
- **Claude Science** — announced 2026-06-30, no public API yet
- **Claude Tag** — announced 2026-06-23, no public API yet
- **Claude Design** — announced product, no public API yet
- **Claude Security** — announced product, no public API yet

Features confirmed already implemented:
- **300k output tokens** — `claude_batch.py` (v1.11.1)
- **Scheduled deployments** — `claude_agents_sdk.py` (v1.21.0)
- **Webhooks** — `claude_agents_sdk.py` (v1.20.0)
- **Advisor tool** — `claude_advisor.py` (v1.11.0)
- **MCP connector** — `claude_agents_sdk.py`
- **Token counting** — `claude_tokens.py` (uses server-side tokenizer)

---

## Part 7 — SDK Changelog Cross-Reference (2026-07-09, third pass)

Cross-referenced the Anthropic Python SDK changelog (v0.76.0–v0.116.0,
Jan–Jul 2026) against the zaicoder codebase. SDK v0.116.0 is currently
installed.

### Gaps Found & Closed

#### 🟡 P2-7 — `output_tokens_details` / `thinking_tokens` capture ✅ DONE

**What it is:** The usage response now includes `output_tokens_details`
with a `thinking_tokens` field — a re-tokenized count of internal
reasoning tokens. Read-only, doesn't affect billing. Added in SDK
v0.105.0 (May 2026).

**Implementation:** Updated `claude_stream.py` to capture
`output_tokens_details.thinking_tokens` from `message_delta` streaming
events, plus `cache_creation_input_tokens` and `cache_read_input_tokens`
from `message_start`. Updated the usage display to show thinking, cache
write, and cache read tokens when present. Updated `claude_thinking.py`'s
`cmd_thinking` to extract and display `output_tokens_details.thinking_tokens`
from the usage response (replacing the incorrect `thinking_input_tokens`
field that was never actually populated by the API).

#### 🟢 P2-8 — `system_message` streaming event handler ✅ DONE

**What it is:** SDK v0.112.0 (Jun 2026) added `system.message` streaming
events that fire when mid-conversation system messages are processed.

**Implementation:** Added explicit `system_message` event handler in
`claude_stream.py`'s streaming loop. Events are acknowledged but don't
require action since the message content was already in the request.

### Features Already Present (confirmed by SDK cross-reference)

| SDK Version | Feature | zaicoder Status |
|---|---|---|
| v0.116.0 | `agent-memory-2026-07-22` beta | ✅ v1.19.0 |
| v0.115.0 | Agent overrides, event deltas | ✅ v1.22.0 |
| v0.115.0 | Vault credential injection scoping | ✅ v1.22.0 |
| v0.114.0 | `claude-sonnet-5` model | ✅ |
| v0.113.0 | Web fetch `20260318` | ✅ (this research) |
| v0.112.0 | User Profile ID | ✅ (this research) |
| v0.112.0 | Refusal categories | ✅ (this research) |
| v0.111.0 | Refusal-fallback middleware | ✅ `claude_fable5.py` |
| v0.110.0 | `code_execution_20260120` | ✅ |
| v0.109.0 | Deployments, env var credentials | ✅ |
| v0.108.0 | Fable 5/Mythos 5, server fallbacks | ✅ |
| v0.106.0 | Opus 4.1 deprecation | ✅ (this research) |
| v0.105.0 | Opus 4.8, mid-conv system blocks | ✅ v1.18.0 |
| v0.102.0 | Cache diagnostics beta | ✅ v1.18.0 |
| v0.100.0 | Multiagents, outcomes, webhooks | ✅ v1.20.0 |

### Known Deferred Items (not gaps — intentionally not built)

- **Self-hosted sandboxes** (SDK v0.103.0): Managed Agents feature for
  running agent sessions in user-provided sandbox environments. Requires
  infrastructure setup beyond a CLI wrapper's scope.
- **AWS client for Claude Platform on AWS** (SDK v0.101.0): zaicoder
  targets the direct Claude API only, not Bedrock/Foundry/Google Cloud.

---

## Part 8 — Code-Level Wiring Audit (2026-07-09, fourth pass)

Cross-referenced CLI flags against actual API request construction to
find parameters that are accepted from the user but never reach the API.

### Gap Found & Closed

#### 🔴 P1-5 — `output_config.effort` never sent on Messages API request ✅ DONE

**What it is:** The `--effort` CLI flag (low/medium/high/xhigh/max) was
accepted by argparse and used to map thinking budgets in
`claude_thinking.py`, but never sent as the `output_config.effort`
parameter on the actual Messages API request. This meant effort level
only affected thinking-token budgets, not the API-level reasoning
depth control that Opus 4.8 and Sonnet 5 both support.

**Root cause:** The `Coder` class in `coder.py` had no `effort` parameter
and never constructed `output_config` in the request payload. The
`--effort` flag in `main.py` was only passed to `cmd_thinking()` (the
thinking path), silently dropped for all other code paths.

**Implementation:** Added `effort` parameter to `Coder.__init__()`,
constructs `output_config: {"effort": ...}` in the request payload
when set, and wired `--effort` from `main.py` through to the `Coder`
constructor. Now `--effort high` on a plain `--prompt "..."` request
actually sends `output_config.effort: "high"` to the API.

Files: `coder.py`, `main.py`.

### Other Code Paths Audited (all confirmed wired)

| CLI Flag | Wired To | Status |
|---|---|---|
| `--service-tier` | `Coder.service_tier` → payload | ✅ |
| `--inference-geo` | `Coder.inference_geo` → payload | ✅ |
| `--fast-mode` | `Coder.fast_mode` → `speed: "fast"` | ✅ |
| `--user-profile` | `Coder.user_profile_id` → header | ✅ (pass 2) |
| `--effort` | `Coder.effort` → `output_config.effort` | ✅ (this pass) |
| `--thinking-display` | `ThinkingCoder.display` → thinking config | ✅ (pass 1) |
| `--search-response-inclusion` | `SearchCoder.search()` | ✅ (pass 1) |
| `--fetch-no-cache` | `SearchCoder.search(use_cache=False)` | ✅ (pass 1) |

---

## Part 9 — Dependency & Default Audit (2026-07-09, fifth pass)

Audited third-party dependencies and default model choices against
current upstream documentation.

### Gap Found & Closed

#### 🟢 P2-9 — Voyage embeddings default model outdated ✅ DONE

**What it is:** `claude_embeddings.py` defaulted to `voyage-3.5`, which
was superseded by the Voyage 4 series (released 2026-01-15). The Voyage
4 series includes `voyage-4` (balanced), `voyage-4-large` (best quality),
`voyage-4-lite` (latency-optimized), and `voyage-4-nano` (open-weight).
Also found: `voyage-context-4` (2026-06-29, contextualized chunk
embeddings for RAG) and `voyage-multimodal-3.5` (text+image+video).

**Implementation:** Updated `DEFAULT_MODEL` from `voyage-3.5` to
`voyage-4`, updated `main.py` `--embed-model` default, added module
docstring listing all available Voyage 4 models with descriptions.

Files: `claude_embeddings.py`, `main.py`.

### Other Module Defaults Audited (all current)

| Module | Default | Status |
|---|---|---|
| `claude_models.py` | `claude-sonnet-5` | ✅ Current |
| `claude_code_exec.py` | `code_execution_20260120` | ✅ Current |
| `claude_tools.py` | `web_search_20260318` | ✅ (pass 1) |
| `claude_tools.py` | `web_fetch_20260318` | ✅ (pass 1) |
| `claude_tools.py` | `memory_20250818` | ✅ Current |
| `claude_advisor.py` | `advisor_20260301` | ✅ Current |
| `claude_embeddings.py` | `voyage-4` | ✅ (this pass) |
| `requirements.txt` | `anthropic>=0.116.0` (was `>=0.75.0`) | ✅ (dependency pass) |

---

## Part 10 — SDK Introspection Pass (2026-07-09, sixth pass)

Directly inspected the installed `anthropic` SDK v0.116.0 Python client
for namespaces, methods, and types not covered by zaicoder.

### New SDK Namespaces Found

| Namespace | Methods | zaicoder Status |
|---|---|---|
| `beta.user_profiles` | create, list, retrieve, update, create_enrollment_url | ✅ **NEW** |
| `beta.deployment_runs` | list, retrieve | ✅ **NEW** |
| `beta.messages.parse` | Structured output parsing | Documented (covered by `claude_structured.py`) |
| `beta.agents` | Managed Agents CRUD | ✅ Existing |
| `beta.deployments` | Scheduled deployments | ✅ v1.21.0 |
| `beta.environments` | Managed environments | ✅ Existing |
| `beta.files` | Files API | ✅ Existing |
| `beta.memory_stores` | Memory stores | ✅ v1.19.0 |
| `beta.sessions` | Sessions | ✅ Existing |
| `beta.skills` | Platform Skills | ✅ v1.15.0 |
| `beta.vaults` | Credentials vault | ✅ Existing |
| `beta.webhooks` | Webhooks | ✅ v1.20.0 |

### Gaps Found & Closed

#### 🟡 P2-10 — Deployment runs history ✅ DONE

**What it is:** `deployment_runs` tracks the execution history of
scheduled deployments — each time a cron schedule fires, a new run is
created. Supports `list(deployment_id, has_error, trigger_type, ...)`
and `retrieve(run_id)`.

**Implementation:** Added `list_deployment_runs()` and
`get_deployment_run()` to `ManagedAgentsClient`, plus CLI commands
`cmd_agent_deployment_runs()`. New flags: `--agent-deployment-runs`,
`--agent-deployment-run-filter`, `--agent-deployment-run-id`,
`--agent-deployment-run-errors`. Files: `claude_agents_sdk.py`, `main.py`.

#### 🟡 P2-11 — User profiles CRUD management ✅ DONE

**What it is:** `user_profiles` manages the profile records used by
the `anthropic-user-profile-id` header (pass 2). The header attributes
requests to a profile; this API creates/lists/updates the profiles
themselves. Supports create/list/retrieve/update/create_enrollment_url.

**Implementation:** Added `create_user_profile()`, `list_user_profiles()`,
`get_user_profile()` to `ManagedAgentsClient`, plus CLI commands
`cmd_agent_user_profile_list()`, `cmd_agent_user_profile_create()`.
New flags: `--agent-user-profile-list`, `--agent-user-profile-create`,
`--agent-user-profile-external-id`. Files: `claude_agents_sdk.py`, `main.py`.

### Documented (Not Implemented — Already Covered)

- **`messages.parse`**: convenience method for structured output parsing
  via Pydantic models. `claude_structured.py` already handles structured
  outputs via `output_config.format` on the raw Messages API — the
  `parse()` method is an SDK convenience wrapper, not a new API surface.

### Intentionally Deferred (confirmed real, not gaps)

Following the same pattern as v1.20.0's deferred Multiagent orchestration:
real SDK features that exist but have no concrete use case yet in a CLI
wrapper. Documented here for the next audit cycle.

| SDK Namespace | Methods | Why Deferred |
|---|---|---|
| `sessions.threads` | archive, events, list, retrieve | Conversation branches within sessions — niche feature, sessions.events.send/stream already covers the common case |
| `environments.work` | ack, heartbeat, list, poll, retrieve, stats, stop, update | Self-hosted sandbox work management — requires infrastructure beyond CLI scope |
| `sessions.resources` | add, delete, list, retrieve, update | Post-creation resource CRUD — memory stores already mounted at session creation (v1.19.0) |
| `user_profiles.update` | update | Profile mutation — create/list/retrieve implemented; update is rarely needed |
| `user_profiles.create_enrollment_url` | create_enrollment_url | Enrollment URL generation — useful for onboarding flows, low priority |

### All `messages.create` Params Verified

Cross-referenced all 27 SDK `messages.create` parameters against zaicoder
coverage:

| Parameter | Status |
|---|---|
| `max_tokens`, `messages`, `model` | ✅ Core |
| `cache_control` | ✅ `claude_cache.py` |
| `container` | ✅ `claude_skills_api.py`, `claude_excel.py`, `claude_powerpoint.py` |
| `context_management` | ✅ `claude_tools.py` |
| `diagnostics` | ✅ `claude_cache.py` (cache diagnostics beta) |
| `fallback_credit_token` | ✅ `claude_fable5.py` |
| `fallbacks` | ✅ `claude_fable5.py` (server-side fallback) |
| `inference_geo` | ✅ `coder.py` |
| `mcp_servers` | ✅ `claude_agents_sdk.py` |
| `metadata` | ✅ Core |
| `output_config` | ✅ `coder.py` (effort), `claude_structured.py` (format) |
| `output_format` | ✅ `claude_structured.py` |
| `service_tier` | ✅ `coder.py` |
| `speed` | ✅ `coder.py` (fast_mode) |
| `stop_sequences` | ✅ Core |
| `stream` | ✅ `claude_stream.py` |
| `system` | ✅ Core |
| `temperature` | ✅ Core |
| `thinking` | ✅ `claude_thinking.py` |
| `tool_choice` | ✅ `claude_tools.py` |
| `tools` | ✅ `claude_tools.py` |
| `top_k`, `top_p` | ✅ Core |
| `user_profile_id` | ✅ `coder.py` (pass 2) |

---

## Part 11 — Engineering Blog & Cookbook (2026-07-09, seventh pass)

Reviewed Anthropic's engineering blog (9 posts, Jan–Apr 2026) for
implementation patterns that might reveal undocumented API features.

### Findings

| Blog Post | Key Insight | API Gap? |
|---|---|---|
| Auto Mode (Mar 25) | Model-based permission classifiers (input probe + transcript classifier) | No — application-level design pattern, not an API feature |
| Scaling Managed Agents (Apr 8) | Brain/hands architecture decoupling | No — internal architecture, not exposed via API |
| Harness Design (Mar 24) | Patterns for long-running dev sessions | No — client-side patterns |
| C Compiler with Parallel Claudes (Feb 5) | Multi-agent parallel processing | No — covered by `--agent-orchestrate` |
| Eval Awareness (Mar 6) | Model behavior in evaluations | No — behavioral observation |
| Infrastructure Noise (Feb 5) | Eval infrastructure variability | No — operational insight |
| AI-Resistant Evals (Jan 21) | Benchmark design methodology | No — benchmark design |
| Demystifying Evals (Jan 9) | Agent evaluation best practices | No — evaluation patterns |
| Claude Code Quality (Apr 23) | Code quality metrics | No — operational metrics |

**Conclusion:** The engineering blog posts describe application-level
design patterns and internal architecture, not new API surfaces. No
gaps identified. Auto Mode's three-tier permission architecture is a
sophisticated pattern that could inspire future zaicoder features but
is beyond the scope of an API wrapper.

### Anthropic Cookbook

The cookbook.claude.com domain was unreachable during this research.
The GitHub repository (anthropics/anthropic-cookbook) was accessed via
the GitHub API and its directory structure was verified. Cookbook
directories and their zaicoder coverage:

| Cookbook Directory | zaicoder Coverage |
|---|---|
| `capabilities/` (classification, RAG, summarization, text-to-sql) | `claude_rag.py`, `claude_structured.py` ✅ |
| `claude_agent_sdk/` (8 agent patterns, session browser, hosting) | `claude_agents_sdk.py`, `claude_tool_runner.py` ✅ |
| `extended_thinking/` | `claude_thinking.py` ✅ |
| `fable_5_fallback_billing/` | `claude_fable5.py` ✅ |
| `finetuning/` (Bedrock-only) | Out of scope (direct API only) |
| `managed_agents/` (13 CMA patterns, self-hosted sandboxes) | `claude_agents_sdk.py` ✅; sandboxes deferred |
| `tool_use/` (parallel, PTC, memory, compaction, pydantic, vision) | `claude_tools.py`, `claude_memory.py`, `claude_vision.py` ✅ |
| `skills/` | `claude_skills_api.py` ✅ |
| `evals/`, `tool_evaluation/` | `claude_evals.py`, `claude_eval.py` ✅ |
| `observability/` | `claude_observability.py`, `claude_metrics.py` ✅ |
| `patterns/` | Various modules ✅ |

**Conclusion:** All cookbook patterns use API features already
investigated and implemented in passes 1-6. No new API surfaces found.
