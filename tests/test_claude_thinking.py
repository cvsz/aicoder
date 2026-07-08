"""tests/test_claude_thinking.py

Covers claude_thinking.py:
  - pre-existing generate_with_thinking() / stream_with_thinking() behavior
    (effort -> budget mapping, thinking/response text split, usage passthrough)
  - the v1.19.0 adaptive-only model gate: _resolve_thinking_type() and its
    wiring into both generate_with_thinking() and stream_with_thinking()
  - --thinking-allow-manual bypass behavior

Previously this module (claude_thinking.py) had zero test coverage at all.
"""
import sys
import types

import pytest

from claude_thinking import (
    ThinkingCoder,
    THINKING_ADAPTIVE_ONLY,
    EFFORT_BUDGETS,
    _resolve_thinking_type,
    cmd_thinking,
)


# ── _resolve_thinking_type() ────────────────────────────────────────────────


def test_resolve_adaptive_flag_always_wins():
    assert _resolve_thinking_type("claude-haiku-4-5-20251001", adaptive=True, allow_manual=False) == "adaptive"
    assert _resolve_thinking_type("claude-opus-4-8", adaptive=True, allow_manual=False) == "adaptive"


def test_resolve_manual_on_extended_only_model_stays_enabled():
    # Haiku 4.5 is "extended" (manual) in MODEL_CATALOG, not adaptive-only.
    assert "claude-haiku-4-5-20251001" not in THINKING_ADAPTIVE_ONLY
    assert _resolve_thinking_type("claude-haiku-4-5-20251001", adaptive=False, allow_manual=False) == "enabled"


@pytest.mark.parametrize("model", sorted(THINKING_ADAPTIVE_ONLY))
def test_resolve_manual_on_adaptive_only_model_is_upgraded(model, capsys):
    result = _resolve_thinking_type(model, adaptive=False, allow_manual=False)
    assert result == "adaptive"
    warning = capsys.readouterr().err
    assert model in warning
    assert "adaptive" in warning.lower()


@pytest.mark.parametrize("model", sorted(THINKING_ADAPTIVE_ONLY))
def test_resolve_manual_on_adaptive_only_model_with_allow_manual(model, capsys):
    result = _resolve_thinking_type(model, adaptive=False, allow_manual=True)
    assert result == "enabled"
    assert capsys.readouterr().err == ""


def test_sonnet_5_is_adaptive_only():
    # The concrete case that motivated this gate this cycle: Sonnet 5's
    # migration notes (checked 2026-07-08) say manual thinking now 400s.
    assert "claude-sonnet-5" in THINKING_ADAPTIVE_ONLY


def test_fable5_and_mythos5_are_adaptive_only():
    assert "claude-fable-5" in THINKING_ADAPTIVE_ONLY
    assert "claude-mythos-5" in THINKING_ADAPTIVE_ONLY
    assert "claude-mythos-preview" in THINKING_ADAPTIVE_ONLY


# ── ThinkingCoder.generate_with_thinking() ──────────────────────────────────


class _FakeBlock:
    def __init__(self, type_, **kw):
        self.type = type_
        for k, v in kw.items():
            setattr(self, k, v)


class _FakeUsage:
    def model_dump(self):
        return {"input_tokens": 10, "output_tokens": 5, "thinking_input_tokens": 3}


class _FakeResponse:
    def __init__(self, thinking_text="pondering", response_text="hello"):
        self.content = [
            _FakeBlock("thinking", thinking=thinking_text),
            _FakeBlock("text", text=response_text),
        ]
        self.usage = _FakeUsage()


class _FakeMessages:
    def __init__(self):
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeResponse()


class _FakeClient:
    def __init__(self):
        self.messages = _FakeMessages()


def _coder(model="claude-sonnet-4-6"):
    tc = ThinkingCoder(api_key="k", model=model)
    tc.client = _FakeClient()
    return tc


def test_generate_with_thinking_splits_blocks():
    tc = _coder()
    result = tc.generate_with_thinking("hi")
    assert result["thinking"] == "pondering"
    assert result["response"] == "hello"
    assert result["usage"]["input_tokens"] == 10
    assert result["model"] == "claude-sonnet-4-6"


def test_generate_with_thinking_effort_overrides_budget():
    tc = _coder()
    tc.generate_with_thinking("hi", effort="high", budget_tokens=1)
    sent = tc.client.messages.last_kwargs["thinking"]
    assert sent["budget_tokens"] == EFFORT_BUDGETS["high"]


