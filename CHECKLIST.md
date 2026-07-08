# CHECKLIST.md

**zcoder v1.16.0 — Roadmap Execution Checklist**
Derived from `ROADMAP.md` Part 2 (Gap Audit vs. `platform.claude.com/docs`, checked 2026-07-04).

Six confirmed gaps, ranked by priority. Check off each sub-task as it lands;
a priority group is only "done" when every box under it is checked **and**
the shared Definition of Done at the bottom passes.

All six items are now done — the sixth (Compliance API) was deliberately
held back in v1.15.0 pending a concrete request, which has since arrived
(see the P2 — Compliance API section below and `docs/30_upgrade_v1.16.0.md`).

---

## 🔴 P0 — Server-side fallback (`fallbacks` parameter) ✅ DONE
*Est. effort: ~1 file, ~60 lines, no new deps.*

- [x] Add `fallback_chain: list[str] = None` param to `Fable5Client.__init__`
- [x] In `call()`: when `fallback_chain` is set, add `payload["fallbacks"] = fallback_chain` (replacing, not supplementing, the manual retry path)
- [x] Rework `call_with_fallback()` into a thin compatibility wrapper:
  - [x] If `fallback_chain` is set → inspect `stop_reason` + which model served the response, no manual retry
  - [x] If `fallback_chain` is unset → fall through to the existing manual retry path
- [x] Add new CLI flag: `--fable5-fallback-chain MODEL1,MODEL2` (max 3 models total, including primary)
- [x] Update `claude_fable5.py` module docstring to document both patterns and when to use each:
  - [x] Manual retry → changing prompt/system before retrying
  - [x] `fallbacks` param → let the platform handle it in one round trip
- [x] Add/update tests covering both the `fallback_chain` path and the legacy manual path (`tests/test_claude_fable5.py`, 15 tests)

---

## 🟠 P1 — Context editing ✅ DONE (scope revised — see note)
*Est. effort: ~1 new file + 1 integration point, ~200 lines total.*

> **Correction found during implementation:** `claude_tools.py` already had
> a complete `build_context_management()` — the roadmap's audit missed it.
> No new `claude_context_editing.py` module was needed; the real gap was
> narrower (the agent loop just never called the existing function).

- [x] ~~Create new module `claude_context_editing.py`~~ — not needed, reused `claude_tools.build_context_management()`
- [x] Wire into `claude_code.py`'s agent loop behind an opt-in `--agent-context-editing` flag
- [x] Add a worked example under `docs/` showing Compaction + context editing used together in one long agent run (`docs/29_upgrade_v1.15.0.md`)
- [x] Confirm this does not change default behavior (opt-in only, `context_management=None` default)

---

## 🟠 P1 — Agent Skills via the API (`skill_id`) ✅ DONE (base client)
*Est. effort: ~1 new file for the base client, ~120 lines (excel/pptx integration is a separate follow-up).*

