"""
claude_advisor.py — Advisor tool (advisor_20260301, beta)
AI Model Coder CLI v1.11.1

Pairs a fast "executor" model (Sonnet 4.6 or Haiku 4.5) with a stronger
"advisor" model (Opus) the executor can consult mid-generation at decision
points (before committing to an approach, when stuck on a recurring error,
before declaring a task complete). The advisor sees the full transcript and
returns guidance the executor applies before continuing; it never calls
tools and never produces the user-facing final answer itself.

CONFIDENCE NOTE — this entry was re-verified via live web search on
2026-07-03 (not just inherited from the prior pass), against Anthropic's
own docs page (platform.claude.com/docs/en/agents-and-tools/tool-use/
advisor-tool), Anthropic's launch blog post (claude.com/blog/
the-advisor-strategy, dated 2026-04-09), and independent confirmation via
LiteLLM's integration docs and a third-party GitHub example. The mechanics
below (tool shape, beta header, pause_turn resume loop, Bedrock/Vertex/
Foundry unavailability) are consistently confirmed across all sources.

One real discrepancy found between sources, flagged rather than silently
resolved: Anthropic's own docs page shows the advisor model as
"claude-opus-4-8" in its code examples, while the original April 2026
launch blog post and third-party docs (LiteLLM) describe the beta as
locked to "claude-opus-4-6" only. Most likely explanation: it launched
pinned to Opus 4.6 and was later opened up to newer Opus versions as
Anthropic shipped them, with the docs page reflecting current state and
the blog posts frozen at their April 9 publish date. This module follows
the docs page (claude-opus-4-8) as the more likely current value, but
if you get a "model not supported for advisor" error, try claude-opus-4-6.

Corrected from the previous pass: the executor-model list below previously
included Opus and Fable 5 variants as valid executors. No source — not
Anthropic's docs, not the launch blog, not the third-party integrations —
describes anything other than Sonnet 4.6 and Haiku 4.5 as executors, which
makes sense: the entire point of the pattern is a cheap model driving the
loop and an expensive one consulted sparingly, so "Opus executor consulting
an Opus advisor" doesn't fit the pattern's own premise. Narrowed to match
what's actually documented.

Mechanics, as documented:
  • Add a tool of type "advisor_20260301" to your tools array, with its own
    "model" (the advisor model), optional "max_uses", optional "caching".
  • The executor emits a server_tool_use block named "advisor" when it wants
    guidance; the API runs the advisor pass server-side and returns the
    result as an advisor_tool_result block in the SAME response — no extra
    round trip needed on your part, UNLESS the response ends with
    stop_reason:"pause_turn" while an advisor call is still pending. In that
    case, resume by resending the assistant message unchanged (including the
    pending server_tool_use block) with the advisor tool still present.
  • If you omit the advisor tool from a follow-up request while the message
    history still contains advisor_tool_result blocks, the API 400s. Once
    you're done with the advisor for a conversation, strip those blocks too.
  • Supported executor models (beta, confirmed): Sonnet 4.6, Haiku 4.5.
  • Not available on Amazon Bedrock, Google Cloud (Vertex AI), or Microsoft
    Foundry — beta on the Claude API / Claude Platform on AWS only.
  • Advisor output tokens are billed at the advisor model's own rate — this
    is usually the dominant cost line, not the executor's tokens. Anthropic's
    own benchmarks (their numbers, not independently verified): Sonnet+Opus
    scored 74.8% on SWE-bench Multilingual vs. 72.1% for Sonnet alone while
    costing ~12% less than running Opus solo; Haiku+Opus more than doubled
    BrowseComp score (19.7% → 41.2%) at ~85% lower cost than Sonnet alone.

CLI flags:
  --advisor PROMPT           Run PROMPT with an advisor attached
  --advisor-model MODEL      Advisor model (default: claude-opus-4-8;
                               try claude-opus-4-6 if you get a
                               model-not-supported error — see note above)
  --advisor-max-uses N       Cap advisor calls this conversation (client-side
                              tracking — the tool itself has no built-in cap)
  --advisor-max-tokens N     Cap the advisor's output per call (max_tokens on
                              the advisor tool definition)
"""

import json
import urllib.request
import urllib.error
from typing import Optional


ADVISOR_TOOL_TYPE = "advisor_20260301"
ADVISOR_TOOL_BETA = "advisor-tool-2026-03-01"
ENDPOINT = "https://api.anthropic.com/v1/messages"

# Executor models the advisor tool is confirmed to support, per Anthropic's
# docs, launch blog, and independent third-party integrations (all checked
# 2026-07-03). Only Sonnet 4.6 and Haiku 4.5 are documented as executors —
# see the module docstring for why Opus/Fable-5-as-executor was removed.
ADVISOR_EXECUTOR_MODELS = {
    "claude-sonnet-4-6", "claude-sonnet-5",
    "claude-haiku-4-5", "claude-haiku-4-5-20251001",
}

# Advisor model candidates seen across sources — see the docstring's
# discrepancy note. Used only for the informational warning below, not
# to block a call; the live API is the real authority on what's valid.
ADVISOR_MODEL_CANDIDATES = {"claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6"}


def build_advisor_tool(advisor_model: str = "claude-opus-4-8",
                        max_uses: Optional[int] = None,
                        max_tokens: Optional[int] = None,
                        cache_ttl: Optional[str] = "5m") -> dict:
    """Build the advisor tool definition. cache_ttl caches the advisor's own
    read of the conversation (ephemeral, 5m default) so repeated advisor
    calls in one session don't re-process the full transcript from scratch
    every time — set to None to disable."""
    tool = {
        "type":  ADVISOR_TOOL_TYPE,
        "name":  "advisor",
        "model": advisor_model,
    }
    if max_uses is not None:
        tool["max_uses"] = max_uses
    if max_tokens is not None:
        tool["max_tokens"] = max_tokens
    if cache_ttl:
        tool["caching"] = {"type": "ephemeral", "ttl": cache_ttl}
    return tool


