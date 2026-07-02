# Changelog

Full per-version detail lives in `docs/*_upgrade_*.md` — this file is a
high-level index. Two project lineages (`ai-coder-cli-v1`, the modular
`claude_*.py`-per-feature codebase, and `ai-coder-cli-v2`, a smaller
single-`coder.py` CLI with its own PyInstaller packaging) were merged into
this release; see "v1.12.0" below for exactly what came from where.

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


- Merged in `ai-coder-cli-v2`'s standalone-executable packaging: `build.sh`
  / `build.bat` (PyInstaller, produces a single `dist/ai-coder` binary with
  no local Python required), `setup.sh` / `setup.bat` (venv + `.env` setup
  for running from source), `ai-coder.spec`, `LICENSE` (MIT).
- Added `.env.example` (referenced by `setup.sh`/`setup.bat` but missing
  from both source projects) documenting `ANTHROPIC_API_KEY` (required),
  `VOYAGE_API_KEY` (optional, `claude_embeddings.py`), `GITHUB_TOKEN`
  (optional, `claude_github.py`).
- `requirements.txt`: bumped minimum `anthropic` SDK to `>=0.75.0`,
  required for `client.beta.agents/.environments/.sessions`
  (`--agent-managed-run`, see `claude_agents_sdk.ManagedAgentsClient`).
- Everything else in `ai-coder-cli-v2` (`coder.py`, `config.py`, `utils.py`,
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
