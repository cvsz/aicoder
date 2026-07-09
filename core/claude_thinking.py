"""
claude_thinking.py — Extended Thinking & Adaptive Thinking
ZAI Coder CLI v1.23.0

Wraps the Anthropic SDK to expose:
  • Extended thinking  (explicit budget_tokens)
  • Adaptive thinking  (model decides when/how much to think)
  • Effort levels      (low / medium / high / xhigh / max)
  • Streaming thinking blocks
  • Thinking display   (summarized / omitted)

CLI flags added in main.py:
  --thinking                 Enable extended thinking
  --thinking-budget N        Token budget (default 8000, min 1024)
  --effort low|medium|high|xhigh|max
  --adaptive                 Let model decide thinking depth
  --thinking-display MODE    summarized (default for older models) or
                             omitted (default for Fable 5/Mythos 5/Sonnet 5/
                             Opus 4.8/4.7 — reduces latency by not streaming
                             thinking tokens; full thinking tokens still billed)
  --stream                   Stream the response (with thinking blocks)
  --show-thinking            Print thinking content to stderr
"""

import os
import sys
import json
import anthropic
from typing import Optional


# ── Effort → budget mapping ────────────────────────────────────────────────
# Five levels per output_config.effort (platform.claude.com/docs, checked
# 2026-07-09): low, medium, high, xhigh, max.
EFFORT_BUDGETS = {
    "low":    2_000,
    "medium": 8_000,
    "high":   16_000,
    "xhigh":  24_000,
    "max":    32_000,
}

# ── Adaptive-only models ───────────────────────────────────────────────────
# These models always use adaptive thinking (type: "adaptive" instead of
# "enabled"). The API returns an error if you try type: "enabled" on them.
# Checked against claude_models.py MODEL_CATALOG (2026-07-09).
# Sonnet 5 added per migration notes (checked 2026-07-08): manual thinking
# now 400s.
THINKING_ADAPTIVE_ONLY = frozenset({
    "claude-fable-5",
    "claude-mythos-5",
    "claude-mythos-preview",
    "claude-sonnet-5",
    "claude-opus-4-8",
})


def _resolve_thinking_type(model: str, adaptive: bool = False,
                           allow_manual: bool = False) -> str:
    """Return the thinking config type for a given model.

    Returns "adaptive" if adaptive=True is explicitly passed, or if the
    model is in THINKING_ADAPTIVE_ONLY and allow_manual is False.
    Returns "enabled" otherwise.

    When a model is adaptive-only and allow_manual is False, prints a
    warning to stderr explaining the auto-upgrade.
    """
    if adaptive:
        return "adaptive"
    if model in THINKING_ADAPTIVE_ONLY:
        if allow_manual:
            return "enabled"
        import sys
        print(f"\033[93m⚠ {model} requires adaptive thinking — "
              f"auto-upgrading from 'enabled' to 'adaptive'\033[0m",
              file=sys.stderr)
        return "adaptive"
    return "enabled"


