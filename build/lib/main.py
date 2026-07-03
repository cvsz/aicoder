#!/usr/bin/env python3
"""
main.py — AI Model Coder CLI
Version 1.12.0 "Release" | Standalone packaging merged in from the
ai-coder-cli-v2 lineage (PyInstaller build, setup scripts, LICENSE) —
no functional/API changes from v1.11.1, this is a packaging-only release
"""
import argparse
import os
import sys

# Both are tiny, dependency-free dicts (no urllib/API calls at import time),
# so importing them eagerly to build argparse `choices=` is cheap and keeps
# the CLI's advertised choices in sync with the actual data instead of a
# second hardcoded list drifting from it.
from core.personalities import PERSONALITIES

VERSION = "1.12.1"
BANNER  = f"\033[94mAI Model Coder CLI v{VERSION}\033[0m"

# Named agent roles. Previously these seven names only existed as a
# print-only list under --list-agents (main.py:447 in v1.11.1) with no
# backing data anyone could actually use — --agent accepted a value that
# was silently discarded. One-line system-prompt per role, in the same
# spirit as personalities.py's PERSONALITIES table.
AGENT_SYSTEM_PROMPTS = {
    "code_generator":       "You are a full-project code generation agent. Produce complete, "
                             "runnable code for the request, not a partial sketch.",
    "code_reviewer":        "You are a code review agent. Focus on correctness, readability, "
                             "and maintainability; call out concrete issues with line-level detail.",
    "testing_agent":        "You are a testing agent. Produce comprehensive test suites, "
                             "covering edge cases and failure modes, not just the happy path.",
    "documentation_agent":  "You are a documentation agent. Write clear docs, READMEs, and API "
                             "references aimed at a reader new to this codebase.",
    "optimizer":            "You are a performance optimization agent. Identify concrete "
                             "bottlenecks and propose measurable improvements.",
    "security_auditor":     "You are a security audit agent. Review for vulnerabilities "
                             "(injection, auth, secrets handling, unsafe deserialization, etc.) "
                             "and rate severity for each finding.",
    "full_stack":           "You are a full-stack engineering agent. Consider frontend, backend, "
                             "and data-layer concerns together when responding.",
}


