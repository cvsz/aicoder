"""
claude_thinking.py — Extended Thinking & Adaptive Thinking
AI Model Coder CLI v1.8.0

Wraps the Anthropic SDK to expose:
  • Extended thinking  (explicit budget_tokens)
  • Adaptive thinking  (model decides when/how much to think)
  • Effort levels      (low / medium / high / max)
  • Streaming thinking blocks
  • Thinking display   (show / hide / summary)

CLI flags added in main.py:
  --thinking                 Enable extended thinking
  --thinking-budget N        Token budget (default 8000, min 1024)
  --effort low|medium|high|max
  --adaptive                 Let model decide thinking depth
  --stream                   Stream the response (with thinking blocks)
  --show-thinking            Print thinking content to stderr
"""

import os
import sys
import json
import anthropic
from typing import Optional


# ── Effort → budget mapping ────────────────────────────────────────────────
EFFORT_BUDGETS = {
    "low":    2_000,
    "medium": 8_000,
    "high":   16_000,
    "max":    32_000,
}


class ThinkingCoder:
    """Claude client with extended / adaptive thinking support."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-5",
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
    ) -> dict:
        """
        Returns {"thinking": str, "response": str, "usage": dict}
        """
        if effort and effort in EFFORT_BUDGETS:
            budget_tokens = EFFORT_BUDGETS[effort]

        # Build betas header
        betas = []

        # thinking config
        if adaptive:
            thinking_cfg = {"type": "adaptive", "budget_tokens": budget_tokens}
        else:
            thinking_cfg = {"type": "enabled", "budget_tokens": budget_tokens}

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
    ) -> str:
        """Stream response, optionally printing thinking blocks to stderr."""
        if effort and effort in EFFORT_BUDGETS:
            budget_tokens = EFFORT_BUDGETS[effort]

        thinking_cfg = {"type": "enabled", "budget_tokens": budget_tokens}
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
                 stream: bool, system: str = None):
    """Called from main.py --thinking"""
    tc = ThinkingCoder(api_key=api_key, model=model)

    print(f"\033[94mℹ Extended Thinking | effort={effort or 'custom'} | budget={budget} tokens\033[0m\n")

    if stream:
        result = tc.stream_with_thinking(
            prompt, system=system, budget_tokens=budget,
            effort=effort, show_thinking=show_thinking,
        )
        return result
    else:
        result = tc.generate_with_thinking(
            prompt, system=system, budget_tokens=budget,
            effort=effort, adaptive=adaptive, show_thinking=show_thinking,
        )
        print(result["response"])
        usage = result.get("usage", {})
        if usage:
            print(f"\n\033[90m[tokens] input={usage.get('input_tokens',0)}  "
                  f"output={usage.get('output_tokens',0)}  "
                  f"thinking={usage.get('thinking_input_tokens',0)}\033[0m")
        return result["response"]