class ThinkingCoder:
    """Claude client with extended / adaptive thinking support."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6",
                 max_tokens: int = 8000):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model   = model
        self.max_tokens = max_tokens

    # ── Single-shot with thinking ──────────────────────────────────────────

    def generate_with_thinking(
        self,
        prompt: str,
        system: Optional[str] = None,
        budget_tokens: int = 8_000,
        effort: Optional[str] = None,
        adaptive: bool = False,
        show_thinking: bool = False,
        display: Optional[str] = None,
        allow_manual: bool = False,
    ) -> dict:
        """
        Returns {"thinking": str, "response": str, "usage": dict}

        display: "summarized" or "omitted" (or None for API default).
        When "omitted", thinking blocks return empty content with a
        signature for multi-turn continuity — reduces latency but full
        thinking tokens are still billed. Default on Fable 5, Mythos 5,
        Sonnet 5, Opus 4.8/4.7 is already "omitted" server-side.

        allow_manual: bypass the adaptive-only gate, allowing "enabled"
        thinking on models that normally require adaptive. Use with
        caution — the API may 400.
        """
        if effort and effort in EFFORT_BUDGETS:
            budget_tokens = EFFORT_BUDGETS[effort]

        # Build betas header
        betas = []

        # thinking config — resolve type via the adaptive-only gate
        thinking_type = _resolve_thinking_type(
            self.model, adaptive=adaptive, allow_manual=allow_manual)
        thinking_cfg: dict = {"type": thinking_type, "budget_tokens": budget_tokens}

        # display control (platform.claude.com/docs, checked 2026-07-09)
        if display in ("summarized", "omitted"):
            thinking_cfg["display"] = display

        kwargs = dict(
            model=self.model,
            max_tokens=max(self.max_tokens, budget_tokens + 1000),
            thinking=thinking_cfg,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system
        if betas:
            kwargs["betas"] = betas

        resp = self.client.messages.create(**kwargs)

        thinking_text = ""
        response_text = ""
        for block in resp.content:
            if block.type == "thinking":
                thinking_text = block.thinking
            elif block.type == "text":
                response_text += block.text

        if show_thinking and thinking_text:
            print("\n\033[90m── THINKING ──────────────────────\033[0m", file=sys.stderr)
            print(thinking_text, file=sys.stderr)
            print("\033[90m── END THINKING ──────────────────\033[0m\n", file=sys.stderr)

        return {
            "thinking":  thinking_text,
            "response":  response_text,
            "usage":     resp.usage.model_dump() if hasattr(resp.usage, "model_dump") else {},
            "model":     self.model,
        }

    # ── Streaming with thinking ────────────────────────────────────────────

    def stream_with_thinking(
        self,
        prompt: str,
        system: Optional[str] = None,
        budget_tokens: int = 8_000,
        effort: Optional[str] = None,
        show_thinking: bool = False,
        display: Optional[str] = None,
        adaptive: bool = False,
        allow_manual: bool = False,
    ) -> str:
        """Stream response, optionally printing thinking blocks to stderr.

        When display="omitted", no thinking_delta events are emitted —
        only a signature_delta before text streaming begins. The show_thinking
        flag has no visible effect in omitted mode (thinking content is empty).
        """
        if effort and effort in EFFORT_BUDGETS:
            budget_tokens = EFFORT_BUDGETS[effort]

        thinking_cfg: dict = {"type": _resolve_thinking_type(
            self.model, adaptive=adaptive, allow_manual=allow_manual),
            "budget_tokens": budget_tokens}
        if display in ("summarized", "omitted"):
            thinking_cfg["display"] = display

        kwargs = dict(
            model=self.model,
            max_tokens=max(self.max_tokens, budget_tokens + 1000),
            thinking=thinking_cfg,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system

        full_response = ""
        in_thinking   = False

        with self.client.messages.stream(**kwargs) as stream:
            for event in stream:
                etype = getattr(event, "type", "")

                if etype == "content_block_start":
                    bt = getattr(event.content_block, "type", "")
                    if bt == "thinking":
                        in_thinking = True
                        if show_thinking:
                            print("\n\033[90m[thinking] ", end="", file=sys.stderr, flush=True)
                    elif bt == "text":
                        in_thinking = False

                elif etype == "content_block_delta":
                    delta = event.delta
                    dt = getattr(delta, "type", "")
                    if dt == "thinking_delta" and show_thinking:
                        print(delta.thinking, end="", file=sys.stderr, flush=True)
                    elif dt == "signature_delta":
                        # display="omitted" mode: no thinking_delta events,
                        # only signature_delta before the block closes.
                        # Nothing to show — signature is for multi-turn
                        # continuity, not human-readable.
                        pass
                    elif dt == "text_delta":
                        print(delta.text, end="", flush=True)
                        full_response += delta.text

                elif etype == "content_block_stop" and in_thinking and show_thinking:
                    print("\033[0m", file=sys.stderr)
                    in_thinking = False

        print()  # newline after streaming
        return full_response


# ── CLI entry points ───────────────────────────────────────────────────────

def cmd_thinking(prompt: str, api_key: str, model: str, budget: int,
                 effort: str, adaptive: bool, show_thinking: bool,
                 stream: bool, system: str = None,
                 display: Optional[str] = None,
                 allow_manual: bool = False):
    """Called from main.py --thinking"""
    tc = ThinkingCoder(api_key=api_key, model=model)

    display_note = f" | display={display}" if display else ""
    print(f"\033[94mℹ Extended Thinking | effort={effort or 'custom'} | budget={budget} tokens{display_note}\033[0m\n")

    if stream:
        result = tc.stream_with_thinking(
            prompt, system=system, budget_tokens=budget,
            effort=effort, show_thinking=show_thinking,
            display=display, adaptive=adaptive,
            allow_manual=allow_manual,
        )
        return result
    else:
        result = tc.generate_with_thinking(
            prompt, system=system, budget_tokens=budget,
            effort=effort, adaptive=adaptive, show_thinking=show_thinking,
            display=display, allow_manual=allow_manual,
        )
        print(result["response"])
        usage = result.get("usage", {})
        if usage:
            in_tok  = usage.get("input_tokens", 0)
            out_tok = usage.get("output_tokens", 0)
            # output_tokens_details.thinking_tokens (SDK v0.105.0+):
            # re-tokenized count of internal reasoning tokens. Read-only,
            # always <= output_tokens. Falls back to 0 when absent.
            out_details = usage.get("output_tokens_details") or {}
            think_tok   = out_details.get("thinking_tokens", 0)
            parts = [f"input={in_tok}", f"output={out_tok}"]
            if think_tok:
                parts.append(f"thinking={think_tok}")
            print(f"\n\033[90m[tokens] {'  '.join(parts)}\033[0m")
        return result["response"]
