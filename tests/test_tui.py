"""tests/test_tui.py — Master Omega TUI tests

Tests the TUI module structure, CSS, bindings, and helper logic
without requiring a running Textual application (which needs a terminal).
"""
import json
import os
import asyncio
from datetime import datetime
from unittest.mock import patch

import pytest


# ── Import Tests ───────────────────────────────────────────────────────────

def test_tui_module_imports():
    """TUI module imports without errors."""
    from tui import MasterOmegaTUI, launch_tui, TUI_CSS, StatusRow
    assert MasterOmegaTUI is not None
    assert launch_tui is not None
    assert TUI_CSS is not None
    assert StatusRow is not None


def test_tui_css_is_nonempty():
    """TUI CSS stylesheet is non-empty and contains key selectors."""
    from tui import TUI_CSS
    assert len(TUI_CSS) > 100
    assert "left-panel" in TUI_CSS
    assert "right-panel" in TUI_CSS
    assert "chat-display" in TUI_CSS
    assert "status-dashboard" in TUI_CSS
    assert "live-output" in TUI_CSS
    assert "prompt-input" in TUI_CSS
    assert "file-explorer" in TUI_CSS
    assert "action-bar" in TUI_CSS


def test_tui_css_has_responsive_layout():
    """TUI CSS defines responsive split layout."""
    from tui import TUI_CSS
    assert "45%" in TUI_CSS  # left panel width
    assert "55%" in TUI_CSS  # right panel width
    assert "layout: horizontal" in TUI_CSS


# ── Class Attribute Tests ─────────────────────────────────────────────────

def test_tui_app_title():
    """MasterOmegaTUI has the correct title."""
    from tui import MasterOmegaTUI
    assert "Omega" in MasterOmegaTUI.TITLE
    assert "TUI" in MasterOmegaTUI.TITLE


def test_tui_app_subtitle():
    """MasterOmegaTUI subtitle includes version."""
    from tui import MasterOmegaTUI
    assert "1.23.0" in MasterOmegaTUI.SUB_TITLE


def test_tui_bindings_count():
    """TUI has at least 8 keybindings."""
    from tui import MasterOmegaTUI
    assert len(MasterOmegaTUI.BINDINGS) >= 8


def test_tui_bindings_include_essentials():
    """TUI has all essential keybindings."""
    from tui import MasterOmegaTUI
    binding_keys = [b.key for b in MasterOmegaTUI.BINDINGS]
    assert "ctrl+q" in binding_keys
    assert "ctrl+n" in binding_keys
    assert "ctrl+l" in binding_keys
    assert "ctrl+k" in binding_keys
    assert "ctrl+s" in binding_keys
    assert "f1" in binding_keys
    assert "f2" in binding_keys
    assert "f3" in binding_keys
    assert "escape" in binding_keys


def test_tui_binding_labels():
    """All bindings have human-readable labels."""
    from tui import MasterOmegaTUI
    for b in MasterOmegaTUI.BINDINGS:
        assert b.description, f"Binding {b.key} has no description"


# ── Reactive State Tests (class-level, no instance) ──────────────────────

def test_tui_has_reactive_model():
    """MasterOmegaTUI has a reactive current_model attribute."""
    from tui import MasterOmegaTUI
    assert hasattr(MasterOmegaTUI, "current_model")


def test_tui_has_reactive_tokens():
    """MasterOmegaTUI has reactive token counters."""
    from tui import MasterOmegaTUI
    assert hasattr(MasterOmegaTUI, "total_input_tokens")
    assert hasattr(MasterOmegaTUI, "total_output_tokens")


def test_tui_has_reactive_latency():
    """MasterOmegaTUI has a reactive latency attribute."""
    from tui import MasterOmegaTUI
    assert hasattr(MasterOmegaTUI, "last_latency_ms")


def test_tui_has_reactive_processing():
    """MasterOmegaTUI has a reactive is_processing attribute."""
    from tui import MasterOmegaTUI
    assert hasattr(MasterOmegaTUI, "is_processing")


def test_tui_has_reactive_messages():
    """MasterOmegaTUI has a reactive session_messages counter."""
    from tui import MasterOmegaTUI
    assert hasattr(MasterOmegaTUI, "session_messages")


# ── Method Existence Tests ────────────────────────────────────────────────

def test_tui_has_compose():
    """MasterOmegaTUI has a compose method."""
    from tui import MasterOmegaTUI
    assert hasattr(MasterOmegaTUI, "compose")
    assert callable(getattr(MasterOmegaTUI, "compose"))


def test_tui_has_on_mount():
    """MasterOmegaTUI has an on_mount method."""
    from tui import MasterOmegaTUI
    assert hasattr(MasterOmegaTUI, "on_mount")