- [x] Create new module `claude_skills_api.py`
  - [x] `list_skills()` (static list of pre-built skills — no documented list endpoint for custom skills)
  - [x] `SkillRef` helper to build a `skill_id` reference for a Messages request
  - [x] CLI flag `--skills-list`
  - [x] CLI flag `--skills-info ID` (info-only, matching `claude_fable5.py`'s `cmd_fable5_info` pattern)
- [x] **Follow-up (landed this pass, ahead of schedule):** `--excel-native` / `--pptx-native` flags added to `claude_excel.py` / `claude_powerpoint.py`, routing through `claude_skills_api.py`'s `call_with_skills_turn()` while keeping the hand-rolled implementation as the fallback when Skills access isn't available

---

## 🟡 P2 — Usage and Cost API ✅ DONE
*Est. effort: ~1 file, ~100 lines. Requires an Admin API key.*

- [x] Create new module `claude_admin_api.py` (named per the roadmap's own suggested regrouping, see below)
  - [x] `get_usage_report(start, end, group_by)` wrapping the usage/cost endpoint (plus `get_cost_report`)
  - [x] CLI flag `--usage-report` that prints a table
- [x] Cross-link from `claude_cost_optimizer.py`'s docstring to the real reporting endpoint
- [x] Clearly flag in CLI help text / runtime error that this requires an **Admin API key** (not a regular key)

---

## 🟡 P2 — API key management (Admin API) ✅ DONE (list/revoke — create is N/A by design)
*Est. effort: ~80 lines, combined with the Usage API module.*

- [x] Decide module name: folded into `claude_admin_api.py` alongside the Usage API, per the roadmap's own suggested grouping
- [x] CLI flag `--admin-list-keys`
- [x] CLI flag `--admin-create-key NAME` — implemented as an explanation, not a real call: there's no documented create-key endpoint (Console-only, secret shown once), so this prints why instead of faking success
- [x] CLI flag `--admin-revoke-key ID`
- [x] Confirm Admin API auth requirements are documented alongside the Usage API ones

---

## 🟡 P2 — Compliance API ✅ DONE (v1.16.0)
*Est. effort: ~1 file, ~450 lines (client + all cmd_* wrappers). Requires a*
*Compliance Access Key for most endpoints; an Admin API key unlocks only*
*the Activity Feed.*

> **Reversal note:** v1.15.0 explicitly recommended leaving this as a
> documented gap. That recommendation's own stated exit condition — "revisit
> only if there's an actual concrete request for it" — has since been met,
> which is why this is now built. It is not a decision to build
> speculatively against a guessed shape; the endpoint family is confirmed
> against `platform.claude.com/docs/en/manage-claude/compliance-api*`
> (checked 2026-07-04).

- [x] Create new module `claude_compliance_api.py`
  - [x] `ComplianceApiClient` with the documented retry/backoff contract
        (429 + retryable 5xx back off exponentially 1s→60s; 400/401/403/
        404/409 never retry)
  - [x] Activity Feed: `list_activities()` / `iterate_activities()` with
        `since`/`until`/`activity_types`/`limit` filters and cursor-safe
        pagination (cursor only advances after a successful page)
  - [x] Chats: `list_chats()`/`iterate_chats()`, `get_chat_messages()`,
        `delete_chat()`
  - [x] Files: `download_file()` (with `Content-Disposition` filename
        parsing), `delete_file()`
  - [x] Projects: `list_projects()`, `get_project()`,
        `list_project_attachments()`, `delete_project()`
  - [x] Directory: `list_organizations()`, `list_org_users()`,
        `list_org_roles()`, `get_org_settings()`, `list_groups()`,
        `list_group_members()`
  - [x] Dry-run-by-default guard on every destructive `cmd_*`
        (`cmd_compliance_chat_delete`, `cmd_compliance_file_delete`,
        `cmd_compliance_project_delete`) — requires explicit `yes=True`
        (CLI: `--compliance-yes`), mirroring `claude_models.py`'s
        `--upgrade-all`/`--upgrade-yes` pattern
  - [x] Surfaces the documented 403 scope-mismatch message
        (`Got:`/`Needed:` scopes) with a concrete fix instead of a bare
        permission error, since Compliance Access Key vs. Admin API key
        reach differs per-endpoint
- [x] Add CLI flags (all under a new `Compliance API` argument group in
      `main.py`, dispatch mirrors the `claude_admin_api.py` block):
      `--compliance-api-key`, `--compliance-activities(-since/-until)`,
      `--compliance-activity-types`, `--compliance-activities-limit`,
      `--compliance-activities-all`, `--compliance-chats-list`,
      `--compliance-user-ids`, `--compliance-chat-messages`,
      `--compliance-chat-delete`, `--compliance-file-download`,
      `--compliance-file-delete`, `--compliance-projects-list`,
      `--compliance-project-info`, `--compliance-project-attachments`,
      `--compliance-project-delete`, `--compliance-orgs-list`,
      `--compliance-org-users`, `--compliance-org-roles`,
      `--compliance-org-settings`, `--compliance-groups-list`,
      `--compliance-group-members`, `--compliance-yes`,
      `--compliance-output`
- [x] Key fallback order: `--compliance-api-key` →
      `ANTHROPIC_COMPLIANCE_API_KEY` → `--admin-api-key` →
      `ANTHROPIC_ADMIN_API_KEY` (Admin key fallback only reaches the
      Activity Feed; every other flag 403s with a clear message)
- [x] Module docstring documents both key types and the endpoint-reach
      table, and cross-links `claude_admin_api.py` explaining how the two
      modules differ
- [x] Add tests (`tests/test_claude_compliance_api.py`, 28 tests): error
      classification/retry, exponential backoff on 429/retryable-5xx
      (never on 400/401/403/404/409), cursor-safety in `iterate_*`,
      `Content-Disposition` filename parsing, dry-run guard on every
      destructive `cmd_*`
- [x] Confirm this gap stays documented as *resolved* in `ROADMAP.md` /
      `README.md` (see `docs/30_upgrade_v1.16.0.md`)

---

## 🟠 P1 — Mid-conversation system messages ✅ DONE (v1.18.0)

> New feature, found in the v1.18.0 audit cycle (2026-07-08). Genuinely
> absent — zero matches for role:"system" message construction anywhere
> in the tree. Opus 4.8 only, no beta header.

- [x] `build_mid_system_message(text)` in `claude_cache.py`
- [x] `validate_system_message_placement(messages)` — all five documented
      placement rules, dedicated `SystemMessagePlacementError`
- [x] `MID_SYSTEM_SUPPORTED_MODELS` model gate (Opus 4.8 only)
- [x] Threaded through `generate_cached(mid_system=...)` and
      `multi_turn_cached(mid_system_updates=...)`
- [x] CLI: `--cache-multi-turn`, `--cache-mid-system`, `--cache-mid-system-after`
- [x] Add tests (`tests/test_claude_cache.py` — new file, 18 tests)

## 🟡 P2 — Cache diagnostics (beta) CLI wiring ✅ DONE (v1.18.0)

> Looked like a fresh gap on first grep (`cache_diagnostic` / `cache.diagnostic`
> matched nothing), but the feature was already fully built in
> `claude_cache.py` (`diagnose=`, the `cache-diagnosis-2026-04-07` beta
> header, `cache_miss_reason`) — just never reachable from `main.py`.

- [x] Add `--cache-diagnose` flag, wire to `cmd_cache_generate(diagnose=...)`
- [x] Add tests covering both the first-call and reference-prior-id cases
      (`tests/test_claude_cache.py`)

## 🟠 P1 — Managed Agents memory stores ✅ DONE (v1.19.0)

> New feature, found in the v1.19.0 audit cycle (2026-07-08) by checking
> the `anthropic` SDK's own changelog for drift, which surfaced the
> `agent-memory-2026-07-22` beta header. Genuinely absent — zero matches
> for `memory_store` or a `resources` param anywhere in
> `claude_agents_sdk.py`.

- [x] `ManagedAgentsClient.create_memory_store(name)` wraps
      `client.beta.memory_stores.create`
- [x] `create_session(..., memory_store_id=...)` mounts the store as a
      `resources` entry and adds the `agent-memory-2026-07-22` beta header
- [x] `cmd_agent_memory_store_create()` standalone helper
- [x] CLI: `--agent-memory-store NAME`, `--agent-memory-store-create`
- [x] Add tests (`tests/test_claude_agents_sdk.py` — new file, 10 tests,
      also covering pre-existing untested behavior per this cycle's scope)

## 🟠 P1 — Managed Agents Dreaming ✅ DONE (v1.20.0)

> New feature (research preview), found in the v1.20.0 audit cycle by
> re-checking the Managed Agents docs for what shipped alongside the
> memory-store feature. Genuinely absent — confirmed with two
> differently-worded greps (`dream`, then
> `curat|reflect.*session|memory.*consolidat`).

- [x] `ManagedAgentsClient.create_dream/.get_dream/.list_dreams/.cancel_dream`
      wrap `client.beta.dreams.*` with the `dreaming-2026-04-21` beta header
- [x] CLI: `--agent-dream`, `--agent-dream-sessions`,
      `--agent-dream-instructions`, `--agent-dream-list`, `--agent-dream-get`
- [x] Tests added (`tests/test_claude_agents_sdk.py`)

## 🟠 P1 — Managed Agents Outcomes ✅ DONE (v1.20.0)

> New feature (public beta). Genuinely absent — confirmed with two
> differently-worded greps (`define_outcome`, then
> `outcome_evaluation|rubric`).

- [x] `ManagedAgentsClient.define_outcome/.wait_for_outcome` send the
      `user.define_outcome` event and stream to a terminal
      `span.outcome_evaluation_end`
- [x] `cmd_managed_agent_run()` gains opt-in outcome params, falling
      through to the existing `run_task()` path when unset
- [x] CLI: `--agent-outcome`, `--agent-outcome-rubric`,
      `--agent-outcome-max-iter`
- [x] Tests added (`tests/test_claude_agents_sdk.py`)

## 🟡 P2 — Managed Agents Webhooks ✅ DONE (v1.20.0)

> New feature (public beta). Genuinely absent — grep for `webhook`
> matched only an unrelated docstring comment.

- [x] `ManagedAgentsClient.register_webhook()` wraps `client.beta.webhooks.create`
- [x] CLI: `--agent-webhook-register`, `--agent-webhook-events`
- [x] Tests added (`tests/test_claude_agents_sdk.py`)

## 🟡 P2 — Managed Agents native Multiagent orchestration ⏸ DEFERRED (v1.20.0)

> Confirmed real and absent (distinct from the pre-existing client-side
> `--agent-orchestrate`, which makes separate Messages API calls per
> subagent rather than sharing one Managed Agents session/sandbox).
> Deliberately not built this cycle — larger surface than the other
> three items, no concrete use case yet. See `ROADMAP.md`'s Priority
> Summary section for the full reasoning and exit condition. Matches how
> the Compliance API gap was handled between v1.15.0 and v1.16.0.

---

## Definition of Done (applies to every P0/P1/P2 item above)

- [x] New/changed code has a CLI flag consistent with existing house style (`--flag-name`) — verified: `--fable5-fallback-chain`, `--agent-context-editing`, `--skills-list`/`--skills-info`, `--usage-report`/`--cost-report`(+`-start`/`-end`/`-group-by`), `--admin-list-keys`/`--admin-revoke-key`/`--admin-create-key`, `--excel-native`/`--pptx-native`, the full `--compliance-*` group (23 flags), `--cache-diagnose`/`--cache-multi-turn`/`--cache-mid-system`/`--cache-mid-system-after`, `--agent-memory-store`/`--agent-memory-store-create`, and the new `--agent-dream*`/`--agent-outcome*`/`--agent-webhook-*` groups all wired in `main.py`
- [x] Module docstring updated to explain the feature and, where relevant, how it relates to an existing similar feature — confirmed in `claude_fable5.py`, `claude_code.py`, `claude_skills_api.py`, `claude_admin_api.py`, `claude_compliance_api.py`, `claude_cache.py`, `claude_agents_sdk.py`
- [x] Tests added or updated for the new code path — `tests/test_claude_fable5.py` (15), `tests/test_claude_code_context_editing.py` (6), `tests/test_claude_skills_api.py` (17), `tests/test_claude_admin_api.py` (10), `tests/test_claude_compliance_api.py` (28), `tests/test_claude_cache.py` (18), `tests/test_claude_agents_sdk.py` (26, up from 10 in v1.19.0); all 176 pass
- [x] `README.md` per-flag reference updated — "New in v1.15.0" section, "New in v1.16.0" section for the Compliance API, "New in v1.18.0" section, "New in v1.19.0" section, and a new "New in v1.20.0" section
- [x] `CHANGELOG.md` entry added — see "v1.15.0 — Roadmap gap-audit implementation", "v1.16.0 — Compliance API", "v1.18.0 — Mid-conversation system messages + Cache diagnostics CLI wiring", "v1.19.0 — Managed Agents memory stores", "v1.20.0 — Dreaming, Outcomes, Webhooks", and "v1.23.0 — Deep Web Research Cycle (18 gaps closed)"
- [x] No regression to existing default behavior — every new capability is opt-in (`context_management=None` default, `fallback_chain` unset falls through to the existing manual-retry path, Admin/Compliance API calls only fire when their flags are passed, every Compliance destructive op is dry-run unless `--compliance-yes` is also passed, `mid_system`/`mid_system_updates` default to `None`/`{}`, `diagnose` defaults to `False`, `memory_store_id` defaults to `None`, and `outcome_description`/`outcome_rubric` default to `None` so existing callers are unaffected; v1.23.0 additions: `display` defaults to `None` (API default), `effort` defaults to `None` (not sent unless set), `allow_manual` defaults to `False`, `response_inclusion`/`use_cache` default to `None`)
- [x] `ROADMAP.md` Part 1 coverage table updated to move the item from Part 2 (gap) into Part 1 (implemented) — confirmed present for all twelve implemented items (native Multiagent orchestration intentionally stays in the gap/defer section, not Part 1); v1.23.0 entries added via six audit cycle notes

---

## Priority Summary (for quick reference)

| Priority | Item | Status |
|---|---|---|
| 🔴 P0 | Server-side `fallbacks` param | ✅ Done (`claude_fable5.py`) |
| 🟠 P1 | Context editing | ✅ Done — wired existing `claude_tools.build_context_management()` into `claude_code.py` |
| 🟠 P1 | Agent Skills API (`skill_id`) | ✅ Done (`claude_skills_api.py`) — base client + `--excel-native`/`--pptx-native` follow-up both landed |
| 🟡 P2 | Usage and Cost API | ✅ Done (`claude_admin_api.py`) |
| 🟡 P2 | API key management | ✅ Done — list/revoke (`claude_admin_api.py`); create is N/A by design |
| 🟡 P2 | Compliance API | ✅ Done (`claude_compliance_api.py`, v1.16.0) — built once the recommendation's own "concrete request" condition was met |
| 🟠 P1 | Mid-conversation system messages | ✅ Done (`claude_cache.py`, v1.18.0) |
| 🟡 P2 | Cache diagnostics CLI wiring | ✅ Done (`claude_cache.py`/`main.py`, v1.18.0) |
| 🟠 P1 | Managed Agents memory stores | ✅ Done (`claude_agents_sdk.py`, v1.19.0) |
| 🟠 P1 | Managed Agents Dreaming | ✅ Done (`claude_agents_sdk.py`, v1.20.0) |
| 🟠 P1 | Managed Agents Outcomes | ✅ Done (`claude_agents_sdk.py`, v1.20.0) |
| 🟡 P2 | Managed Agents Webhooks | ✅ Done (`claude_agents_sdk.py`, v1.20.0) |
| 🟡 P2 | Managed Agents native Multiagent orchestration | ⏸ Deferred (v1.20.0) — real gap, no concrete use case yet |
| 🟠 P1 | Thinking `display: "omitted"` + adaptive gate | ✅ Done (`claude_thinking.py`, v1.23.0) |
| 🔴 P1 | `output_config.effort` wiring (was silently dropped) | ✅ Done (`coder.py`/`main.py`, v1.23.0) |
| 🟠 P1 | Server tool version drift (→ 20260318) | ✅ Done (`claude_tools.py`/`claude_search.py`, v1.23.0) |
| 🟡 P2 | User profiles CRUD + deployment runs | ✅ Done (`claude_agents_sdk.py`, v1.23.0) |
| 🟡 P2 | `output_tokens_details` / thinking tokens | ✅ Done (`claude_stream.py`/`claude_thinking.py`, v1.23.0) |
| 🟡 P2 | Voyage-4 embeddings + Opus 4.1 retirement + Mythos Preview | ✅ Done (`claude_embeddings.py`/`claude_models.py`, v1.23.0) |
