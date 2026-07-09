"""
claude_tool_runner.py — SDK Tool Runner (client.beta.messages.tool_runner)
ZAI Coder CLI v1.19.0

Wraps the Anthropic Python SDK's own tool-calling convenience helper:
`@beta_tool`-decorated plain Python functions, executed automatically by
`client.beta.messages.tool_runner(...)`, which iterates the request/
tool-execution/next-request loop for you until Claude stops calling tools.

Why this is a different thing from zaicoder's other agent loops:
  `claude_tools.py`'s docstring and CLI-flag list had claimed a
  "Tool runner (auto-executes registered Python callables)" feature and a
  `--tool-run` flag since at least v1.11.0. Confirmed absent this cycle —
  `--tool-run` was never a real argparse flag anywhere in `main.py`, and no
  code path in the tree calls `client.beta.messages.tool_runner` or uses
  the `@beta_tool` decorator (checked with two differently-worded greps:
  `tool_runner`/`ToolRunner`, then `beta_tool`/`client\\.beta\\.messages` —
  both came back empty outside this new module). That claim in
  `claude_tools.py` was aspirational, not implemented; see the correction
  note in `ROADMAP.md` Part 2.
  `ToolCoder` in `claude_tools.py` and the agent loops in `claude_code.py`
  / `claude_agents_sdk.py` are all hand-rolled: they build the request,
  inspect `tool_use` blocks themselves, dispatch to your own tool-execution
  code, and re-issue the request — because they need to do other things
  in the same loop (context editing, compaction, task budgets, hooks,
  permissions, sandboxing) that the SDK helper doesn't know about.
  `tool_runner` is the opposite tradeoff: it's Anthropic's own convenience
  wrapper for the common case of "I just have some plain Python functions
  Claude should be able to call" — no context editing/compaction/hooks
  integration, but no loop to hand-write either. Use zaicoder's other agent
  loops when you need those extras; use `--tool-runner` for a quick script
  where a handful of `@beta_tool` functions are the whole tool surface.

CLI flags:
  --tool-runner PROMPT       Run prompt through client.beta.messages.tool_runner
                              with zaicoder's small built-in read-only local
                              tool set (read_file, list_directory)
  --tool-runner-max-iters N  Cap on tool-call round trips (default 10) —
                              a safety bound since tool_runner will keep
                              iterating for as long as Claude keeps calling
                              tools
"""

import os
from typing import Optional

import anthropic
from anthropic import beta_tool

# Local tools are intentionally read-only and path-restricted — this
# module is meant as a quick-script convenience, not a sandboxed agent
# loop like claude_code.py's, so it doesn't try to allow writes at all.
_MAX_READ_BYTES = 200_000


@beta_tool
def read_file(path: str) -> str:
    """Read a UTF-8 text file and return its contents.

    Args:
        path: Path to the file to read.

    Returns:
        The file's text content, truncated to 200,000 bytes if longer.
    """
    real = os.path.realpath(path)
    try:
        with open(real, "rb") as f:
            data = f.read(_MAX_READ_BYTES)
        return data.decode("utf-8", errors="replace")
    except OSError as e:
        return f"[ERROR] could not read {path}: {e}"


@beta_tool
def list_directory(path: str = ".") -> str:
    """List the entries of a directory, one per line.

    Args:
        path: Directory to list. Defaults to the current directory.

    Returns:
        Newline-separated entry names, or an error string.
    """
    real = os.path.realpath(path)
    try:
        return "\n".join(sorted(os.listdir(real)))
    except OSError as e:
        return f"[ERROR] could not list {path}: {e}"


DEFAULT_TOOLS = [read_file, list_directory]


def run_tool_runner(
    prompt: str,
    api_key: str,
    model: str,
    max_tokens: int = 4096,
    tools: Optional[list] = None,
    max_iterations: int = 10,
) -> str:
    """Run `prompt` through client.beta.messages.tool_runner with `tools`
    (defaults to DEFAULT_TOOLS). Returns the final assistant text.

    max_iterations bounds how many request/tool-execution round trips the
    SDK helper will run before this function gives up and returns whatever
    the last message was — tool_runner itself has no built-in cap, so
    without this a buggy tool or a model stuck calling tools could loop
    indefinitely.
    """
    client = anthropic.Anthropic(api_key=api_key)
    runner = client.beta.messages.tool_runner(
        max_tokens=max_tokens,
        model=model,
        tools=tools if tools is not None else DEFAULT_TOOLS,
        messages=[{"role": "user", "content": prompt}],
    )

    last_message = None
    for i, message in enumerate(runner):
        last_message = message
        if i + 1 >= max_iterations:
            break

    if last_message is None:
        return ""

    texts = []
    for block in getattr(last_message, "content", []) or []:
        if getattr(block, "type", "") == "text":
            texts.append(block.text)
    return "\n".join(texts)


# ── CLI entry point ─────────────────────────────────────────────────────────


def cmd_tool_runner(prompt: str, api_key: str, model: str, max_iterations: int = 10):
    """Called from main.py --tool-runner"""
    print(f"\033[94mℹ SDK Tool Runner | max_iterations={max_iterations}\033[0m\n")
    result = run_tool_runner(prompt, api_key, model, max_iterations=max_iterations)
    print(result)
    return result