def _api_key(args):
    k = getattr(args, "api_key", None) or os.getenv("ANTHROPIC_API_KEY", "")
    if not k:
        print("[ERROR] ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)
    return k

def _model(args):
    return getattr(args, "model", "claude-sonnet-5") or "claude-sonnet-5"

def _read_file(path):
    try:
        return open(path).read()
    except Exception as e:
        print(f"[ERROR] Cannot read {path}: {e}", file=sys.stderr)
        sys.exit(1)


def build_parser():
    from api.claude_models import UPGRADE_TARGETS
    p = argparse.ArgumentParser(prog="ai-coder",
        description=f"AI Model Coder CLI v{VERSION}",
        formatter_class=argparse.RawTextHelpFormatter)

    g = p.add_argument_group("Global")
    g.add_argument("-p", "--prompt");  g.add_argument("-f", "--file")
    g.add_argument("-o", "--output");  g.add_argument("-i", "--interactive", action="store_true")
    g.add_argument("--model", default="claude-sonnet-5")
    g.add_argument("--temperature", type=float, default=0.3)
    g.add_argument("--max-tokens", type=int, default=4096, dest="max_tokens")
    g.add_argument("--api-key", default="", dest="api_key")
    g.add_argument("--version", action="store_true")
    g.add_argument("--service-tier", choices=["auto", "standard_only"], default=None,
                   dest="service_tier",
                   help="Priority Tier routing (requires an existing capacity "
                        "commitment; not supported on Sonnet 5 or Mythos-tier models)")
    g.add_argument("--inference-geo", choices=["us", "global"], default=None,
                   dest="inference_geo",
                   help="Data residency: 'us' pins inference to US data centers "
                        "at 1.1x pricing (Opus 4.6+/Sonnet 4.6+ only)")
    g.add_argument("--fast-mode", action="store_true", dest="fast_mode",
                   help="Research-preview reduced-latency mode (speed:\"fast\"); "
                        "currently Opus-only and billed at a premium rate")

    sa = p.add_argument_group("Skills & Agents")
    # --skill/--agent were accepted by the parser and never read anywhere
    # (no args.skill / args.agent reference existed in this file at all) —
    # picking a skill or agent silently had zero effect on the request.
    # Now: --skill injects that skill's description into the system prompt,
    # --agent injects a role prompt for one of the named roles --list-agents
    # already prints (previously the only place those names existed), and
    # --personality was the same story one module over — personalities.py's
    # PersonalityManager was fully implemented and even wired into
    # coder.py's Coder.generate() via personality_style, but nothing in
    # main.py ever passed personality_style to a Coder(...) call because
    # there was no flag to source it from.
    sa.add_argument("--skill", help="Prepend a named skill's system prompt (see --list-skills)")
    sa.add_argument("--agent", choices=sorted(AGENT_SYSTEM_PROMPTS),
                    help="Prepend a named agent role's system prompt (see --list-agents)")
    sa.add_argument("--personality", choices=sorted(PERSONALITIES),
                    help="Apply a response style/personality (see --list-personalities)")
    sa.add_argument("--list-skills", action="store_true")
    sa.add_argument("--list-agents", action="store_true")
    sa.add_argument("--list-personalities", action="store_true", dest="list_personalities")

    pr = p.add_argument_group("Feature Projects")
    pr.add_argument("--project-create", metavar="NAME")
    pr.add_argument("--project-list", action="store_true")
    pr.add_argument("--project-show", metavar="ID")
    pr.add_argument("--project-plan", metavar="ID")
    pr.add_argument("--project-run", metavar="ID")
    pr.add_argument("--project-add-task", metavar="ID")
    pr.add_argument("--project-delete", metavar="ID")
    pr.add_argument("--project-archive", metavar="ID")
    pr.add_argument("--project-templates", action="store_true")
    pr.add_argument("--project-template", default="blank")
    pr.add_argument("--project-desc", default="")
    pr.add_argument("--task", metavar="TASK_ID")
    pr.add_argument("--task-title", default="")
    pr.add_argument("--task-desc", default="")
    pr.add_argument("--task-agent", default="")
    pr.add_argument("--task-priority", default="medium")

    ar = p.add_argument_group("Artifacts")
    ar.add_argument("--artifact-create", metavar="NAME")
    ar.add_argument("--artifact-list", action="store_true")
    ar.add_argument("--artifact-show", metavar="ID")
    ar.add_argument("--artifact-iterate", metavar="ID")
    ar.add_argument("--artifact-export", metavar="ID")
    ar.add_argument("--artifact-export-all", metavar="PROJ_ID")
    ar.add_argument("--artifact-tag", metavar="ID")
    ar.add_argument("--artifact-attach", metavar="ART_ID")
    ar.add_argument("--artifact-diff", metavar="ID")
    ar.add_argument("--artifact-delete", metavar="ID")
    ar.add_argument("--artifact-types", action="store_true")
    ar.add_argument("--artifact-type", default="code")
    ar.add_argument("--artifact-lang", default="")
    ar.add_argument("--artifact-tags", default="")
    ar.add_argument("--artifact-version", type=int)
    ar.add_argument("--artifact-query", default="")
    ar.add_argument("--artifact-project", default="")
    ar.add_argument("--tag", default="")
    ar.add_argument("--to-project", default="")
    ar.add_argument("--v1", type=int); ar.add_argument("--v2", type=int)
    ar.add_argument("--artifact-output-dir", default="")

    th = p.add_argument_group("Extended Thinking")
    th.add_argument("--thinking", action="store_true")
    th.add_argument("--thinking-budget", type=int, default=8000, dest="thinking_budget")
    th.add_argument("--effort", default="", choices=["","low","medium","high","max"])
    th.add_argument("--adaptive", action="store_true")
    th.add_argument("--interleaved-thinking", action="store_true", dest="interleaved_thinking")
    th.add_argument("--show-thinking", action="store_true", dest="show_thinking")

    p.add_argument("--stream", action="store_true")

    ws = p.add_argument_group("Web Search & Fetch")
    ws.add_argument("--web-search", action="store_true")
    ws.add_argument("--web-fetch", action="store_true")
    ws.add_argument("--max-searches", type=int, default=5, dest="max_searches")
    ws.add_argument("--no-citations", action="store_true", dest="no_citations")
    ws.add_argument("--fetch-url", metavar="URL", dest="fetch_url")

    vi = p.add_argument_group("Vision")
    vi.add_argument("--vision", metavar="FILE")
    vi.add_argument("--vision-pdf", metavar="FILE", dest="vision_pdf")
    vi.add_argument("--vision-url", metavar="URL", dest="vision_url")
    vi.add_argument("--vision-code", action="store_true", dest="vision_code")
    vi.add_argument("--vision-compare", nargs=2, metavar="FILE", dest="vision_compare")
    vi.add_argument("--vision-ocr", metavar="FILE", dest="vision_ocr")
    vi.add_argument("--vision-lang", default="auto", dest="vision_lang")

    ba = p.add_argument_group("Batch API")
    ba.add_argument("--batch-submit", metavar="FILE", dest="batch_submit")
    ba.add_argument("--batch-status", metavar="ID", dest="batch_status")
    ba.add_argument("--batch-results", metavar="ID", dest="batch_results")
    ba.add_argument("--batch-cancel", metavar="ID", dest="batch_cancel")
    ba.add_argument("--batch-list", action="store_true", dest="batch_list")
    ba.add_argument("--batch-wait", action="store_true", dest="batch_wait")
    ba.add_argument("--batch-generate", type=int, default=0, dest="batch_generate")
    ba.add_argument("--batch-300k-output", action="store_true", dest="batch_300k_output",
                    help="Opt into 300k max output tokens per request (beta "
                         "output-300k-2026-03-24), Opus 4.8/4.7/4.6 and Sonnet 5/4.6 only")

    ca = p.add_argument_group("Prompt Caching")
    ca.add_argument("--cache", action="store_true")
    ca.add_argument("--cache-ttl", default="5m", choices=["5m","1h"], dest="cache_ttl")
    ca.add_argument("--cache-warm", action="store_true", dest="cache_warm")
    ca.add_argument("--cache-system", default="", dest="cache_system")
    ca.add_argument("--cache-stats", action="store_true", dest="cache_stats",
                    help="With --cache: print token/hit-rate stats after the response "
                         "(previously accepted by the parser but never read anywhere, "
                         "so it had no effect either way — --cache always silently "
                         "printed stats and there was no way to turn that off)")
    ca.add_argument("--cache-docs", nargs="+", metavar="FILE", dest="cache_docs")

    tu = p.add_argument_group("Tool Use")
    tu.add_argument("--tool-agent", action="store_true", dest="tool_agent")
    tu.add_argument("--server-tool", metavar="TOOL", dest="server_tool")
    tu.add_argument("--list-server-tools", action="store_true", dest="list_server_tools")
    tu.add_argument("--max-turns", type=int, default=10, dest="max_turns")
    tu.add_argument("--memory-agent", metavar="PROMPT", dest="memory_agent",
                    help="Run an agent loop backed by the native memory tool (memory_20250818)")
    tu.add_argument("--memory-dir", default="~/.ai-coder/memory", dest="memory_dir",
                    help="Local directory backing --memory-agent (default: ~/.ai-coder/memory)")
    tu.add_argument("--context-management", action="store_true", dest="context_management",
                    help="With --server-tool: auto-clear stale tool results on long calls "
                         "(context-management-2025-06-27 beta)")
    tu.add_argument("--compaction", action="store_true", dest="compaction",
                    help="With --server-tool: enable server-side conversation compaction "
                         "(compact_20260112 beta) instead of / alongside clear_tool_uses")
    tu.add_argument("--task-budget", type=int, default=0, dest="task_budget",
                    help="With --server-tool: advisory task_budget in tokens for the full "
                         "agentic loop (task-budgets-2026-03-13 beta; Opus 4.7/4.8, "
                         "Fable 5, Mythos 5 only)")
    tu.add_argument("--ptc", action="store_true", dest="ptc",
                    help="With --server-tool code_execution and --tool-file: mark those "
                         "custom tools as callable from code (Programmatic Tool Calling)")
    tu.add_argument("--stream-tools", metavar="PROMPT", dest="stream_tools",
                    help="Stream a turn with fine-grained tool input streaming, using "
                         "--tool-file for the tool definitions")

    adv = p.add_argument_group("Advisor Tool")
    adv.add_argument("--advisor", metavar="PROMPT", dest="advisor",
                     help="Run PROMPT with an advisor model consulted mid-generation "
                          "(advisor_20260301 beta)")
    adv.add_argument("--advisor-model", default="claude-opus-4-8", dest="advisor_model",
                     help="Advisor model (default: claude-opus-4-8)")
    adv.add_argument("--advisor-max-uses", type=int, default=0, dest="advisor_max_uses",
                     help="Cap on advisor tool definition's max_uses (unset = no cap)")
    adv.add_argument("--advisor-max-tokens", type=int, default=0, dest="advisor_max_tokens",
                     help="Cap the advisor model's output tokens per call")

    em = p.add_argument_group("Embeddings")
    em.add_argument("--embed", metavar="TEXT", dest="embed",
                    help="Embed TEXT via Voyage AI, print vector info (needs VOYAGE_API_KEY; "
                         "Anthropic doesn't host its own embedding model)")
    em.add_argument("--embed-file", metavar="FILE", dest="embed_file",
                    help="Embed each line of FILE via Voyage AI")
    em.add_argument("--embed-similarity", nargs=2, metavar=("A", "B"), dest="embed_similarity",
                    help="Cosine similarity between two strings' embeddings")
    em.add_argument("--embed-model", default="voyage-3.5", dest="embed_model")
    em.add_argument("--embed-input-type", default="document", choices=["document", "query"],
                    dest="embed_input_type")

    so = p.add_argument_group("Structured Outputs")
    so.add_argument("--structured", action="store_true")
    so.add_argument("--schema", metavar="FILE")
    so.add_argument("--schema-inline", metavar="JSON", dest="schema_inline")
    so.add_argument("--structured-analyse", metavar="FILE", dest="structured_analyse")
    so.add_argument("--structured-extract", metavar="FILE", dest="structured_extract")

    fa = p.add_argument_group("Files API")
    fa.add_argument("--file-upload", metavar="FILE", dest="file_upload")
    fa.add_argument("--file-list", action="store_true", dest="file_list")
    fa.add_argument("--file-delete", metavar="ID", dest="file_delete")
    fa.add_argument("--file-ask", metavar="ID", dest="file_ask")
    fa.add_argument("--file-download", metavar="ID", dest="file_download")
    fa.add_argument("--file-output", default="", dest="file_output")
    fa.add_argument("--file-media-type", default="application/pdf", dest="file_media_type")

    ce = p.add_argument_group("Code Execution")
    ce.add_argument("--code-exec", action="store_true", dest="code_exec")
    ce.add_argument("--code-debug", metavar="FILE", dest="code_debug")
    ce.add_argument("--code-exec-output", default="", dest="code_exec_output")

    tc = p.add_argument_group("Token Counting")
    tc.add_argument("--count-tokens", action="store_true", dest="count_tokens")
    tc.add_argument("--count-budget", type=int, default=0, dest="count_budget")

    ci = p.add_argument_group("Citations & RAG")
    ci.add_argument("--cite", nargs="+", metavar="FILE")
    ci.add_argument("--rag", metavar="DIR")
    ci.add_argument("--rag-pattern", default="*.md", dest="rag_pattern")

    mo = p.add_argument_group("Models API")
    mo.add_argument("--list-models", action="store_true", dest="list_models")
    mo.add_argument("--list-models-legacy", action="store_true", dest="list_models_legacy",
                    help="Include superseded (still-callable) models in --list-models' offline view")
    mo.add_argument("--model-info", metavar="ID", dest="model_info")
    mo.add_argument("--check-deprecated", metavar="PATH", dest="check_deprecated",
                    help="Scan a file or directory for retired model ID strings and print migration targets")
    mo.add_argument("--upgrade-all", metavar="PATH", dest="upgrade_all",
                    help="Rewrite EVERY known Claude model ID under PATH (retired, legacy, "
                         "or just a different current model) to --upgrade-target. Unlike "
                         "--check-deprecated this actually edits files. Dry-run by default.")
    mo.add_argument("--upgrade-target", choices=sorted(UPGRADE_TARGETS), default="fable5",
                    dest="upgrade_target",
                    help="Target for --upgrade-all: fable5 (claude-fable-5), opus "
                         "(claude-opus-4-8), sonnet5 (claude-sonnet-5), haiku45 (claude-haiku-4-5-20251001), "
                         "or mythos5 (claude-mythos-5). Default: fable5")
    mo.add_argument("--upgrade-yes", action="store_true", dest="upgrade_yes",
                    help="With --upgrade-all: actually write changes (default is a dry-run preview)")
    mo.add_argument("--upgrade-no-backup", action="store_true", dest="upgrade_no_backup",
                    help="With --upgrade-all --upgrade-yes: skip writing .bak backup files")

    f5 = p.add_argument_group("Claude Fable 5 / Mythos 5")
    f5.add_argument("--fable5-info", action="store_true", dest="fable5_info",
                    help="Show what's known about Fable 5 / Mythos 5 (pricing, context, refusal handling)")
    f5.add_argument("--fable5", metavar="PROMPT", dest="fable5",
                    help="Call Claude Fable 5 with refusal detection and automatic fallback")
    f5.add_argument("--fable5-no-fallback", action="store_true", dest="fable5_no_fallback",
                    help="With --fable5: disable automatic fallback on refusal (just report it)")
    f5.add_argument("--fallback-model", default="claude-opus-4-8", dest="fallback_model",
                    help="Model to fall back to on refusal (default: claude-opus-4-8)")

    m5 = p.add_argument_group("Claude Mythos 5 (limited access)")
    m5.add_argument("--mythos5-info", action="store_true", dest="mythos5_info",
                    help="Show what's known about Mythos 5 access/pricing (approval-gated, see --fable5-info for the public sibling)")
    m5.add_argument("--mythos5", metavar="PROMPT", dest="mythos5",
                    help="Call Claude Mythos 5 directly (requires approved Project Glasswing access)")

    cu = p.add_argument_group("Computer Use")
    cu.add_argument("--computer-use", metavar="TASK", dest="computer_use")

    ag = p.add_argument_group("Agent SDK")
    ag.add_argument("--agent-session", metavar="ID", dest="agent_session")
    ag.add_argument("--agent-orchestrate", action="store_true", dest="agent_orchestrate")
    ag.add_argument("--agent-managed-run", metavar="TASK", dest="agent_managed_run",
                    help="Run TASK on the real hosted Claude Managed Agents API "
                         "(creates a throwaway agent/environment/session)")
    ag.add_argument("--agent-list-sessions", action="store_true", dest="agent_list_sessions")
    ag.add_argument("--list-tool-presets", action="store_true", dest="list_tool_presets")

    cw = p.add_argument_group("Cowork")
    cw.add_argument("--cowork", metavar="TYPE")
    cw.add_argument("--cowork-prompt", metavar="TEXT", dest="cowork_prompt")
    cw.add_argument("--cowork-files", nargs="+", dest="cowork_files")
    cw.add_argument("--cowork-depth", type=int, default=3, dest="cowork_depth")
    cw.add_argument("--cowork-format", default="markdown", dest="cowork_format",
                    choices=["markdown","json","outline","bullets"])
    cw.add_argument("--cowork-list", action="store_true", dest="cowork_list")

    # Claude Code
    cc = p.add_argument_group("Claude Code")
    cc.add_argument("--code-agent", action="store_true", dest="code_agent")
    cc.add_argument("--code-agent-cwd", default=".", dest="code_agent_cwd")
    cc.add_argument("--code-agent-tools", default="all", dest="code_agent_tools")
    cc.add_argument("--code-agent-permission", default="askPermission",
                    dest="code_agent_permission")
    cc.add_argument("--code-agent-session", metavar="ID", dest="code_agent_session")
    cc.add_argument("--code-agent-resume", metavar="ID", dest="code_agent_resume")
    cc.add_argument("--code-agent-system", metavar="TEXT", dest="code_agent_system")
    cc.add_argument("--code-agent-mcp", nargs="+", metavar="URL", dest="code_agent_mcp")
    cc.add_argument("--code-agent-mcp-tunnel", type=int, metavar="PORT",
                    dest="code_agent_mcp_tunnel",
                    help="Open an MCP tunnel to a local MCP server on PORT and print "
                         "its public URL (research preview)")
    cc.add_argument("--code-agent-list-sessions", action="store_true",
                    dest="code_agent_list_sessions")
    cc.add_argument("--code-agent-list-tools", action="store_true",
                    dest="code_agent_list_tools")
    cc.add_argument("--code-agent-hooks", metavar="FILE", dest="code_agent_hooks")
    cc.add_argument("--code-agent-checkpoint", action="store_true",
                    dest="code_agent_checkpoint")
    cc.add_argument("--code-agent-subagent", metavar="PROMPT",
                    dest="code_agent_subagent")
    cc.add_argument("--code-agent-todo", metavar="PROMPT", dest="code_agent_todo")
    cc.add_argument("--code-agent-slash", metavar="CMD", dest="code_agent_slash")
    cc.add_argument("--code-agent-cost", action="store_true", dest="code_agent_cost")
    cc.add_argument("--code-agent-output", default="stream",
                    dest="code_agent_output",
                    choices=["stream","json","text"])
    cc.add_argument("--code-agent-headless", action="store_true",
                    dest="code_agent_headless",
                    help="Non-interactive print mode: run one prompt, print plain text, exit (like `claude -p`)")
    cc.add_argument("--code-agent-output-style", metavar="NAME",
                    dest="code_agent_output_style",
                    help="Apply a named output style (default, explanatory, concise, learning, or custom)")
    cc.add_argument("--list-output-styles", action="store_true",
                    dest="list_output_styles")
    cc.add_argument("--code-agent-sandbox", action="store_true",
                    dest="code_agent_sandbox",
                    help="Run Bash tool calls inside a filesystem+network sandbox")
    cc.add_argument("--code-agent-sandbox-allow-net", action="store_true",
                    dest="code_agent_sandbox_allow_net",
                    help="Allow network access inside the sandbox (default: blocked)")
    cc.add_argument("--code-agent-sandbox-roots", nargs="+", metavar="PATH",
                    dest="code_agent_sandbox_roots",
                    help="Extra filesystem roots the sandbox may read/write besides cwd")

    pl = p.add_argument_group("Plugins & Marketplaces")
    pl.add_argument("--plugin-marketplace-add", metavar="PATH_OR_URL",
                    dest="plugin_marketplace_add")
    pl.add_argument("--plugin-marketplace-name", metavar="NAME",
                    dest="plugin_marketplace_name")
    pl.add_argument("--plugin-marketplace-list", action="store_true",
                    dest="plugin_marketplace_list")
    pl.add_argument("--plugin-marketplace-remove", metavar="NAME",
                    dest="plugin_marketplace_remove")
    pl.add_argument("--plugin-install", metavar="NAME[@MARKETPLACE]",
                    dest="plugin_install")
    pl.add_argument("--plugin-dir", metavar="PATH", dest="plugin_dir",
                    help="Install a plugin directly from a local directory or .zip")
    pl.add_argument("--plugin-uninstall", metavar="NAME", dest="plugin_uninstall")
    pl.add_argument("--plugin-list", action="store_true", dest="plugin_list")
    pl.add_argument("--plugin-info", metavar="NAME", dest="plugin_info")
    pl.add_argument("--plugin-enable", metavar="NAME", dest="plugin_enable")
    pl.add_argument("--plugin-disable", metavar="NAME", dest="plugin_disable")
    pl.add_argument("--plugin-validate", metavar="PATH", dest="plugin_validate")

    mem = p.add_argument_group("Memory")
    mem.add_argument("--memory-add", metavar="TEXT", dest="memory_add")
    mem.add_argument("--memory-type", default="fact", choices=["fact","preference","event","task"], dest="memory_type")
    mem.add_argument("--memory-tags", default="", dest="memory_tags")
    mem.add_argument("--memory-importance", type=int, default=5, dest="memory_importance")
    mem.add_argument("--memory-recall", metavar="QUERY", dest="memory_recall")
    mem.add_argument("--memory-forget", metavar="ID", dest="memory_forget")
    mem.add_argument("--memory-stats", action="store_true", dest="memory_stats")
    mem.add_argument("--memory-retention", action="store_true", dest="memory_retention")
    mem.add_argument("--memory-ns", default="default", dest="memory_ns")

    ses = p.add_argument_group("Sessions & Checkpoints")
    ses.add_argument("--sessions-list", action="store_true", dest="sessions_list")
    ses.add_argument("--session-show", metavar="ID", dest="session_show")
    ses.add_argument("--checkpoint-list", metavar="SESSION_ID", dest="checkpoint_list")
    ses.add_argument("--away-summary", metavar="SESSION_ID", dest="away_summary")

    lv = p.add_argument_group("zai-live")
    lv.add_argument("--live", action="store_true", dest="live")

    rs = p.add_argument_group("Deep Research")
    rs.add_argument("--research", metavar="TOPIC", dest="research")
    rs.add_argument("--research-depth", type=int, default=4, dest="research_depth")
    rs.add_argument("--research-urls", nargs="*", default=None, dest="research_urls")

    rag = p.add_argument_group("RAG")
    rag.add_argument("--rag-index", metavar="NAME", dest="rag_index")
    rag.add_argument("--rag-folder", metavar="PATH", dest="rag_folder")
    rag.add_argument("--rag-query", metavar="TEXT", dest="rag_query")
    rag.add_argument("--rag-index-name", default="default", dest="rag_index_name")
    rag.add_argument("--rag-list", action="store_true", dest="rag_list")
    rag.add_argument("--rag-k", type=int, default=5, dest="rag_k")

    ev = p.add_argument_group("Evaluation")
    ev.add_argument("--eval-run", metavar="SUITE_JSON", dest="eval_run")
    ev.add_argument("--eval-compare", nargs=2, metavar=("MODEL_A","MODEL_B"), dest="eval_compare")
    ev.add_argument("--eval-list", action="store_true", dest="eval_list")
    ev.add_argument("--eval-scaffold", metavar="PATH", dest="eval_scaffold")
    ev.add_argument("--eval-threshold", type=float, default=0.7, dest="eval_threshold")

    gt = p.add_argument_group("Git Integration")
    gt.add_argument("--git-commit", action="store_true", dest="git_commit")
    gt.add_argument("--git-commit-style", default="conventional",
                    choices=["conventional","imperative","detailed"], dest="git_commit_style")
    gt.add_argument("--git-commit-write", action="store_true", dest="git_commit_write")
    gt.add_argument("--git-pr", nargs=2, metavar=("BASE","HEAD"), dest="git_pr")
    gt.add_argument("--git-changelog", metavar="SINCE_TAG", dest="git_changelog")
    gt.add_argument("--git-review", action="store_true", dest="git_review")
    gt.add_argument("--git-blame-explain", nargs=3, metavar=("FILE","START","END"), dest="git_blame_explain")

    co = p.add_argument_group("Cost Optimizer")
    co.add_argument("--optimized", metavar="PROMPT", dest="optimized")
    co.add_argument("--force-model", default=None, dest="force_model")
    co.add_argument("--cost-summary", action="store_true", dest="cost_summary")
    co.add_argument("--cost-reset", action="store_true", dest="cost_reset")

    ob = p.add_argument_group("Observability")
    ob.add_argument("--obs-latency", action="store_true", dest="obs_latency")
    ob.add_argument("--obs-errors", action="store_true", dest="obs_errors")
    ob.add_argument("--obs-tail", type=int, nargs="?", const=20, default=None, dest="obs_tail")
    ob.add_argument("--obs-clear", action="store_true", dest="obs_clear")
    ob.add_argument("--obs-hours", type=int, default=24, dest="obs_hours")

    wf = p.add_argument_group("Workflows")
    wf.add_argument("--workflow-run", metavar="PATH", dest="workflow_run")
    wf.add_argument("--workflow-input", default="", dest="workflow_input")
    wf.add_argument("--workflow-scaffold", metavar="PATH", dest="workflow_scaffold")

    hk = p.add_argument_group("Hooks")
    hk.add_argument("--hooks-add", nargs=2, metavar=("EVENT","COMMAND"), dest="hooks_add")
    hk.add_argument("--hook-tool-match", default=None, dest="hook_tool_match")
    hk.add_argument("--hooks-list", action="store_true", dest="hooks_list")
    hk.add_argument("--hooks-remove", type=int, metavar="INDEX", dest="hooks_remove")

    pm = p.add_argument_group("Permissions")
    pm.add_argument("--perms-list", action="store_true", dest="perms_list")
    pm.add_argument("--perms-add", nargs=2, metavar=("PATTERN","DECISION"), dest="perms_add")
    pm.add_argument("--perms-reason", default="", dest="perms_reason")

    pln = p.add_argument_group("Plan Mode")
    pln.add_argument("--plan", metavar="TASK", dest="plan")
    pln.add_argument("--plan-context", default="", dest="plan_context")
    pln.add_argument("--plan-execute", action="store_true", dest="plan_execute")

    se = p.add_argument_group("Settings")
    se.add_argument("--settings-show", action="store_true", dest="settings_show")
    se.add_argument("--status-line", action="store_true", dest="status_line")

    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    if args.version:
        print(BANNER); return

    # ── No-key listing ──
    if args.list_skills:
        from core.skills import SkillManager
        for s in SkillManager().list_skills():
            print(f"  {s['name']:<25} — {s['description']}")
        return
    if args.list_agents:
        # Was a second, independent hardcoded list of the same seven names
        # with no data behind them; now sourced from AGENT_SYSTEM_PROMPTS,
        # the same table --agent actually uses, so the two can't drift.
        for n, sys_prompt in sorted(AGENT_SYSTEM_PROMPTS.items()):
            print(f"  {n:<25} — {sys_prompt}")
        return
    if args.list_personalities:
        from core.personalities import PersonalityManager
        for p_ in PersonalityManager().list_personalities():
            print(f"  {p_['name']:<12} — {p_['description']}")
        return

    # ── Plugins & Marketplaces (no API key required) ──
    if args.plugin_marketplace_add:
        from core.claude_plugins import cmd_plugin_marketplace_add
        cmd_plugin_marketplace_add(args.plugin_marketplace_add, args.plugin_marketplace_name); return
    if args.plugin_marketplace_list:
        from core.claude_plugins import cmd_plugin_marketplace_list
        cmd_plugin_marketplace_list(); return
    if args.plugin_marketplace_remove:
        from core.claude_plugins import cmd_plugin_marketplace_remove
        cmd_plugin_marketplace_remove(args.plugin_marketplace_remove); return
    if args.plugin_install:
        from core.claude_plugins import cmd_plugin_install
        cmd_plugin_install(args.plugin_install); return
    if args.plugin_dir:
        from core.claude_plugins import cmd_plugin_install_dir
        cmd_plugin_install_dir(args.plugin_dir); return
    if args.plugin_uninstall:
        from core.claude_plugins import cmd_plugin_uninstall
        cmd_plugin_uninstall(args.plugin_uninstall); return
    if args.plugin_list:
        from core.claude_plugins import cmd_plugin_list
        cmd_plugin_list(); return
    if args.plugin_info:
        from core.claude_plugins import cmd_plugin_info
        cmd_plugin_info(args.plugin_info); return
    if args.plugin_enable:
        from core.claude_plugins import cmd_plugin_enable
        cmd_plugin_enable(args.plugin_enable); return
    if args.plugin_disable:
        from core.claude_plugins import cmd_plugin_disable
        cmd_plugin_disable(args.plugin_disable); return
    if args.plugin_validate:
        from core.claude_plugins import cmd_plugin_validate
        cmd_plugin_validate(args.plugin_validate); return

    # ── Settings (no API key required) ──
    if args.settings_show:
        from core.claude_settings import cmd_settings_show
        cmd_settings_show(); return
    if args.status_line:
        from core.claude_settings import cmd_status_line
        cmd_status_line(model=args.model or "claude-sonnet-5", cwd=args.code_agent_cwd); return
    if args.list_output_styles:
        from core.claude_output_styles import cmd_list_output_styles
        cmd_list_output_styles(); return

    if args.fable5_info:
        from agents.claude_fable5 import cmd_fable5_info
        cmd_fable5_info(); return

    if args.mythos5_info:
        from agents.claude_mythos5 import cmd_mythos5_info
        cmd_mythos5_info(); return

    if args.check_deprecated:
        from api.claude_models import cmd_check_deprecated
        cmd_check_deprecated(args.check_deprecated); return
    if args.upgrade_all:
        from api.claude_models import cmd_upgrade_all
        cmd_upgrade_all(args.upgrade_all, target=args.upgrade_target,
                        apply=args.upgrade_yes, no_backup=args.upgrade_no_backup); return

    if args.project_list:
        from core.projects import cmd_project_list; cmd_project_list(); return
    if args.project_templates:
        from core.projects import cmd_project_templates; cmd_project_templates(); return
    if args.project_show:
        from core.projects import cmd_project_show; cmd_project_show(args.project_show); return
    if args.project_delete:
        from core.projects import ProjectManager; ProjectManager().delete_project(args.project_delete)
        print("✓ Deleted."); return
    if args.project_archive:
        from core.projects import ProjectManager; ProjectManager().archive_project(args.project_archive)
        print("✓ Archived."); return
    if args.project_create:
        from core.projects import cmd_project_create
        cmd_project_create(args.project_create, args.project_desc, args.project_template); return
    if args.project_add_task:
        from core.projects import cmd_project_add_task
        cmd_project_add_task(args.project_add_task, args.task_title or args.prompt or "",
                             args.task_desc, args.task_agent, args.task_priority); return
    if args.artifact_types:
        from artifacts import cmd_artifact_types; cmd_artifact_types(); return
    if args.artifact_list:
        from artifacts import cmd_artifact_list
        cmd_artifact_list(query=args.artifact_query,
            artifact_type=args.artifact_type if args.artifact_type!="code" else "",
            project_id=args.artifact_project, tag=args.tag); return
    if args.artifact_show:
        from artifacts import cmd_artifact_show
        cmd_artifact_show(args.artifact_show, args.artifact_version); return
    if args.artifact_export:
        from artifacts import cmd_artifact_export
        cmd_artifact_export(args.artifact_export, args.output or "", args.artifact_version); return
    if args.artifact_export_all:
        from artifacts import cmd_artifact_export_all
        cmd_artifact_export_all(args.artifact_export_all, args.artifact_output_dir); return
    if args.artifact_diff:
        from artifacts import cmd_artifact_diff
        cmd_artifact_diff(args.artifact_diff, args.v1, args.v2); return
    if args.artifact_delete:
        from artifacts import cmd_artifact_delete; cmd_artifact_delete(args.artifact_delete); return
    if args.artifact_tag:
        from artifacts import cmd_artifact_tag; cmd_artifact_tag(args.artifact_tag, args.tag); return
    if args.artifact_attach:
        from artifacts import cmd_artifact_attach
        cmd_artifact_attach(args.artifact_attach, args.to_project); return
    if args.list_server_tools:
        from core.claude_tools import cmd_list_server_tools; cmd_list_server_tools(); return
    if args.cowork_list:
        from agents.cowork import cmd_cowork_list; cmd_cowork_list(); return
    if args.agent_list_sessions:
        from agents.claude_agents_sdk import cmd_agent_list_sessions; cmd_agent_list_sessions(); return
    if args.list_tool_presets:
        from agents.claude_agents_sdk import cmd_list_tool_presets; cmd_list_tool_presets(); return
    if args.code_agent_list_sessions:
        from core.claude_code import cmd_code_list_sessions; cmd_code_list_sessions(); return
    if args.code_agent_list_tools:
        from core.claude_code import cmd_code_list_tools; cmd_code_list_tools(); return

    # ── New in v1.10.0 — no API key required ──
    if args.memory_add:
        from core.claude_memory import cmd_memory_add
        cmd_memory_add(args.memory_add, args.memory_type, args.memory_tags,
                       args.memory_importance, args.memory_ns); return
    if args.memory_recall:
        from core.claude_memory import cmd_memory_recall
        cmd_memory_recall(args.memory_recall, args.memory_ns); return
    if args.memory_forget:
        from core.claude_memory import cmd_memory_forget
        cmd_memory_forget(args.memory_forget, args.memory_ns); return
    if args.memory_stats:
        from core.claude_memory import cmd_memory_stats; cmd_memory_stats(args.memory_ns); return
    if args.memory_retention:
        from core.claude_memory import cmd_memory_retention; cmd_memory_retention(args.memory_ns); return
    if args.sessions_list:
        from agents.claude_sessions import cmd_sessions_list; cmd_sessions_list(); return
    if args.session_show:
        from agents.claude_sessions import cmd_session_show; cmd_session_show(args.session_show); return
    if args.checkpoint_list:
        from agents.claude_sessions import cmd_checkpoint_list; cmd_checkpoint_list(args.checkpoint_list); return
    if args.away_summary:
        from agents.claude_sessions import cmd_away_summary; cmd_away_summary(args.away_summary); return
    if args.rag_index and args.rag_folder:
        from agents.claude_rag import cmd_rag_index; cmd_rag_index(args.rag_index, args.rag_folder); return
    if args.rag_list:
        from agents.claude_rag import cmd_rag_list; cmd_rag_list(); return
    if args.eval_list:
        from agents.claude_eval import cmd_eval_list; cmd_eval_list(); return
    if args.eval_scaffold:
        from agents.claude_eval import cmd_eval_scaffold; cmd_eval_scaffold(args.eval_scaffold); return
    if args.cost_summary:
        from utils.claude_cost_optimizer import cmd_cost_summary; cmd_cost_summary(); return
    if args.cost_reset:
        from utils.claude_cost_optimizer import cmd_cost_reset; cmd_cost_reset(); return
    if args.obs_latency:
        from utils.claude_observability import cmd_obs_latency; cmd_obs_latency(args.obs_hours); return
    if args.obs_tail is not None:
        from utils.claude_observability import cmd_obs_tail; cmd_obs_tail(args.obs_tail); return
    if args.obs_clear:
        from utils.claude_observability import cmd_obs_clear; cmd_obs_clear(); return
    if args.workflow_scaffold:
        from agents.claude_workflow import cmd_workflow_scaffold; cmd_workflow_scaffold(args.workflow_scaffold); return
    if args.hooks_add:
        from core.claude_hooks_perms_plan import cmd_hooks_add
        cmd_hooks_add(args.hooks_add[0], args.hooks_add[1], args.hook_tool_match); return
    if args.hooks_list:
        from core.claude_hooks_perms_plan import cmd_hooks_list; cmd_hooks_list(); return
    if args.hooks_remove is not None:
        from core.claude_hooks_perms_plan import cmd_hooks_remove; cmd_hooks_remove(args.hooks_remove); return
    if args.perms_list:
        from core.claude_hooks_perms_plan import cmd_perms_list; cmd_perms_list(); return
    if args.perms_add:
        from core.claude_hooks_perms_plan import cmd_perms_add
        cmd_perms_add(args.perms_add[0], args.perms_add[1], args.perms_reason); return

    # ── API key required ──
    key   = _api_key(args)
    model = _model(args)

    if args.list_models:
        from api.claude_models import cmd_list_models
        cmd_list_models(key, include_legacy=getattr(args, "list_models_legacy", False)); return
    if args.model_info:
        from api.claude_models import cmd_model_info; cmd_model_info(args.model_info, key); return
    if args.fable5:
        from agents.claude_fable5 import cmd_fable5_call
        cmd_fable5_call(args.fable5, key, fallback_model=args.fallback_model,
                        allow_fallback=not args.fable5_no_fallback); return
    if args.mythos5:
        from agents.claude_mythos5 import cmd_mythos5_call
        cmd_mythos5_call(args.mythos5, key); return

    # ── zai-live ──
    if args.live:
        from agents.claude_live import cmd_live
        # --temperature was accepted by the parser but never reached cmd_live,
        # so live mode always used LiveSession's 0.7 default regardless of the
        # flag. Now threaded through (still safely dropped by sampling_kwargs()
        # for claude-sonnet-5 and later, which reject it).
        cmd_live(key, model=model, temperature=args.temperature); return

    # ── Deep Research ──
    if args.research:
        from agents.claude_research import cmd_research
        cmd_research(args.research, key, model, depth=args.research_depth,
                     source_urls=args.research_urls, output=args.output); return

    # ── RAG (query needs the key for generation; index/list handled above) ──
    if args.rag_query:
        from agents.claude_rag import cmd_rag_query
        cmd_rag_query(args.rag_index_name, args.rag_query, key, model, k=args.rag_k); return

    # ── Evaluation (run/compare call the model; list/scaffold handled above) ──
    if args.eval_run:
        from agents.claude_eval import cmd_eval_run
        cmd_eval_run(args.eval_run, key, model, threshold=args.eval_threshold, output=args.output); return
    if args.eval_compare:
        from agents.claude_eval import cmd_eval_compare
        cmd_eval_compare(args.eval_run or args.eval_scaffold or "", args.eval_compare[0],
                         args.eval_compare[1], key); return

    # ── Git Integration ──
    if args.git_commit:
        from agents.claude_git import cmd_git_commit
        cmd_git_commit(key, model, style=args.git_commit_style, write=args.git_commit_write); return
    if args.git_pr:
        from agents.claude_git import cmd_git_pr; cmd_git_pr(args.git_pr[0], args.git_pr[1], key, model); return
    if args.git_changelog:
        from agents.claude_git import cmd_git_changelog
        cmd_git_changelog(args.git_changelog, key, model, output=args.output); return
    if args.git_review:
        from agents.claude_git import cmd_git_review; cmd_git_review(key, model); return
    if args.git_blame_explain:
        from agents.claude_git import cmd_git_blame_explain
        f, s, e = args.git_blame_explain
        cmd_git_blame_explain(f, int(s), int(e), key, model); return

    # ── Cost Optimizer (optimized calls the model; summary/reset handled above) ──
    if args.optimized:
        from utils.claude_cost_optimizer import cmd_optimized
        cmd_optimized(args.optimized, key, verbose=True, force_model=args.force_model); return

    # ── Observability (errors needs the model for analysis; rest handled above) ──
    if args.obs_errors:
        from utils.claude_observability import cmd_obs_errors; cmd_obs_errors(key, model, args.obs_hours); return

    # ── Workflows (run calls the model; scaffold handled above) ──
    if args.workflow_run:
        from agents.claude_workflow import cmd_workflow_run
        cmd_workflow_run(args.workflow_run, key, input_text=args.workflow_input, output=args.output); return

    # ── Plan Mode ──
    if args.plan:
        from core.claude_hooks_perms_plan import cmd_plan
        cmd_plan(args.plan, key, model, context=args.plan_context,
                execute=args.plan_execute, output=args.output); return

    if args.thinking or args.adaptive:
        from core.claude_thinking import cmd_thinking
        prompt = args.prompt or (args.file and _read_file(args.file)) or ""
        cmd_thinking(prompt=prompt, api_key=key, model=model,
                     budget=args.thinking_budget, effort=args.effort or None,
                     adaptive=args.adaptive, show_thinking=args.show_thinking,
                     stream=args.stream); return
    if args.stream:
        from api.claude_stream import cmd_stream
        cmd_stream(args.prompt or "", key, model,
                   file_content=_read_file(args.file) if args.file else None,
                   show_thinking=args.show_thinking); return
    if args.web_search or args.web_fetch:
        from api.claude_search import cmd_web_search
        cmd_web_search(args.prompt or "", key, model,
                       max_searches=args.max_searches,
                       show_citations=not args.no_citations,
                       web_fetch=args.web_fetch); return
    if args.fetch_url:
        from api.claude_search import cmd_fetch_url
        cmd_fetch_url(args.fetch_url, args.prompt or "", key, model); return
    if args.vision:
        from api.claude_vision import cmd_vision
        cmd_vision(args.vision, args.prompt or "", key, model,
                   is_code=args.vision_code, language=args.vision_lang); return
    if args.vision_pdf:
        from api.claude_vision import cmd_vision_pdf
        cmd_vision_pdf(args.vision_pdf, args.prompt or "", key, model); return
    if args.vision_url:
        from api.claude_vision import cmd_vision_url
        cmd_vision_url(args.vision_url, args.prompt or "", key, model); return
    if args.vision_compare:
        from api.claude_vision import cmd_vision_compare
        cmd_vision_compare(args.vision_compare, args.prompt or "", key, model); return
    if args.vision_ocr:
        from api.claude_vision import cmd_vision_ocr
        cmd_vision_ocr(args.vision_ocr, key, model); return
    if args.batch_submit:
        from api.claude_batch import cmd_batch_submit
        cmd_batch_submit(args.batch_submit, key, model,
                         use_300k_output=args.batch_300k_output); return
    if args.batch_status:
        from api.claude_batch import cmd_batch_status
        cmd_batch_status(args.batch_status, key); return
    if args.batch_results:
        from api.claude_batch import cmd_batch_results
        cmd_batch_results(args.batch_results, key, save_to=args.output or None); return
    if args.batch_cancel:
        from api.claude_batch import cmd_batch_cancel
        cmd_batch_cancel(args.batch_cancel, key); return
    if args.batch_list:
        from api.claude_batch import cmd_batch_list; cmd_batch_list(key); return
    if args.batch_generate > 0:
        from api.claude_batch import cmd_batch_generate
        cmd_batch_generate(args.prompt or "", args.batch_generate, key, model,
                           wait=args.batch_wait); return
    if args.cache_warm:
        from api.claude_cache import cmd_cache_warm
        cmd_cache_warm(key, model, system=args.cache_system or None,
                       doc_files=args.cache_docs or [], ttl=args.cache_ttl); return
    if args.cache:
        from api.claude_cache import cmd_cache_generate
        docs = [open(f).read() for f in (args.cache_docs or [])]
        cmd_cache_generate(args.prompt or "", key, model,
                           system=args.cache_system or None, docs=docs,
                           ttl=args.cache_ttl, show_stats=args.cache_stats); return
    if args.tool_agent:
        from core.claude_tools import cmd_tool_agent
        cmd_tool_agent(args.prompt or "", key, model,
                       max_turns=args.max_turns); return
    if args.server_tool:
        from core.claude_tools import cmd_server_tool
        extra_tool_defs = None
        if args.file:
            import json as _json
            extra_tool_defs = _json.loads(_read_file(args.file))
            if isinstance(extra_tool_defs, dict):
                extra_tool_defs = [extra_tool_defs]
        cmd_server_tool(args.prompt or "",
                        [t.strip() for t in args.server_tool.split(",")], key, model,
                        use_context_management=args.context_management,
                        use_compaction=args.compaction,
                        task_budget_tokens=args.task_budget or None,
                        use_ptc=args.ptc,
                        extra_tool_defs=extra_tool_defs); return
    if args.memory_agent:
        from core.claude_tools import cmd_memory_agent
        cmd_memory_agent(args.memory_agent, key, model,
                         memory_dir=args.memory_dir, max_turns=args.max_turns); return
    if args.advisor:
        from agents.claude_advisor import cmd_advisor
        cmd_advisor(args.advisor, key, model,
                   advisor_model=args.advisor_model,
                   max_uses=args.advisor_max_uses or None,
                   advisor_max_tokens=args.advisor_max_tokens or None); return
    if args.embed:
        from utils.claude_embeddings import cmd_embed
        cmd_embed(args.embed, model=args.embed_model, input_type=args.embed_input_type); return
    if args.embed_file:
        from utils.claude_embeddings import cmd_embed_file
        cmd_embed_file(args.embed_file, model=args.embed_model,
                       input_type=args.embed_input_type); return
    if args.embed_similarity:
        from utils.claude_embeddings import cmd_embed_similarity
        cmd_embed_similarity(args.embed_similarity[0], args.embed_similarity[1],
                             model=args.embed_model); return
    if args.stream_tools:
        from api.claude_stream import cmd_stream_tools
        import json as _json
        tool_defs = _json.loads(_read_file(args.file)) if args.file else []
        if isinstance(tool_defs, dict):
            tool_defs = [tool_defs]
        cmd_stream_tools(args.stream_tools, tool_defs, key, model); return
    if args.structured:
        from api.claude_structured import cmd_structured
        cmd_structured(args.prompt or "", key, model,
                       schema_path=args.schema, schema_inline=args.schema_inline); return
    if args.structured_analyse:
        from api.claude_structured import cmd_structured_analyse
        cmd_structured_analyse(args.structured_analyse, key, model); return
    if args.structured_extract:
        from api.claude_structured import cmd_structured_extract
        cmd_structured_extract(args.structured_extract, args.schema, key, model); return
    if args.file_upload:
        from api.claude_files import cmd_file_upload
        cmd_file_upload(args.file_upload, key, model); return
    if args.file_list:
        from api.claude_files import cmd_file_list; cmd_file_list(key, model); return
    if args.file_delete:
        from api.claude_files import cmd_file_delete; cmd_file_delete(args.file_delete, key); return
    if args.file_ask:
        from api.claude_files import cmd_file_ask
        cmd_file_ask(args.file_ask, args.prompt or "Summarise.", key, model,
                     media_type=args.file_media_type); return
    if args.file_download:
        from api.claude_files import cmd_file_download
        cmd_file_download(args.file_download,
                          args.file_output or args.output or f"{args.file_download}.bin", key); return
    if args.code_exec:
        from core.claude_code_exec import cmd_code_exec
        cmd_code_exec(args.prompt or "", key, model,
                      output_dir=args.code_exec_output or None); return
    if args.code_debug:
        from core.claude_code_exec import cmd_code_debug
        cmd_code_debug(args.code_debug, key, model); return
    if args.count_tokens:
        from utils.claude_tokens import cmd_count_tokens
        cmd_count_tokens(args.prompt or "", key, model,
                         file_path=args.file, budget=args.count_budget or None); return
    if args.cite:
        from api.claude_citations import cmd_cite
        cmd_cite(args.prompt or "", args.cite, key, model); return
    if args.rag:
        from api.claude_citations import cmd_rag
        cmd_rag(args.prompt or "", args.rag, key, model, pattern=args.rag_pattern); return
    if args.computer_use:
        from api.claude_models import cmd_computer_use
        cmd_computer_use(args.computer_use, key, model); return
    if args.interleaved_thinking:
        from api.claude_models import cmd_adaptive_thinking
        cmd_adaptive_thinking(args.prompt or "", key, model, effort=args.effort or "medium"); return
    if args.agent_session or args.agent_orchestrate:
        from agents.claude_agents_sdk import cmd_agent_chat, cmd_agent_orchestrate
        if args.agent_orchestrate:
            cmd_agent_orchestrate(args.prompt or "", key, model,
                                  session_id=args.agent_session)
        else:
            cmd_agent_chat(args.prompt or "", key, model,
                           session_id=args.agent_session)
        return
    if args.agent_managed_run:
        # Real hosted Claude Managed Agents API (/v1/agents, /v1/environments,
        # /v1/sessions) — distinct from --agent-session above, which runs a
        # local agent loop over the plain Messages API. See
        # claude_agents_sdk.ManagedAgentsClient.
        from agents.claude_agents_sdk import cmd_managed_agent_run
        cmd_managed_agent_run(args.agent_managed_run, key, model=model); return
    if args.cowork:
        from agents.cowork import cmd_cowork
        prompt = args.cowork_prompt or args.prompt or ""
        if not prompt:
            print("[ERROR] --cowork requires -p or --cowork-prompt"); sys.exit(1)
        cmd_cowork(args.cowork, prompt, key, model,
                   files=args.cowork_files, depth=args.cowork_depth,
                   output_fmt=args.cowork_format, output_file=args.output); return

    # Claude Code commands
    if args.code_agent_mcp_tunnel:
        from agents.claude_agents_sdk import cmd_mcp_tunnel_open
        cmd_mcp_tunnel_open(key, args.code_agent_mcp_tunnel); return
    if args.code_agent or args.code_agent_session or args.code_agent_resume:
        from core.claude_code import cmd_code_agent
        prompt = args.prompt or ""
        if not prompt:
            print("[ERROR] --code-agent requires -p PROMPT"); sys.exit(1)
        cmd_code_agent(
            prompt=prompt, api_key=key, model=model,
            cwd=args.code_agent_cwd,
            tools=args.code_agent_tools,
            permission=args.code_agent_permission,
            session_id=args.code_agent_session or args.code_agent_resume,
            system=args.code_agent_system,
            mcp_urls=args.code_agent_mcp or [],
            output_mode=args.code_agent_output,
            hooks_file=args.code_agent_hooks,
            checkpoint=args.code_agent_checkpoint,
            output_file=args.output,
            output_style=args.code_agent_output_style,
            sandbox=args.code_agent_sandbox,
            sandbox_allow_net=args.code_agent_sandbox_allow_net,
            sandbox_roots=args.code_agent_sandbox_roots or [],
            headless=args.code_agent_headless,
        ); return
    if args.code_agent_subagent:
        from core.claude_code import cmd_code_subagent
        cmd_code_subagent(args.code_agent_subagent, key, model,
                          cwd=args.code_agent_cwd); return
    if args.code_agent_todo:
        from core.claude_code import cmd_code_todo
        cmd_code_todo(args.code_agent_todo, key, model); return
    if args.code_agent_slash:
        from core.claude_code import cmd_code_slash
        cmd_code_slash(args.code_agent_slash, key, model,
                       cwd=args.code_agent_cwd, prompt=args.prompt or ""); return
    if args.code_agent_cost:
        from core.claude_code import cmd_code_cost
        cmd_code_cost(key); return

    if args.project_plan:
        from core.projects import cmd_project_plan
        from core.coder import Coder
        cmd_project_plan(args.project_plan, Coder(api_key=key, model=model)); return
    if args.project_run:
        from core.projects import cmd_project_run
        from core.coder import Coder
        cmd_project_run(args.project_run, args.task or "all",
                        Coder(api_key=key, model=model)); return
    if args.artifact_create:
        from artifacts import cmd_artifact_create
        from core.coder import Coder
        if not args.prompt:
            print("[ERROR] --artifact-create requires -p"); sys.exit(1)
        tags = [t.strip() for t in args.artifact_tags.split(",") if t.strip()]
        cmd_artifact_create(args.artifact_create, args.prompt,
                            artifact_type=args.artifact_type,
                            language=args.artifact_lang, tags=tags,
                            project_id=args.artifact_project,
                            coder=Coder(api_key=key, model=model)); return
    if args.artifact_iterate:
        from artifacts import cmd_artifact_iterate
        from core.coder import Coder
        cmd_artifact_iterate(args.artifact_iterate, args.prompt or "",
                             Coder(api_key=key, model=model)); return

    if args.prompt or args.file:
        from core.coder import Coder
        c = Coder(api_key=key, model=model,
                  temperature=args.temperature, max_tokens=args.max_tokens,
                  service_tier=args.service_tier, inference_geo=args.inference_geo,
                  fast_mode=args.fast_mode,
                  # Previously never sourced from a CLI flag at all — see
                  # the Skills & Agents arg group comment above.
                  personality_style=args.personality)
        # --skill and --agent now actually affect the request: each
        # contributes a system-prompt fragment instead of being accepted
        # and discarded.
        system_parts = []
        if args.skill:
            from core.skills import SkillManager
            skill = SkillManager().get_skill(args.skill)
            if skill:
                system_parts.append(f"Skill focus — {skill['name']}: {skill['description']}")
            else:
                print(f"\033[93m⚠ Unknown --skill '{args.skill}' (see --list-skills); ignoring.\033[0m",
                     file=sys.stderr)
        if args.agent:
            system_parts.append(AGENT_SYSTEM_PROMPTS[args.agent])
        system = "\n\n".join(system_parts) or None

        result = c.generate(args.prompt or "", system=system,
                            file_content=_read_file(args.file) if args.file else None)
        print(result)
        if args.output:
            open(args.output, "w").write(result)
        return

    parser.print_help()

if __name__ == "__main__":
    main()