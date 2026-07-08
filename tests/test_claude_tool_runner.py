"""tests/test_claude_tool_runner.py

Covers claude_tool_runner.py — the SDK's client.beta.messages.tool_runner
wrapper added in v1.19.0 to close the gap where claude_tools.py's
docstring claimed a "Tool runner" feature / --tool-run flag that was
never actually implemented (confirmed absent: no argparse flag, no
tool_runner/beta_tool code path anywhere in the tree before this cycle).
"""
import os

import pytest

from claude_tool_runner import (
    read_file,
    list_directory,
    run_tool_runner,
    cmd_tool_runner,
    DEFAULT_TOOLS,
)


# ── local tool functions ─────────────────────────────────────────────────


def test_read_file_returns_contents(tmp_path):
    f = tmp_path / "hello.txt"
    f.write_text("hello world")
    assert read_file(str(f)) == "hello world"


def test_read_file_missing_returns_error_string():
    result = read_file("/definitely/does/not/exist.txt")
    assert result.startswith("[ERROR]")


def test_list_directory_lists_entries(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "b.txt").write_text("y")
    result = list_directory(str(tmp_path))
    assert "a.txt" in result
    assert "b.txt" in result


def test_list_directory_missing_returns_error_string():
    result = list_directory("/definitely/does/not/exist/dir")
    assert result.startswith("[ERROR]")


def test_default_tools_includes_both():
    assert read_file in DEFAULT_TOOLS
    assert list_directory in DEFAULT_TOOLS


# ── run_tool_runner() ─────────────────────────────────────────────────────


class _FakeTextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FakeMessage:
    def __init__(self, text):
        self.content = [_FakeTextBlock(text)]


class _FakeToolRunner:
    """Mimics the iterator client.beta.messages.tool_runner() returns."""

    def __init__(self, messages_out):
        self._messages_out = messages_out

    def __iter__(self):
        return iter(self._messages_out)


class _FakeBetaMessages:
    def __init__(self, messages_out):
        self.last_kwargs = None
        self._messages_out = messages_out

    def tool_runner(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeToolRunner(self._messages_out)


class _FakeBeta:
    def __init__(self, messages_out):
        self.messages = _FakeBetaMessages(messages_out)


class _FakeClient:
    def __init__(self, messages_out):
        self.beta = _FakeBeta(messages_out)


def test_run_tool_runner_returns_final_text(monkeypatch):
    fake_client = _FakeClient([_FakeMessage("hi"), _FakeMessage("final answer")])
    monkeypatch.setattr("claude_tool_runner.anthropic.Anthropic", lambda api_key: fake_client)

    result = run_tool_runner("do something", api_key="k", model="claude-opus-4-8")

    assert result == "final answer"
    assert fake_client.beta.messages.last_kwargs["model"] == "claude-opus-4-8"
    assert fake_client.beta.messages.last_kwargs["tools"] == DEFAULT_TOOLS


def test_run_tool_runner_respects_custom_tools(monkeypatch):
    fake_client = _FakeClient([_FakeMessage("ok")])
    monkeypatch.setattr("claude_tool_runner.anthropic.Anthropic", lambda api_key: fake_client)

    run_tool_runner("hi", api_key="k", model="claude-opus-4-8", tools=[read_file])

    assert fake_client.beta.messages.last_kwargs["tools"] == [read_file]


def test_run_tool_runner_stops_at_max_iterations(monkeypatch):
    # 20 messages available, but max_iterations=3 should stop early —
    # this is the safety bound described in the module docstring, since
    # the SDK's tool_runner has no built-in cap of its own.
    many_messages = [_FakeMessage(str(i)) for i in range(20)]
    fake_client = _FakeClient(many_messages)
    monkeypatch.setattr("claude_tool_runner.anthropic.Anthropic", lambda api_key: fake_client)

    result = run_tool_runner("hi", api_key="k", model="claude-opus-4-8", max_iterations=3)

    assert result == "2"  # 3rd message (0-indexed) is where the loop stops


def test_run_tool_runner_empty_iterator_returns_empty_string(monkeypatch):
    fake_client = _FakeClient([])
    monkeypatch.setattr("claude_tool_runner.anthropic.Anthropic", lambda api_key: fake_client)

    result = run_tool_runner("hi", api_key="k", model="claude-opus-4-8")

    assert result == ""


def test_cmd_tool_runner_prints_and_returns(monkeypatch, capsys):
    fake_client = _FakeClient([_FakeMessage("printed answer")])
    monkeypatch.setattr("claude_tool_runner.anthropic.Anthropic", lambda api_key: fake_client)

    result = cmd_tool_runner("hi", api_key="k", model="claude-opus-4-8")

    assert result == "printed answer"
    out = capsys.readouterr().out
    assert "printed answer" in out