class AdvisorCoder:
    """Claude client wired to run an executor model with an advisor tool
    attached, including the pause_turn resume loop the advisor tool uses
    when it needs to hand a pending call back to you before continuing."""

    def __init__(self, api_key: str, executor_model: str = "claude-sonnet-5",
                 max_tokens: int = 4096):
        self.api_key        = api_key
        self.executor_model = executor_model
        self.max_tokens     = max_tokens
        if executor_model not in ADVISOR_EXECUTOR_MODELS:
            print(f"\033[93m⚠ {executor_model} isn't in the documented advisor-tool "
                  f"executor list ({sorted(ADVISOR_EXECUTOR_MODELS)}) — sending anyway, "
                  f"the API will reject it if unsupported.\033[0m")

    def _post(self, payload: dict) -> dict:
        headers = {
            "Content-Type":      "application/json",
            "x-api-key":         self.api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta":    ADVISOR_TOOL_BETA,
        }
        req = urllib.request.Request(
            ENDPOINT, data=json.dumps(payload).encode(),
            headers=headers, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.read().decode(), "status": e.code}
        except Exception as e:
            return {"error": str(e)}

    def run(self, prompt: str, advisor_tool: dict,
            extra_tools: Optional[list[dict]] = None,
            system: Optional[str] = None,
            max_advisor_calls: int = 10,
            verbose: bool = True) -> str:
        """Single user turn, resolving any pause_turn advisor round trips
        along the way. max_advisor_calls is client-side bookkeeping (the
        advisor tool has no built-in conversation-level cap per the docs);
        once hit, the advisor tool is dropped from tools and any
        advisor_tool_result blocks are stripped from history, matching the
        documented approach for retiring the advisor mid-conversation."""
        tools    = [advisor_tool] + (extra_tools or [])
        messages = [{"role": "user", "content": prompt}]
        advisor_calls = 0

        while True:
            payload: dict = {
                "model":      self.executor_model,
                "max_tokens": self.max_tokens,
                "messages":   messages,
                "tools":      tools,
            }
            if system:
                payload["system"] = system

            data = self._post(payload)
            if "error" in data:
                return f"[ERROR] {data['error']}"

            stop_reason = data.get("stop_reason", "")
            content     = data.get("content", [])

            for block in content:
                if block.get("type") == "server_tool_use" and block.get("name") == "advisor":
                    advisor_calls += 1
                    if verbose:
                        print(f"\033[90m  [advisor call #{advisor_calls}]\033[0m")
                if block.get("type") == "advisor_tool_result" and verbose:
                    txt = "".join(
                        c.get("text", "") for c in block.get("content", [])
                        if isinstance(c, dict) and c.get("type") == "text"
                    )
                    if txt:
                        print(f"\033[90m  [advisor guidance] {txt[:200]}"
                              f"{'...' if len(txt) > 200 else ''}\033[0m")

            messages.append({"role": "assistant", "content": content})

            if stop_reason == "pause_turn":
                if advisor_calls >= max_advisor_calls:
                    if verbose:
                        print(f"\033[93m⚠ max_advisor_calls ({max_advisor_calls}) reached — "
                              f"dropping the advisor tool and continuing without it.\033[0m")
                    tools = [t for t in tools if t.get("type") != ADVISOR_TOOL_TYPE]
                    messages = _strip_advisor_blocks(messages)
                # No new user message or tool_result needed — just resend;
                # the API runs the pending advisor call and continues.
                continue

            if stop_reason == "tool_use":
                # A client tool was called in the same turn as a pending
                # advisor call. Caller must execute those and send results;
                # this simple loop only handles the advisor-only case.
                pending = [b for b in content if b.get("type") == "tool_use"]
                if pending:
                    return ("[TOOL_USE] Executor called client tool(s) "
                            f"{[b['name'] for b in pending]} — send tool_result "
                            f"blocks and resend to continue (see 'Mixing server "
                            f"tools and client tools in one turn').")
                continue

            if stop_reason == "end_turn":
                return "".join(b.get("text", "") for b in content if b.get("type") == "text")

            return f"[UNEXPECTED stop_reason={stop_reason}]"


def _strip_advisor_blocks(messages: list) -> list:
    """Remove server_tool_use(advisor) / advisor_tool_result blocks from
    history before dropping the advisor tool — the API 400s if it sees
    advisor_tool_result blocks without the advisor tool present."""
    cleaned = []
    for m in messages:
        content = m.get("content")
        if isinstance(content, list):
            content = [
                b for b in content
                if not (isinstance(b, dict) and (
                    (b.get("type") == "server_tool_use" and b.get("name") == "advisor")
                    or b.get("type") == "advisor_tool_result"
                ))
            ]
        cleaned.append({**m, "content": content})
    return cleaned


# ── CLI entry point ─────────────────────────────────────────────────────────

def cmd_advisor(prompt: str, api_key: str, executor_model: str,
                advisor_model: str = "claude-opus-4-8",
                max_uses: Optional[int] = None,
                advisor_max_tokens: Optional[int] = None):
    print(f"\033[94mℹ Advisor tool | executor={executor_model} advisor={advisor_model}\033[0m\n")
    advisor_tool = build_advisor_tool(
        advisor_model=advisor_model, max_uses=max_uses, max_tokens=advisor_max_tokens,
    )
    ac = AdvisorCoder(api_key=api_key, executor_model=executor_model)
    result = ac.run(prompt, advisor_tool)
    print(result)
    return result