def test_generate_with_thinking_default_manual_on_non_gated_model():
    # claude-haiku-4-5-20251001 is the one MODEL_CATALOG entry that's
    # "extended" (manual), not "adaptive" — everything else in the current
    # catalog is adaptive-only, which is exactly the finding this cycle's
    # gap is about.
    tc = _coder(model="claude-haiku-4-5-20251001")
    tc.generate_with_thinking("hi")
    assert tc.client.messages.last_kwargs["thinking"]["type"] == "enabled"


def test_generate_with_thinking_auto_upgrades_on_gated_model(capsys):
    tc = _coder(model="claude-opus-4-8")
    tc.generate_with_thinking("hi")
    assert tc.client.messages.last_kwargs["thinking"]["type"] == "adaptive"
    assert "adaptive" in capsys.readouterr().err.lower()


def test_generate_with_thinking_allow_manual_bypasses_gate(capsys):
    tc = _coder(model="claude-opus-4-8")
    tc.generate_with_thinking("hi", allow_manual=True)
    assert tc.client.messages.last_kwargs["thinking"]["type"] == "enabled"
    assert capsys.readouterr().err == ""


def test_generate_with_thinking_adaptive_flag_always_adaptive():
    tc = _coder(model="claude-haiku-4-5-20251001")
    tc.generate_with_thinking("hi", adaptive=True)
    assert tc.client.messages.last_kwargs["thinking"]["type"] == "adaptive"


# ── ThinkingCoder.stream_with_thinking() ────────────────────────────────────


class _FakeStreamEvent:
    def __init__(self, type_, content_block=None, delta=None):
        self.type = type_
        self.content_block = content_block
        self.delta = delta


class _FakeStreamCtx:
    def __init__(self, events):
        self._events = events

    def __enter__(self):
        return iter(self._events)

    def __exit__(self, *a):
        return False


class _FakeStreamingMessages(_FakeMessages):
    def stream(self, **kwargs):
        self.last_kwargs = kwargs
        text_block = types.SimpleNamespace(type="text")
        text_delta = types.SimpleNamespace(type="text_delta", text="hi")
        events = [
            _FakeStreamEvent("content_block_start", content_block=text_block),
            _FakeStreamEvent("content_block_delta", delta=text_delta),
        ]
        return _FakeStreamCtx(events)


def _streaming_coder(model="claude-sonnet-4-6"):
    tc = ThinkingCoder(api_key="k", model=model)
    tc.client = types.SimpleNamespace(messages=_FakeStreamingMessages())
    return tc


def test_stream_with_thinking_defaults_manual_on_non_gated_model():
    tc = _streaming_coder("claude-haiku-4-5-20251001")
    tc.stream_with_thinking("hi")
    assert tc.client.messages.last_kwargs["thinking"]["type"] == "enabled"


def test_stream_with_thinking_auto_upgrades_on_gated_model(capsys):
    tc = _streaming_coder("claude-sonnet-5")
    tc.stream_with_thinking("hi")
    assert tc.client.messages.last_kwargs["thinking"]["type"] == "adaptive"
    assert "claude-sonnet-5" in capsys.readouterr().err


def test_stream_with_thinking_adaptive_param_supported():
    # Previously stream_with_thinking had no `adaptive` parameter at all.
    tc = _streaming_coder("claude-haiku-4-5-20251001")
    tc.stream_with_thinking("hi", adaptive=True)
    assert tc.client.messages.last_kwargs["thinking"]["type"] == "adaptive"


# ── cmd_thinking() wiring ────────────────────────────────────────────────────


def test_cmd_thinking_passes_allow_manual_through(monkeypatch):
    captured = {}

    class _Stub:
        def __init__(self, api_key, model):
            pass

        def generate_with_thinking(self, prompt, **kwargs):
            captured.update(kwargs)
            return {"thinking": "", "response": "ok", "usage": {}}

    monkeypatch.setattr("claude_thinking.ThinkingCoder", _Stub)
    cmd_thinking(prompt="hi", api_key="k", model="claude-opus-4-8", budget=8000,
                 effort=None, adaptive=False, show_thinking=False, stream=False,
                 allow_manual=True)
    assert captured["allow_manual"] is True