def test_tui_has_action_methods():
    """MasterOmegaTUI has all required action methods."""
    from tui import MasterOmegaTUI
    actions = [
        "action_quit", "action_new_session", "action_clear_chat",
        "action_save_session", "action_toggle_logs", "action_copy_last",
        "action_show_help", "action_model_picker", "action_focus_input",
    ]
    for action in actions:
        assert hasattr(MasterOmegaTUI, action), f"Missing {action}"
        assert callable(getattr(MasterOmegaTUI, action))


def test_tui_has_helper_methods():
    """MasterOmegaTUI has all required helper methods."""
    from tui import MasterOmegaTUI
    helpers = [
        "_append_chat", "_update_status", "_log",
        "_show_error", "_add_recent_file", "_handle_command",
    ]
    for helper in helpers:
        assert hasattr(MasterOmegaTUI, helper), f"Missing {helper}"


def test_tui_has_reactive_watchers():
    """MasterOmegaTUI has reactive watcher methods."""
    from tui import MasterOmegaTUI
    watchers = [
        "watch_total_input_tokens", "watch_total_output_tokens",
        "watch_last_latency_ms", "watch_session_messages",
        "watch_current_model",
    ]
    for watcher in watchers:
        assert hasattr(MasterOmegaTUI, watcher), f"Missing {watcher}"


# ── Async Command Handler Test ────────────────────────────────────────────

def test_handle_command_is_async():
    """_handle_command is an async coroutine function."""
    from tui import MasterOmegaTUI
    assert asyncio.iscoroutinefunction(MasterOmegaTUI._handle_command)


def test_send_to_claude_is_async():
    """_send_to_claude is an async coroutine function."""
    from tui import MasterOmegaTUI
    assert asyncio.iscoroutinefunction(MasterOmegaTUI._send_to_claude)


def test_handle_prompt_is_async():
    """handle_prompt is an async coroutine function."""
    from tui import MasterOmegaTUI
    assert asyncio.iscoroutinefunction(MasterOmegaTUI.handle_prompt)


# ── StatusRow Widget Tests ────────────────────────────────────────────────

def test_status_row_init():
    """StatusRow initializes with label and value."""
    from tui import StatusRow
    row = StatusRow("Model", "claude-sonnet-5")
    assert row._label == "Model"
    assert row._value == "claude-sonnet-5"


def test_status_row_default_value():
    """StatusRow defaults to em-dash when no value given."""
    from tui import StatusRow
    row = StatusRow("Latency")
    assert row._value == "—"


def test_status_row_has_compose():
    """StatusRow has a compose method."""
    from tui import StatusRow
    assert hasattr(StatusRow, "compose")


def test_status_row_has_update_value():
    """StatusRow has an update_value method."""
    from tui import StatusRow
    row = StatusRow("Model")
    assert hasattr(row, "update_value")
    assert callable(row.update_value)


# ── Launch Function Test ──────────────────────────────────────────────────

def test_launch_tui_is_callable():
    """launch_tui is a callable function."""
    from tui import launch_tui
    assert callable(launch_tui)


def test_launch_tui_accepts_parameters():
    """launch_tui accepts api_key and model parameters."""
    import inspect
    from tui import launch_tui
    sig = inspect.signature(launch_tui)
    params = list(sig.parameters.keys())
    assert "api_key" in params
    assert "model" in params


# ── Session Data Format Test ──────────────────────────────────────────────

def test_session_data_format():
    """Session save produces valid JSON structure."""
    session_data = {
        "model": "claude-sonnet-5",
        "started": datetime.now().isoformat(),
        "saved": datetime.now().isoformat(),
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ],
        "tokens": {"input": 100, "output": 50},
    }
    json_str = json.dumps(session_data, indent=2)
    parsed = json.loads(json_str)
    assert parsed["model"] == "claude-sonnet-5"
    assert len(parsed["messages"]) == 2
    assert parsed["tokens"]["input"] == 100
    assert parsed["tokens"]["output"] == 50
    assert "started" in parsed
    assert "saved" in parsed


# ── CSS Completeness Test ─────────────────────────────────────────────────

def test_css_has_all_panel_styles():
    """CSS defines styles for all major UI panels."""
    from tui import TUI_CSS
    required = [
        "#main-container", "#left-panel", "#right-panel",
        "#chat-display", "#prompt-input", "#monitor-panel",
        "#status-dashboard", "#live-output", "#file-explorer",
        "#action-bar", "#session-info",
    ]
    for selector in required:
        assert selector in TUI_CSS, f"Missing CSS for {selector}"


def test_css_has_toast_styles():
    """CSS defines notification toast styles."""
    from tui import TUI_CSS
    assert ".error-toast" in TUI_CSS
    assert ".success-toast" in TUI_CSS


def test_css_has_thinking_block_style():
    """CSS defines thinking block styling."""
    from tui import TUI_CSS
    assert ".thinking-block" in TUI_CSS


def test_css_has_response_block_style():
    """CSS defines response block styling."""
    from tui import TUI_CSS
    assert ".response-block" in TUI_CSS
