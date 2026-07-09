# IMPLEMENTATION CHECKLIST (Form) — zaicoder v1.16.0

Source: `ROADMAP.md` Part 2 — Gap Audit vs. `platform.claude.com/docs` (checked 2026-07-04)
One form per gap. All six gaps are now done — Forms 1–5 shipped in
v1.15.0, Form 6 (Compliance API) shipped in v1.16.0 once its own stated
exit condition ("revisit only if there's an actual concrete request for
it") was met. See `CHANGELOG.md`, `CHECKLIST.md`, and
`docs/29_upgrade_v1.15.0.md` / `docs/30_upgrade_v1.16.0.md` for the
narrative writeups this form-style tracker summarizes.

---

## Form 1 — 🔴 P0: Server-side fallback (`fallbacks` parameter)

| Field | Value |
|---|---|
| Priority | 🔴 P0 |
| Module(s) affected | `claude_fable5.py` |
| Est. effort | ~1 file, ~60 lines, no new deps |
| Owner | zaicoder maintainers |
| Target date | v1.15.0 |
| Status | ☐ Not started ☐ In progress ☐ In review ☑ Done |

**Task list**
- [x] Add `fallback_chain: list[str] = None` param to `Fable5Client.__init__`
- [x] `call()`: set `payload["fallbacks"] = fallback_chain` when provided (replaces manual path, not additive)
- [x] `call_with_fallback()` reworked into compatibility wrapper (fallback_chain path vs. legacy manual path)
- [x] New CLI flag `--fable5-fallback-chain MODEL1,MODEL2` (max 3 incl. primary)
- [x] Docstring updated: explain manual retry vs. `fallbacks` param, and when to use each
- [x] Tests added/updated for both code paths (`tests/test_claude_fable5.py`, 15 tests)

**Sign-off**
- Reviewed by: zaicoder maintainers  Date: v1.15.0 release
- Notes: Shipped as planned, no scope changes.

---

## Form 2 — 🟠 P1: Context editing

| Field | Value |
|---|---|
| Priority | 🟠 P1 |
| Module(s) affected | ~~New: `claude_context_editing.py`~~; integration: `claude_code.py` (see notes — no new module was needed) |
| Est. effort | ~1 new file + 1 integration point, ~200 lines (revised: 0 new files, ~1 integration point) |
| Owner | zaicoder maintainers |
| Target date | v1.15.0 |
| Status | ☐ Not started ☐ In progress ☐ In review ☑ Done |

**Task list**
- [x] ~~New module `claude_context_editing.py` mirroring `claude_cache.py` structure~~ — not needed
- [x] ~~`ContextEditingConfig` dataclass...`~~ — not needed
- [x] Function to build `context_management` payload block — already existed as `claude_tools.build_context_management()`
- [x] Wire into `claude_code.py` agent loop behind `--agent-context-editing` (opt-in)
- [x] Worked example added to `docs/` showing Compaction + context editing together (`docs/29_upgrade_v1.15.0.md`)
- [x] Confirm default behavior unchanged (opt-in only, `context_management=None` default)

**Sign-off**
- Reviewed by: zaicoder maintainers  Date: v1.15.0 release
- Notes: The original gap-audit was wrong about this one — `claude_tools.py`
  already had a complete `build_context_management()`, so no new module
  was created. The real gap was narrower: `claude_code.py`'s agent loop
  never called it. Module(s) affected / Est. effort above are struck
  through rather than deleted, to keep an honest record of what the audit
  originally assumed vs. what was actually true.

---

## Form 3 — 🟠 P1: Agent Skills via the API (`skill_id`)

| Field | Value |
|---|---|
| Priority | 🟠 P1 |
| Module(s) affected | New: `claude_skills_api.py`; follow-up: `claude_excel.py`, `claude_powerpoint.py` |
| Est. effort | ~1 new file, ~120 lines (excel/pptx integration is a separate follow-up) |
| Owner | zaicoder maintainers |
| Target date | v1.15.0 |
| Status | ☐ Not started ☐ In progress ☐ In review ☑ Done |

**Task list**
- [x] New module `claude_skills_api.py`
- [x] `list_skills()` wrapper
- [x] `SkillRef` helper for `skill_id` in Messages requests
- [x] CLI flag `--skills-list`
- [x] CLI flag `--skills-info ID` (info-only, matches `cmd_fable5_info` pattern)
- [x] **Follow-up PR (separate, not this one):** `--excel-native` / `--pptx-native` flags on `claude_excel.py` / `claude_powerpoint.py`, existing hand-rolled logic kept as fallback — landed in the same v1.15.0 pass, ahead of the original schedule

**Sign-off**
- Reviewed by: zaicoder maintainers  Date: v1.15.0 release
- Notes: Follow-up item landed early rather than as a separate PR; no
  regression to the fallback path when Skills access isn't available.

---

## Form 4 — 🟡 P2: Usage and Cost API

| Field | Value |
|---|---|
| Priority | 🟡 P2 |
| Module(s) affected | New: `claude_admin_api.py` (renamed from planned `claude_usage_api.py`, folded with Form 5); cross-link: `claude_cost_optimizer.py` |
| Est. effort | ~1 file, ~100 lines. Requires Admin API key |
| Owner | zaicoder maintainers |
| Target date | v1.15.0 |
| Status | ☐ Not started ☐ In progress ☐ In review ☑ Done |

**Task list**
- [x] New module `claude_admin_api.py`
- [x] `get_usage_report(start, end, group_by)` wrapper (plus `get_cost_report`)
- [x] CLI flag `--usage-report` (prints table)
- [x] Cross-link from `claude_cost_optimizer.py` docstring
- [x] CLI help text clearly flags Admin API key requirement (avoid silent 401)

**Sign-off**
- Reviewed by: zaicoder maintainers  Date: v1.15.0 release
- Notes: Named `claude_admin_api.py`, not `claude_usage_api.py` — see
  Form 5, folded into the same module.

---

## Form 5 — 🟡 P2: API key management (Admin API)

| Field | Value |
|---|---|
| Priority | 🟡 P2 |
| Module(s) affected | `claude_admin_api.py` |
| Est. effort | ~80 lines, combined with Usage API module |
| Owner | zaicoder maintainers |
| Target date | v1.15.0 |
| Status | ☐ Not started ☐ In progress ☐ In review ☑ Done (list/revoke — create is N/A by design) |

**Task list**
- [x] Decide module grouping — folded into `claude_admin_api.py` alongside Usage API
- [x] CLI flag `--admin-list-keys`
- [x] CLI flag `--admin-create-key NAME` — implemented as an explanation, not a real call: no documented create-key endpoint exists (Console-only, secret shown once), so this prints why rather than faking success
- [x] CLI flag `--admin-revoke-key ID`
- [x] Admin API auth requirements documented alongside Usage API

**Sign-off**
- Reviewed by: zaicoder maintainers  Date: v1.15.0 release
- Notes: `--admin-create-key` deliberately does not call an endpoint —
  see the module docstring for why that's a documented boundary, not a
  gap.

---

## Form 6 — 🟡 P2: Compliance API

| Field | Value |
|---|---|
| Priority | 🟡 P2 |
| Module(s) affected | New: `claude_compliance_api.py`; integration: `main.py` (new `Compliance API` argument group + dispatch block) |
| Est. effort | Originally estimated N/A (documented gap only); actual: ~450 lines (client + all `cmd_*` wrappers) |
| Owner | zaicoder maintainers |
| Target date | v1.16.0 |
| Status | ☐ Documented gap (default) ☑ Reconsidered — built |

**Task list**
- [x] Confirm gap remained documented in `ROADMAP.md` / `README.md` through v1.15.0
- [x] No speculative implementation in v1.15.0 — waited, as recommended
- [x] Revisit trigger arrived: the Compliance API is now real and documented
  at `platform.claude.com/docs/en/manage-claude/compliance-api*`
  (confirmed 2026-07-04), which is the "concrete request" condition the
  v1.15.0 recommendation named
- [x] `ComplianceApiClient`: documented retry contract (429 + retryable
  5xx back off exponentially 1s→60s; 400/401/403/404/409 never retry)
- [x] Activity Feed: list + cursor-safe pagination (`iterate_activities`)
- [x] Chats: list, get messages, hard-delete
- [x] Files: download (with `Content-Disposition` filename parsing), hard-delete
- [x] Projects: list, info, attachments, hard-delete
- [x] Directory: orgs, org users, org roles, org settings, groups, group members
- [x] Dry-run-by-default guard on every destructive `cmd_*`, requires
  explicit `yes=True` (`--compliance-yes`)
- [x] Surfaces the documented 403 scope-mismatch message with a concrete
  fix instead of a bare permission error
- [x] 23 new CLI flags wired into `main.py` under a `Compliance API`
  argument group, dispatch mirrors `claude_admin_api.py`'s block
- [x] Key fallback order documented: `--compliance-api-key` →
  `ANTHROPIC_COMPLIANCE_API_KEY` → `--admin-api-key` →
  `ANTHROPIC_ADMIN_API_KEY` (Admin key fallback reaches only the Activity
  Feed endpoint)
- [x] Tests: `tests/test_claude_compliance_api.py`, 28 tests, all passing

**Sign-off**
- Reviewed by: zaicoder maintainers  Date: v1.16.0 release
- Notes: This is not a reversal of the v1.15.0 "leave as a gap" call —
  that recommendation's own stated exit condition was met, so building
  it now is consistent with the original plan, not a departure from it.

---

## Form 7 — 🟠 P1: Mid-conversation system messages

| Field | Value |
|---|---|
| Module(s) affected | `claude_cache.py`; integration: `main.py` (new `Prompt Caching` group flags + dispatch) |
| Est. effort | ~150 lines (builder + validator + threading through `generate_cached()`/`multi_turn_cached()`) |
| Owner | zaicoder maintainers |
| Target date | v1.18.0 |
| Status | ☑ Done |

**Task list**
- [x] Confirmed genuinely absent — zero matches for `role.*system` message
  construction anywhere in the tree outside test fixtures, not just no
  module with a matching name
- [x] `build_mid_system_message(text)` — builds the `{"role": "system", ...}`
  message block (text-only content, per docs)
- [x] `validate_system_message_placement(messages)` — encodes all five
  documented placement rules (not first entry; not adjacent to another
  system message; must follow a user turn or an assistant turn ending in
  server tool use; cannot sit between a tool_use and its tool_result; must
  be the last entry or followed by an assistant turn) and raises a
  dedicated `SystemMessagePlacementError` naming which rule failed
- [x] `MID_SYSTEM_SUPPORTED_MODELS = {"claude-opus-4-8"}` model gate, since
  this feature is Opus 4.8 only (no beta header) per docs
- [x] `mid_system` param threaded through `generate_cached()`
- [x] `mid_system_updates` (turn-index → text map) threaded through
  `multi_turn_cached()` — the realistic use case, since the placement
  rules require existing conversation history to attach to
- [x] CLI: `--cache-multi-turn TEXT [TEXT...]`, `--cache-mid-system TEXT`,
  `--cache-mid-system-after N`, dispatched via new `cmd_cache_multi_turn()`
- [x] Confirm default behavior unchanged — `mid_system`/`mid_system_updates`
  both default to `None`/`{}`, no effect unless explicitly passed
- [x] Tests: `tests/test_claude_cache.py` (new file — this module had zero
  test coverage before this cycle)

**Sign-off**
- Reviewed by: zaicoder maintainers  Date: v1.18.0 release
- Notes: Placement validation runs client-side before the request goes
  out, so a misplaced system message fails fast with a specific message
  instead of spending a round trip on the API's 400.

---

## Form 8 — 🟡 P2: Cache diagnostics (beta) — CLI wiring

| Field | Value |
|---|---|
| Module(s) affected | `main.py` only — `claude_cache.py`'s client-side support already existed |
| Est. effort | ~10 lines (one flag, one kwarg passthrough) |
| Owner | zaicoder maintainers |
| Target date | v1.18.0 |
| Status | ☑ Done |

**Task list**
- [x] Initial grep for `cache_diagnostic`/`cache.diagnostic` found nothing
  and looked like a fresh P1/P2 gap
- [x] Read `claude_cache.py` directly before writing new code (per the
  Methodology note's "confirm with a second grep" correction) — found
  `diagnose=` on `generate_cached()`, the `cache-diagnosis-2026-04-07`
  beta header, the `diagnostics.previous_message_id` request field, and
  `cache_miss_reason` surfaced through `cache_stats()`/`print_cache_stats()`
  already fully implemented
- [x] Real gap identified: `main.py` never set `diagnose=True` anywhere —
  the feature was unreachable from the CLI despite being fully built
- [x] Added `--cache-diagnose` flag, wired to `cmd_cache_generate(diagnose=...)`
- [x] Tests: `tests/test_claude_cache.py` covers the `diagnose=True` request
  shape (both the first-call `previous_message_id: None` case and the
  second-call reference-prior-id case) and the beta header

**Sign-off**
- Reviewed by: zaicoder maintainers  Date: v1.18.0 release
- Notes: Not a reversal or correction of any prior claim — Part 1 of
  `ROADMAP.md` always listed Prompt caching as covered by `claude_cache.py`
  and that was accurate; this was a CLI-reachability gap, not a coverage
  gap.

---

## Form 9 — 🟠 P1: Managed Agents memory stores

| Field | Value |
|---|---|
| Module(s) affected | `claude_agents_sdk.py`, `main.py` |
| Est. effort | ~90 lines + tests |
| Owner | zaicoder maintainers |
| Target date | v1.19.0 |
| Status | ☑ Done |

**Task list**
- [x] Found via `requirements.txt` SDK-drift check (step 6 of the audit
  methodology), not a direct docs-feature-list grep: `anthropic-sdk-python`
  v0.116.0's changelog mentions a new `agent-memory-2026-07-22` beta
  header, which led to the Managed Agents memory-store docs pages
- [x] Confirmed absence with two differently-worded greps
  (`memory_store` and `memory.?store|agent-memory|resources.*memory`)
  before concluding it was a real gap
- [x] Checked the other two "memory" features already in the tree
  (`claude_memory.py`'s `memory_20250818` tool, Claude Code's local
  `MEMORY.md`) to confirm neither already implements this under a
  different name — confirmed they don't; different scope and storage
  model each
- [x] Added `ManagedAgentsClient.create_memory_store(name)`
- [x] Added `memory_store_id` param to `create_session()`, mounting a
  `{"type": "memory_store", "memory_store_id": ...}` `resources` entry
  and the new beta header when set
- [x] Added `cmd_agent_memory_store_create()` standalone helper
- [x] `cmd_managed_agent_run()` gained an optional `memory_store` param
- [x] CLI: `--agent-memory-store NAME`, `--agent-memory-store-create`
- [x] Tests: new `tests/test_claude_agents_sdk.py` (10 tests) — module
  had zero coverage before this cycle, so also covers pre-existing
  `PermissionMode`, `TOOL_PRESETS`, and `MANAGED_AGENTS_BETA`

**Sign-off**
- Reviewed by: zaicoder maintainers  Date: v1.19.0 release
- Notes: Purely additive — `memory_store_id` defaults to `None` and
  `create_session()`'s existing callers are unaffected; `--agent-managed-run`
  behaves exactly as before when `--agent-memory-store` isn't passed.

---

## Form 10 — 🟠 P1 / 🟡 P2: Dreaming, Outcomes, Webhooks (native Multiagent orchestration deferred)

| Field | Value |
|---|---|
| Module(s) affected | `claude_agents_sdk.py`, `main.py` |
| Est. effort | ~180 lines + tests |
| Owner | zaicoder maintainers |
| Target date | v1.20.0 |
| Status | ☑ Done (Dreaming, Outcomes, Webhooks) / ⏸ Deferred (native Multiagent orchestration) |

**Task list**
- [x] Re-checked Managed Agents docs for what shipped alongside the
  memory-store feature closed in v1.19.0 (per this cycle's step 6),
  surfacing Dreaming, Outcomes, Webhooks, and native Multiagent
  orchestration as candidates
- [x] Confirmed each candidate's absence with two differently-worded
  greps before writing it up: Dreaming (`dream`, then
  `curat|reflect.*session|memory.*consolidat`); Outcomes
  (`define_outcome`, then `outcome_evaluation|rubric`); Webhooks
  (`webhook`, only an unrelated comment matched); native Multiagent
  orchestration (`multiagent|coordinator.*agents`, confirmed distinct
  from the pre-existing client-side `--agent-orchestrate` by reading
  the code directly, not just grep output)
- [x] Added `ManagedAgentsClient.create_dream/.get_dream/.list_dreams/.cancel_dream`
  (`dreaming-2026-04-21` beta header)
- [x] Added `ManagedAgentsClient.define_outcome/.wait_for_outcome`;
  `cmd_managed_agent_run()` gained opt-in outcome params
- [x] Added `ManagedAgentsClient.register_webhook`
- [x] CLI: `--agent-dream(-sessions/-instructions/-list/-get)`,
  `--agent-outcome(-rubric/-max-iter)`, `--agent-webhook-register`,
  `--agent-webhook-events`
- [x] Tests: 16 new tests added to `tests/test_claude_agents_sdk.py`
  (26 total in that file)
- [ ] Native Multiagent orchestration — deliberately not implemented
  this cycle; see `ROADMAP.md`'s Priority Summary section for the full
  reasoning and stated exit condition

**Sign-off**
- Reviewed by: zaicoder maintainers  Date: v1.20.0 release
- Notes: All three shipped features are purely additive —
  `outcome_description`/`outcome_rubric` default to `None` so
  `cmd_managed_agent_run()`'s existing plain-task behavior is unchanged
  when they're not passed. Native Multiagent orchestration intentionally
  left open with a stated exit condition, matching the Compliance API
  precedent from v1.15.0 → v1.16.0.

---

## Shared Definition of Done (all forms)

- [x] CLI flag follows house naming style (`--flag-name`)
- [x] Module docstring documents the feature and its relationship to any similar existing feature
- [x] Tests added/updated
- [x] `README.md` per-flag reference updated
- [x] `CHANGELOG.md` entry added
- [x] No regression to existing default behavior
- [x] `ROADMAP.md` updated — item moved from Part 2 (gap) to Part 1 (implemented)

## Rollup Status

| # | Item | Priority | Status |
|---|---|---|---|
| 1 | Server-side `fallbacks` param | 🔴 P0 | ✅ Done (v1.15.0) |
| 2 | Context editing | 🟠 P1 | ✅ Done (v1.15.0) |
| 3 | Agent Skills API (`skill_id`) | 🟠 P1 | ✅ Done (v1.15.0) |
| 4 | Usage and Cost API | 🟡 P2 | ✅ Done (v1.15.0) |
| 5 | API key management | 🟡 P2 | ✅ Done (v1.15.0) |
| 6 | Compliance API | 🟡 P2 | ✅ Done (v1.16.0) |
| 7 | Mid-conversation system messages | 🟠 P1 | ✅ Done (v1.18.0) |
| 8 | Cache diagnostics CLI wiring | 🟡 P2 | ✅ Done (v1.18.0) |
| 9 | Managed Agents memory stores | 🟠 P1 | ✅ Done (v1.19.0) |
| 10a | Managed Agents Dreaming | 🟠 P1 | ✅ Done (v1.20.0) |
| 10b | Managed Agents Outcomes | 🟠 P1 | ✅ Done (v1.20.0) |
| 10c | Managed Agents Webhooks | 🟡 P2 | ✅ Done (v1.20.0) |
| 10d | Managed Agents native Multiagent orchestration | 🟡 P2 | ⏸ Deferred (v1.20.0) |
| 11a | Thinking `display: "omitted"` | 🟠 P1 | ✅ Done (v1.23.0) |
| 11b | `effort: "xhigh"` + `output_config.effort` wiring | 🔴 P1 | ✅ Done (v1.23.0) |
| 11c | Adaptive-only model gate (`THINKING_ADAPTIVE_ONLY`) | 🟠 P1 | ✅ Done (v1.23.0) |
| 11d | Server tool version drift (→ 20260318) | 🟠 P1 | ✅ Done (v1.23.0) |
| 12a | `anthropic-user-profile-id` header | 🟡 P2 | ✅ Done (v1.23.0) |
| 12b | User profiles CRUD management | 🟡 P2 | ✅ Done (v1.23.0) |
| 12c | Deployment runs history | 🟡 P2 | ✅ Done (v1.23.0) |
| 13a | `output_tokens_details` / thinking tokens capture | 🟡 P2 | ✅ Done (v1.23.0) |
| 13b | Voyage embeddings default (→ voyage-4) | 🟢 P2 | ✅ Done (v1.23.0) |
| 13c | Opus 4.1 upcoming retirement tracking | 🟡 P2 | ✅ Done (v1.23.0) |
| 13d | `claude-mythos-preview` model catalog entry | 🟢 P2 | ✅ Done (v1.23.0) |
