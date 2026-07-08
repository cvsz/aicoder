"""tests/test_claude_admin_api.py

Covers claude_admin_api.py: the Usage/Cost report query building and
default date range, the 401/403 admin-key-required error hint, API key
revoke (status -> inactive, no delete endpoint), and that
--admin-create-key is a pure explanation with no network call.
"""
import re

import pytest

from claude_admin_api import (
    AdminApiClient,
    cmd_usage_report,
    cmd_cost_report,
    cmd_admin_list_keys,
    cmd_admin_revoke_key,
    cmd_admin_create_key,
    _default_date_range,
)


# ── AdminApiClient query building ────────────────────────────────────────


def test_get_usage_report_builds_expected_params(monkeypatch):
    client = AdminApiClient(admin_api_key="admin-k")
    captured = {}
    monkeypatch.setattr(client, "_get", lambda path, params=None: (
        captured.update(path=path, params=params) or {"data": []}
    ))

    client.get_usage_report("2026-06-01", "2026-07-01", group_by="api_key_id")

    assert captured["path"] == "/usage_report"
    assert captured["params"] == {
        "starting_at": "2026-06-01", "ending_at": "2026-07-01",
        "group_by": "api_key_id",
    }


def test_get_cost_report_builds_expected_params(monkeypatch):
    client = AdminApiClient(admin_api_key="admin-k")
    captured = {}
    monkeypatch.setattr(client, "_get", lambda path, params=None: (
        captured.update(path=path, params=params) or {"data": []}
    ))

    client.get_cost_report("2026-06-01", "2026-07-01")

    assert captured["path"] == "/cost_report"
    assert captured["params"]["group_by"] == "model"


def test_revoke_api_key_sets_status_inactive_not_delete(monkeypatch):
    client = AdminApiClient(admin_api_key="admin-k")
    captured = {}
    monkeypatch.setattr(client, "_post", lambda path, payload: (
        captured.update(path=path, payload=payload) or {"id": "key_1", "status": "inactive"}
    ))

    client.revoke_api_key("key_1")

    assert captured["path"] == "/api_keys/key_1"
    assert captured["payload"] == {"status": "inactive"}


def test_default_date_range_is_30_days():
    start, end = _default_date_range()
    from datetime import date
    d1 = date.fromisoformat(start)
    d2 = date.fromisoformat(end)
    assert (d2 - d1).days == 30


# ── cmd_* error handling / admin-key hint ────────────────────────────────


def test_cmd_usage_report_prints_admin_key_hint_on_403(monkeypatch, capsys):
    client = AdminApiClient(admin_api_key="regular-looking-key")
    monkeypatch.setattr(
        "claude_admin_api.AdminApiClient",
        lambda admin_api_key: client,
    )
    monkeypatch.setattr(client, "get_usage_report",
                        lambda start, end, group_by="model": {"error": "forbidden", "status": 403})

    result = cmd_usage_report("regular-looking-key")

    assert result is None
    out = capsys.readouterr().out
    assert "Admin API key" in out


def test_cmd_cost_report_prints_rows(monkeypatch, capsys):
    client = AdminApiClient(admin_api_key="k")
    monkeypatch.setattr("claude_admin_api.AdminApiClient", lambda admin_api_key: client)
    monkeypatch.setattr(client, "get_cost_report",
                        lambda start, end, group_by="model": {
                            "data": [{"model": "claude-sonnet-5", "amount": "12.50", "currency": "usd"}]
                        })

    result = cmd_cost_report("k", start="2026-06-01", end="2026-07-01")

    assert result["data"][0]["amount"] == "12.50"
    out = capsys.readouterr().out
    assert "claude-sonnet-5" in out
    assert "12.50" in out


def test_cmd_admin_list_keys_prints_each_key(monkeypatch, capsys):
    client = AdminApiClient(admin_api_key="k")
    monkeypatch.setattr("claude_admin_api.AdminApiClient", lambda admin_api_key: client)
    monkeypatch.setattr(client, "list_api_keys", lambda limit=20: {
        "data": [{"id": "key_1", "name": "prod", "status": "active"}]
    })

    result = cmd_admin_list_keys("k")

    assert result["data"][0]["id"] == "key_1"
    out = capsys.readouterr().out
    assert "key_1" in out and "active" in out


def test_cmd_admin_revoke_key_success_message(monkeypatch, capsys):
    client = AdminApiClient(admin_api_key="k")
    monkeypatch.setattr("claude_admin_api.AdminApiClient", lambda admin_api_key: client)
    monkeypatch.setattr(client, "revoke_api_key", lambda key_id: {"id": key_id, "status": "inactive"})

    result = cmd_admin_revoke_key("k", "key_1")

    assert result["status"] == "inactive"
    out = capsys.readouterr().out
    assert "key_1" in out


def test_cmd_admin_revoke_key_error(monkeypatch, capsys):
    client = AdminApiClient(admin_api_key="k")
    monkeypatch.setattr("claude_admin_api.AdminApiClient", lambda admin_api_key: client)
    monkeypatch.setattr(client, "revoke_api_key", lambda key_id: {"error": "not found"})

    result = cmd_admin_revoke_key("k", "ghost")

    assert result is None
    out = capsys.readouterr().out
    assert "Failed to revoke" in out


# ── --admin-create-key: explanation only, no network ────────────────────


def test_cmd_admin_create_key_makes_no_network_call(monkeypatch, capsys):
    def boom(*a, **kw):
        raise AssertionError("cmd_admin_create_key must not touch the network")

    monkeypatch.setattr("claude_admin_api.AdminApiClient", boom)

    result = cmd_admin_create_key("my-new-key")

    assert result is None
    out = capsys.readouterr().out
    assert "no documented create-key endpoint" in out
    assert "my-new-key" in out
