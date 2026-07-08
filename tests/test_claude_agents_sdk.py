"""tests/test_claude_agents_sdk.py

Covers claude_agents_sdk.py. This module had zero test coverage going
into v1.19.0, so per this cycle's Definition of Done, this file covers
both the pre-existing behavior (PermissionMode, TOOL_PRESETS,
McpServerConfig) and the new v1.19.0 Managed Agents memory store support
(ManagedAgentsClient.create_memory_store, create_session's
memory_store_id wiring, cmd_managed_agent_run's memory_store param,
cmd_agent_memory_store_create).

The real ManagedAgentsClient talks to the hosted Managed Agents API via
the `anthropic` SDK's client.beta.{agents,environments,sessions,
memory_stores} resources, so these tests stub out `anthropic.Anthropic`
rather than hitting the network.
"""
import sys
import types
from unittest.mock import MagicMock

import pytest


def _install_fake_anthropic_module():
    """Install a minimal fake `anthropic` module into sys.modules so
    `import anthropic` inside claude_agents_sdk works without the real
    package needing client.beta.memory_stores (which may not exist in
    whatever SDK version is actually pinned/installed)."""
    fake = types.ModuleType("anthropic")
    fake.Anthropic = MagicMock()
    sys.modules["anthropic"] = fake
    return fake


@pytest.fixture
def agents_sdk(monkeypatch):
    _install_fake_anthropic_module()
    import importlib
    import claude_agents_sdk as mod
    importlib.reload(mod)
    return mod


# ── Pre-existing behavior (previously untested) ─────────────────────────


def test_permission_mode_constants(agents_sdk):
    assert agents_sdk.PermissionMode.ACCEPT_EDITS == "acceptEdits"
    assert agents_sdk.PermissionMode.ASK_PERMISSION == "askPermission"
    assert agents_sdk.PermissionMode.SUPERVISED == "supervised"


def test_tool_presets_contains_expected_groups(agents_sdk):
    assert "all" in agents_sdk.TOOL_PRESETS
    assert "code" in agents_sdk.TOOL_PRESETS
    assert "bash" in agents_sdk.TOOL_PRESETS["all"]
    assert "web_search" not in agents_sdk.TOOL_PRESETS["code"]


def test_managed_agents_beta_header_unchanged(agents_sdk):
    # Regression guard: this header string is load-bearing for every
    # hosted Managed Agents call. Accidentally editing it silently breaks
    # every endpoint call with a 400, not an obvious error.
    assert agents_sdk.MANAGED_AGENTS_BETA == "managed-agents-2026-04-01"


# ── v1.19.0: Managed Agents memory stores ────────────────────────────────


def test_memory_store_beta_header(agents_sdk):
    assert agents_sdk.MEMORY_STORE_BETA == "agent-memory-2026-07-22"


def test_create_memory_store_sends_expected_betas(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    fake_store = MagicMock(id="store_123")
    client.client.beta.memory_stores.create.return_value = fake_store

    result = client.create_memory_store(name="project-x-memory")

    client.client.beta.memory_stores.create.assert_called_once_with(
        name="project-x-memory",
        betas=[agents_sdk.MANAGED_AGENTS_BETA, agents_sdk.MEMORY_STORE_BETA],
    )
    assert result == {"id": "store_123", "name": "project-x-memory"}


def test_create_session_without_memory_store_omits_resources(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    fake_session = MagicMock(id="sess_1")
    client.client.beta.sessions.create.return_value = fake_session

    result = client.create_session("agent_1", "env_1", title="t")

    _, kwargs = client.client.beta.sessions.create.call_args
    assert kwargs["resources"] is None
    assert kwargs["betas"] == [agents_sdk.MANAGED_AGENTS_BETA]
    assert "vault_ids" not in kwargs
    assert result["memory_store_id"] is None


def test_create_session_with_memory_store_mounts_resource(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    fake_session = MagicMock(id="sess_2")
    client.client.beta.sessions.create.return_value = fake_session

    result = client.create_session("agent_1", "env_1", title="t",
                                    memory_store_id="store_123")

    _, kwargs = client.client.beta.sessions.create.call_args
    assert kwargs["resources"] == [
        {"type": "memory_store", "memory_store_id": "store_123"}
    ]
    assert agents_sdk.MEMORY_STORE_BETA in kwargs["betas"]
    assert result["memory_store_id"] == "store_123"


def test_cmd_managed_agent_run_creates_and_mounts_store_when_named(agents_sdk, monkeypatch, capsys):
    mac = MagicMock()
    mac.create_agent.return_value = {"id": "agent_1"}
    mac.create_environment.return_value = {"id": "env_1"}
    mac.create_memory_store.return_value = {"id": "store_1", "name": "notes"}
    mac.create_session.return_value = {"id": "sess_1"}
    mac.run_task.return_value = {"text": "done", "tool_calls": []}
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    agents_sdk.cmd_managed_agent_run("do the thing", api_key="sk-test",
                                     memory_store="notes")

    mac.create_memory_store.assert_called_once_with(name="notes")
    _, kwargs = mac.create_session.call_args
    assert kwargs["memory_store_id"] == "store_1"


def test_cmd_managed_agent_run_skips_store_when_not_named(agents_sdk, monkeypatch):
    mac = MagicMock()
    mac.create_agent.return_value = {"id": "agent_1"}
    mac.create_environment.return_value = {"id": "env_1"}
    mac.create_session.return_value = {"id": "sess_1"}
    mac.run_task.return_value = {"text": "done", "tool_calls": []}
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    agents_sdk.cmd_managed_agent_run("do the thing", api_key="sk-test")

    mac.create_memory_store.assert_not_called()
    _, kwargs = mac.create_session.call_args
    assert kwargs["memory_store_id"] is None


def test_cmd_agent_memory_store_create_standalone(agents_sdk, monkeypatch):
    mac = MagicMock()
    mac.create_memory_store.return_value = {"id": "store_9", "name": "shared"}
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    result = agents_sdk.cmd_agent_memory_store_create("shared", api_key="sk-test")

    mac.create_memory_store.assert_called_once_with(name="shared")
    assert result == {"id": "store_9", "name": "shared"}


# ── v1.20.0: Dreaming (research preview) ────────────────────────────────


def test_dreaming_beta_header_unchanged(agents_sdk):
    assert agents_sdk.DREAMING_BETA == "dreaming-2026-04-21"


def test_create_dream_sends_expected_inputs_and_betas(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    fake_dream = MagicMock(id="drm_1", status="pending")
    client.client.beta.dreams.create.return_value = fake_dream

    result = client.create_dream("store_1", session_ids=["sesn_1", "sesn_2"],
                                  model="claude-opus-4-8", instructions="focus on prefs")

    _, kwargs = client.client.beta.dreams.create.call_args
    assert kwargs["inputs"] == [
        {"type": "memory_store", "memory_store_id": "store_1"},
        {"type": "sessions", "session_ids": ["sesn_1", "sesn_2"]},
    ]
    assert kwargs["betas"] == [agents_sdk.MANAGED_AGENTS_BETA, agents_sdk.DREAMING_BETA]
    assert result == {"id": "drm_1", "status": "pending"}


def test_create_dream_without_sessions_omits_sessions_input(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.dreams.create.return_value = MagicMock(id="drm_2", status="pending")

    client.create_dream("store_1")

    _, kwargs = client.client.beta.dreams.create.call_args
    assert kwargs["inputs"] == [{"type": "memory_store", "memory_store_id": "store_1"}]


def test_get_dream_extracts_output_store_id(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    fake_output = MagicMock(type="memory_store", memory_store_id="store_curated")
    fake_dream = MagicMock(id="drm_1", status="completed", outputs=[fake_output], error=None)
    client.client.beta.dreams.retrieve.return_value = fake_dream

    result = client.get_dream("drm_1")

    assert result == {"id": "drm_1", "status": "completed",
                       "output_store_id": "store_curated", "error": None}


def test_get_dream_handles_no_outputs_yet(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    fake_dream = MagicMock(id="drm_1", status="pending", outputs=[], error=None)
    client.client.beta.dreams.retrieve.return_value = fake_dream

    result = client.get_dream("drm_1")

    assert result["output_store_id"] is None


def test_list_dreams_returns_id_and_status(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.dreams.list.return_value = [
        MagicMock(id="drm_1", status="completed"),
        MagicMock(id="drm_2", status="pending"),
    ]

    result = client.list_dreams()

    assert result == [{"id": "drm_1", "status": "completed"},
                       {"id": "drm_2", "status": "pending"}]


def test_cancel_dream(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.dreams.cancel.return_value = MagicMock(id="drm_1", status="canceled")

    result = client.cancel_dream("drm_1")

    assert result == {"id": "drm_1", "status": "canceled"}


def test_cmd_agent_dream_prints_and_returns(agents_sdk, monkeypatch, capsys):
    mac = MagicMock()
    mac.create_dream.return_value = {"id": "drm_1", "status": "pending"}
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    result = agents_sdk.cmd_agent_dream("store_1", api_key="sk-test")

    mac.create_dream.assert_called_once()
    assert result == {"id": "drm_1", "status": "pending"}
    assert "drm_1" in capsys.readouterr().out


def test_cmd_agent_dream_list_handles_empty(agents_sdk, monkeypatch, capsys):
    mac = MagicMock()
    mac.list_dreams.return_value = []
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    result = agents_sdk.cmd_agent_dream_list(api_key="sk-test")

    assert result == []
    assert "no dreams found" in capsys.readouterr().out


# ── v1.20.0: Outcomes (public beta) ─────────────────────────────────────


def test_define_outcome_sends_expected_event(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.sessions.events.send.return_value = {"ok": True}

    client.define_outcome("sess_1", "Build a DCF model", "## Rubric\n- has a price column",
                          max_iterations=5)

    _, kwargs = client.client.beta.sessions.events.send.call_args
    event = kwargs["events"][0]
    assert event["type"] == "user.define_outcome"
    assert event["description"] == "Build a DCF model"
    assert event["rubric"] == {"type": "text", "content": "## Rubric\n- has a price column"}
    assert event["max_iterations"] == 5
    assert kwargs["betas"] == [agents_sdk.MANAGED_AGENTS_BETA]


def test_define_outcome_default_max_iterations(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.sessions.events.send.return_value = {"ok": True}

    client.define_outcome("sess_1", "desc", "rubric text")

    _, kwargs = client.client.beta.sessions.events.send.call_args
    assert kwargs["events"][0]["max_iterations"] == 3


def test_cmd_managed_agent_run_with_outcome_calls_define_outcome_not_run_task(agents_sdk, monkeypatch):
    mac = MagicMock()
    mac.create_agent.return_value = {"id": "agent_1"}
    mac.create_environment.return_value = {"id": "env_1"}
    mac.create_memory_store.return_value = {"id": "store_1", "name": "notes"}
    mac.create_session.return_value = {"id": "sess_1"}
    mac.wait_for_outcome.return_value = {"text": "done", "result": "satisfied"}
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    result = agents_sdk.cmd_managed_agent_run(
        "unused task text", api_key="sk-test",
        outcome_description="Build a report", outcome_rubric="## has a table",
        outcome_max_iterations=7,
    )

    mac.define_outcome.assert_called_once_with(
        "sess_1", "Build a report",
        rubric_text="## has a table", rubric_file_id=None, max_iterations=7,
    )
    mac.run_task.assert_not_called()
    assert result == {"text": "done", "result": "satisfied"}


def test_cmd_managed_agent_run_without_outcome_calls_run_task(agents_sdk, monkeypatch):
    mac = MagicMock()
    mac.create_agent.return_value = {"id": "agent_1"}
    mac.create_environment.return_value = {"id": "env_1"}
    mac.create_session.return_value = {"id": "sess_1"}
    mac.run_task.return_value = {"text": "done", "tool_calls": []}
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    agents_sdk.cmd_managed_agent_run("plain task", api_key="sk-test")

    mac.define_outcome.assert_not_called()
    mac.run_task.assert_called_once_with("sess_1", "plain task")


# ── v1.20.0: Webhooks (public beta) ─────────────────────────────────────


def test_register_webhook_sends_expected_payload(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.webhooks.create.return_value = MagicMock(id="wh_1")

    result = client.register_webhook("https://example.com/hook", event_types=["session.status_idle"])

    _, kwargs = client.client.beta.webhooks.create.call_args
    assert kwargs["url"] == "https://example.com/hook"
    assert kwargs["event_types"] == ["session.status_idle"]
    assert kwargs["betas"] == [agents_sdk.MANAGED_AGENTS_BETA]
    assert result == {"id": "wh_1", "url": "https://example.com/hook",
                       "event_types": ["session.status_idle"]}


def test_register_webhook_defaults_event_types_to_none(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.webhooks.create.return_value = MagicMock(id="wh_2")

    client.register_webhook("https://example.com/hook")

    _, kwargs = client.client.beta.webhooks.create.call_args
    assert kwargs["event_types"] is None


def test_cmd_agent_webhook_register_prints_and_returns(agents_sdk, monkeypatch, capsys):
    mac = MagicMock()
    mac.register_webhook.return_value = {"id": "wh_1", "url": "https://x.test/h",
                                          "event_types": None}
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    result = agents_sdk.cmd_agent_webhook_register("https://x.test/h", api_key="sk-test")

    assert result["id"] == "wh_1"
    assert "wh_1" in capsys.readouterr().out


# ── v1.21.0: Vaults & credentials (public beta) ──────────────────────────


def test_create_vault_sends_expected_payload(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.vaults.create.return_value = MagicMock(id="vault_1")

    result = client.create_vault(display_name="Alice", external_user_id="usr_abc123")

    _, kwargs = client.client.beta.vaults.create.call_args
    assert kwargs["display_name"] == "Alice"
    assert kwargs["metadata"] == {"external_user_id": "usr_abc123"}
    assert kwargs["betas"] == [agents_sdk.MANAGED_AGENTS_BETA]
    assert result == {"id": "vault_1", "display_name": "Alice", "external_user_id": "usr_abc123"}


def test_create_vault_without_external_user_omits_metadata(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.vaults.create.return_value = MagicMock(id="vault_2")

    client.create_vault(display_name="Bob")

    _, kwargs = client.client.beta.vaults.create.call_args
    assert kwargs["metadata"] is None


def test_add_credential_static_bearer_requires_mcp_server_url(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    with pytest.raises(ValueError, match="mcp_server_url"):
        client.add_credential("vault_1", "static_bearer", secret_value="tok")


def test_add_credential_mcp_oauth_requires_mcp_server_url(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    with pytest.raises(ValueError, match="mcp_server_url"):
        client.add_credential("vault_1", "mcp_oauth", secret_value="tok")


def test_add_credential_static_bearer_sends_expected_payload(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.vaults.credentials.create.return_value = MagicMock(id="cred_1")

    result = client.add_credential(
        "vault_1", "static_bearer",
        mcp_server_url="https://api.githubcopilot.com/mcp/",
        secret_value="ghp_secrettoken",
    )

    _, kwargs = client.client.beta.vaults.credentials.create.call_args
    assert kwargs["vault_id"] == "vault_1"
    assert kwargs["mcp_server_url"] == "https://api.githubcopilot.com/mcp/"
    assert kwargs["auth"] == {"type": "static_bearer", "token": "ghp_secrettoken"}
    assert kwargs["betas"] == [agents_sdk.MANAGED_AGENTS_BETA]
    assert result["id"] == "cred_1"
    assert result["credential_type"] == "static_bearer"


def test_add_credential_environment_variable_requires_secret_name(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    with pytest.raises(ValueError, match="secret_name"):
        client.add_credential("vault_1", "environment_variable",
                              secret_value="key", allowed_domains=["api.notion.com"])


def test_add_credential_environment_variable_requires_allowed_domains(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    with pytest.raises(ValueError, match="allowed_domains"):
        client.add_credential("vault_1", "environment_variable",
                              secret_name="NOTION_API_KEY", secret_value="key")


def test_add_credential_environment_variable_sends_expected_payload(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.vaults.credentials.create.return_value = MagicMock(id="cred_2")

    result = client.add_credential(
        "vault_1", "environment_variable",
        secret_name="NOTION_API_KEY", secret_value="secret-key-value",
        allowed_domains=["api.notion.com"],
    )

    _, kwargs = client.client.beta.vaults.credentials.create.call_args
    assert kwargs["vault_id"] == "vault_1"
    assert kwargs["secret_name"] == "NOTION_API_KEY"
    assert kwargs["auth"] == {
        "type": "environment_variable", "secret_value": "secret-key-value",
        "allowed_domains": ["api.notion.com"],
        "injection_location": "headers",
    }
    assert result["secret_name"] == "NOTION_API_KEY"


def test_add_credential_rejects_unknown_type(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    with pytest.raises(ValueError, match="Unknown credential_type"):
        client.add_credential("vault_1", "totally_bogus", secret_value="x")


def test_add_credential_never_leaks_secret_in_exception_message(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    mock_value = "test-fake-credential-alpha"
    with pytest.raises(ValueError) as exc_info:
        client.add_credential("vault_1", "static_bearer", secret_value=mock_value)
    assert mock_value not in str(exc_info.value)


def test_add_credential_never_leaks_secret_to_stdout(agents_sdk, capsys):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.vaults.credentials.create.return_value = MagicMock(id="cred_3")
    mock_value = "test-fake-credential-beta"

    client.add_credential("vault_1", "static_bearer",
                          mcp_server_url="https://mcp.example.com", secret_value=mock_value)

    captured = capsys.readouterr()
    assert mock_value not in captured.out
    assert mock_value not in captured.err


def test_list_vaults_returns_id_and_display_name(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.vaults.list.return_value = [
        MagicMock(id="vault_1", display_name="Alice"),
        MagicMock(id="vault_2", display_name="Bob"),
    ]

    result = client.list_vaults()

    assert result == [{"id": "vault_1", "display_name": "Alice"},
                       {"id": "vault_2", "display_name": "Bob"}]


def test_archive_vault(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.vaults.archive.return_value = MagicMock(id="vault_1")

    result = client.archive_vault("vault_1")

    client.client.beta.vaults.archive.assert_called_once_with(
        "vault_1", betas=[agents_sdk.MANAGED_AGENTS_BETA])
    assert result == {"id": "vault_1", "archived": True}


def test_archive_credential(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.vaults.credentials.archive.return_value = MagicMock(id="cred_1")

    result = client.archive_credential("vault_1", "cred_1")

    client.client.beta.vaults.credentials.archive.assert_called_once_with(
        "vault_1", "cred_1", betas=[agents_sdk.MANAGED_AGENTS_BETA])
    assert result == {"id": "cred_1", "vault_id": "vault_1", "archived": True}


def test_create_session_with_vault_ids_passes_through(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.sessions.create.return_value = MagicMock(id="sess_3")

    result = client.create_session("agent_1", "env_1", title="t", vault_ids=["vault_1"])

    _, kwargs = client.client.beta.sessions.create.call_args
    assert kwargs["vault_ids"] == ["vault_1"]
    assert result["vault_ids"] == ["vault_1"]


def test_cmd_agent_vault_create_prints_and_returns(agents_sdk, monkeypatch, capsys):
    mac = MagicMock()
    mac.create_vault.return_value = {"id": "vault_1", "display_name": "Alice",
                                     "external_user_id": None}
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    result = agents_sdk.cmd_agent_vault_create("Alice", api_key="sk-test")

    assert result["id"] == "vault_1"
    assert "vault_1" in capsys.readouterr().out


def test_cmd_agent_vault_add_credential_never_prints_secret(agents_sdk, monkeypatch, capsys):
    mac = MagicMock()
    mock_value = "test-fake-credential-gamma"
    mac.add_credential.return_value = {"id": "cred_1", "vault_id": "vault_1",
                                       "credential_type": "static_bearer",
                                       "mcp_server_url": "https://mcp.example.com",
                                       "secret_name": None}
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    agents_sdk.cmd_agent_vault_add_credential(
        "vault_1", "static_bearer", api_key="sk-test",
        mcp_server_url="https://mcp.example.com", secret_value=mock_value,
    )

    assert mock_value not in capsys.readouterr().out


def test_cmd_agent_vault_list_handles_empty(agents_sdk, monkeypatch, capsys):
    mac = MagicMock()
    mac.list_vaults.return_value = []
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    result = agents_sdk.cmd_agent_vault_list(api_key="sk-test")

    assert result == []
    assert "no vaults found" in capsys.readouterr().out


def test_cmd_managed_agent_run_passes_vault_id_through(agents_sdk, monkeypatch):
    mac = MagicMock()
    mac.create_agent.return_value = {"id": "agent_1"}
    mac.create_environment.return_value = {"id": "env_1"}
    mac.create_session.return_value = {"id": "sess_1"}
    mac.run_task.return_value = {"text": "done", "tool_calls": []}
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    agents_sdk.cmd_managed_agent_run("task", api_key="sk-test", vault_id="vault_1")

    _, kwargs = mac.create_session.call_args
    assert kwargs["vault_ids"] == ["vault_1"]


def test_cmd_managed_agent_run_without_vault_id_passes_none(agents_sdk, monkeypatch):
    mac = MagicMock()
    mac.create_agent.return_value = {"id": "agent_1"}
    mac.create_environment.return_value = {"id": "env_1"}
    mac.create_session.return_value = {"id": "sess_1"}
    mac.run_task.return_value = {"text": "done", "tool_calls": []}
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    agents_sdk.cmd_managed_agent_run("task", api_key="sk-test")

    _, kwargs = mac.create_session.call_args
    assert kwargs["vault_ids"] is None


# ── v1.21.0: Scheduled deployments (public beta) ─────────────────────────


def test_create_scheduled_deployment_sends_expected_payload(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.deployments.create.return_value = MagicMock(id="dep_1", status="active")

    result = client.create_scheduled_deployment(
        "agent_1", "env_1", "0 9 * * 1", timezone="America/New_York",
        task="Summarize last week's failed CI runs",
    )

    _, kwargs = client.client.beta.deployments.create.call_args
    assert kwargs["agent"] == "agent_1"
    assert kwargs["environment_id"] == "env_1"
    assert kwargs["schedule"] == {"type": "cron", "expression": "0 9 * * 1",
                                  "timezone": "America/New_York"}
    assert kwargs["initial_events"] == [{
        "type": "user.message",
        "content": [{"type": "text", "text": "Summarize last week's failed CI runs"}],
    }]
    assert kwargs["betas"] == [agents_sdk.MANAGED_AGENTS_BETA]
    assert result["id"] == "dep_1"
    assert result["status"] == "active"


def test_create_scheduled_deployment_defaults_timezone_to_utc(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.deployments.create.return_value = MagicMock(id="dep_2", status="active")

    client.create_scheduled_deployment("agent_1", "env_1", "0 9 * * 1", task="t")

    _, kwargs = client.client.beta.deployments.create.call_args
    assert kwargs["schedule"]["timezone"] == "UTC"


def test_list_scheduled_deployments(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.deployments.list.return_value = [
        MagicMock(id="dep_1", status="active"),
        MagicMock(id="dep_2", status="archived"),
    ]

    result = client.list_scheduled_deployments()

    assert result == [{"id": "dep_1", "status": "active"},
                       {"id": "dep_2", "status": "archived"}]


def test_get_scheduled_deployment(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.deployments.retrieve.return_value = MagicMock(
        id="dep_1", status="active", schedule={"type": "cron", "expression": "0 9 * * 1"})

    result = client.get_scheduled_deployment("dep_1")

    assert result["id"] == "dep_1"
    assert result["status"] == "active"
    assert result["schedule"] == {"type": "cron", "expression": "0 9 * * 1"}


def test_cancel_scheduled_deployment(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.deployments.archive.return_value = MagicMock(id="dep_1", status="archived")

    result = client.cancel_scheduled_deployment("dep_1")

    client.client.beta.deployments.archive.assert_called_once_with(
        "dep_1", betas=[agents_sdk.MANAGED_AGENTS_BETA])
    assert result == {"id": "dep_1", "status": "archived"}


def test_cmd_agent_schedule_create_prints_and_returns(agents_sdk, monkeypatch, capsys):
    mac = MagicMock()
    mac.create_scheduled_deployment.return_value = {
        "id": "dep_1", "agent_id": "agent_1", "environment_id": "env_1",
        "cron_expression": "0 9 * * 1", "timezone": "UTC", "status": "active",
    }
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    result = agents_sdk.cmd_agent_schedule_create(
        "agent_1", "env_1", "0 9 * * 1", api_key="sk-test")

    assert result["id"] == "dep_1"
    assert "dep_1" in capsys.readouterr().out


def test_cmd_agent_schedule_list_handles_empty(agents_sdk, monkeypatch, capsys):
    mac = MagicMock()
    mac.list_scheduled_deployments.return_value = []
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    result = agents_sdk.cmd_agent_schedule_list(api_key="sk-test")

    assert result == []
    assert "no scheduled deployments found" in capsys.readouterr().out


def test_cmd_agent_schedule_cancel(agents_sdk, monkeypatch, capsys):
    mac = MagicMock()
    mac.cancel_scheduled_deployment.return_value = {"id": "dep_1", "status": "archived"}
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    result = agents_sdk.cmd_agent_schedule_cancel("dep_1", api_key="sk-test")

    assert result["status"] == "archived"
    assert "dep_1" in capsys.readouterr().out


# ── v1.21.0: Native Multiagent orchestration ─────────────────────────────


def test_build_multiagent_config_expands_string_ids(agents_sdk):
    result = agents_sdk.build_multiagent_config(["agent_1", "agent_2"])

    assert result == {
        "type": "coordinator",
        "agents": [{"type": "agent", "id": "agent_1"}, {"type": "agent", "id": "agent_2"}],
    }


def test_build_multiagent_config_passes_through_dicts(agents_sdk):
    result = agents_sdk.build_multiagent_config([{"type": "self"}, "agent_1"])

    assert result["agents"][0] == {"type": "self"}
    assert result["agents"][1] == {"type": "agent", "id": "agent_1"}


def test_build_multiagent_config_rejects_over_20(agents_sdk):
    with pytest.raises(ValueError, match="at most 20"):
        agents_sdk.build_multiagent_config([f"agent_{i}" for i in range(21)])


def test_build_multiagent_config_allows_exactly_20(agents_sdk):
    result = agents_sdk.build_multiagent_config([f"agent_{i}" for i in range(20)])
    assert len(result["agents"]) == 20


def test_create_agent_passes_multiagent_through_when_given(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.agents.create.return_value = MagicMock(id="agent_coord")
    multiagent = agents_sdk.build_multiagent_config(["agent_1", "agent_2"])

    client.create_agent("coordinator", multiagent=multiagent)

    _, kwargs = client.client.beta.agents.create.call_args
    assert kwargs["multiagent"] == multiagent


def test_create_agent_omits_multiagent_when_not_given(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.agents.create.return_value = MagicMock(id="agent_1")

    client.create_agent("plain-agent")

    _, kwargs = client.client.beta.agents.create.call_args
    assert "multiagent" not in kwargs


def test_review_specialist_presets_cover_documented_specialists(agents_sdk):
    assert set(agents_sdk.REVIEW_SPECIALIST_PRESETS) == {"security", "style", "test-coverage"}


def test_cmd_agent_review_multiagent_creates_specialists_and_coordinator(agents_sdk, monkeypatch):
    mac = MagicMock()
    mac.create_agent.side_effect = [
        {"id": "agent_security"}, {"id": "agent_style"}, {"id": "agent_coordinator"},
    ]
    mac.create_environment.return_value = {"id": "env_1"}
    mac.create_session.return_value = {"id": "sess_1"}
    mac.run_task.return_value = {"text": "combined report", "tool_calls": []}
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    result = agents_sdk.cmd_agent_review_multiagent(
        "/repo/checkout", ["security", "style"], api_key="sk-test")

    assert mac.create_agent.call_count == 3
    coordinator_kwargs = mac.create_agent.call_args_list[-1].kwargs
    assert coordinator_kwargs["multiagent"] == {
        "type": "coordinator",
        "agents": [{"type": "agent", "id": "agent_security"},
                   {"type": "agent", "id": "agent_style"}],
    }
    mac.create_session.assert_called_once()
    assert result == {"text": "combined report", "tool_calls": []}


def test_cmd_agent_review_multiagent_rejects_unknown_specialist(agents_sdk, monkeypatch):
    mac = MagicMock()
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    with pytest.raises(ValueError, match="Unknown specialist"):
        agents_sdk.cmd_agent_review_multiagent("/repo", ["not-a-real-specialist"], api_key="sk-test")

    mac.create_agent.assert_not_called()


# ── v1.21.0: Outcomes file_id rubric form ────────────────────────────────


def test_define_outcome_with_rubric_text_unchanged(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.sessions.events.send.return_value = {"ok": True}

    client.define_outcome("sess_1", "Build a DCF model", rubric_text="## has a price column",
                          max_iterations=5)

    _, kwargs = client.client.beta.sessions.events.send.call_args
    event = kwargs["events"][0]
    assert event["rubric"] == {"type": "text", "content": "## has a price column"}
    assert kwargs["betas"] == [agents_sdk.MANAGED_AGENTS_BETA]


def test_define_outcome_with_rubric_file_id(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.sessions.events.send.return_value = {"ok": True}

    client.define_outcome("sess_1", "Build a DCF model", rubric_file_id="file_01abc",
                          max_iterations=5)

    _, kwargs = client.client.beta.sessions.events.send.call_args
    event = kwargs["events"][0]
    assert event["rubric"] == {"type": "file", "file_id": "file_01abc"}
    assert kwargs["betas"] == [agents_sdk.MANAGED_AGENTS_BETA, agents_sdk.FILES_API_BETA]


def test_define_outcome_rejects_both_rubric_text_and_file_id(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    with pytest.raises(ValueError, match="exactly one"):
        client.define_outcome("sess_1", "desc", rubric_text="text", rubric_file_id="file_1")


def test_define_outcome_rejects_neither_rubric_text_nor_file_id(agents_sdk):
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    with pytest.raises(ValueError, match="exactly one"):
        client.define_outcome("sess_1", "desc")


def test_cmd_managed_agent_run_with_rubric_file_id(agents_sdk, monkeypatch):
    mac = MagicMock()
    mac.create_agent.return_value = {"id": "agent_1"}
    mac.create_environment.return_value = {"id": "env_1"}
    mac.create_session.return_value = {"id": "sess_1"}
    mac.wait_for_outcome.return_value = {"text": "done", "result": "satisfied"}
    monkeypatch.setattr(agents_sdk, "ManagedAgentsClient", lambda api_key: mac)

    agents_sdk.cmd_managed_agent_run(
        "unused", api_key="sk-test",
        outcome_description="Build a report", outcome_rubric_file_id="file_01abc",
    )

    mac.define_outcome.assert_called_once_with(
        "sess_1", "Build a report",
        rubric_text=None, rubric_file_id="file_01abc", max_iterations=3,
    )
    mac.run_task.assert_not_called()


def test_cmd_agent_outcome_rubric_upload(agents_sdk, monkeypatch, capsys, tmp_path):
    rubric_file = tmp_path / "rubric.md"
    rubric_file.write_text("## Rubric\n- has a table")

    fake_files_module = types.ModuleType("claude_files")
    fake_files_api = MagicMock()
    fake_files_api.upload.return_value = {"id": "file_01abc", "filename": "rubric.md"}
    fake_files_module.FilesAPI = MagicMock(return_value=fake_files_api)
    monkeypatch.setitem(sys.modules, "claude_files", fake_files_module)

    result = agents_sdk.cmd_agent_outcome_rubric_upload(
        str(rubric_file), api_key="sk-test", model="claude-sonnet-5")

    assert result == "file_01abc"
    assert "file_01abc" in capsys.readouterr().out


# ── v1.22.0: Session-Level Agent Overrides ───────────────────────────────


def test_create_session_without_override_uses_default_agent(agents_sdk):
    """Finding 1: When agent_id_override is not given, the default agent_id
    is used — no regression to pre-v1.22.0 behavior."""
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.sessions.create.return_value = MagicMock(id="sess_1")

    result = client.create_session("agent_v1", "env_01")

    _, kwargs = client.client.beta.sessions.create.call_args
    assert kwargs["agent"] == "agent_v1"
    assert result["agent_id"] == "agent_v1"
    assert result["agent_id_override"] is None


def test_create_session_with_override_uses_override_agent(agents_sdk):
    """Finding 1: When agent_id_override is given, it overrides the agent
    field in the session creation payload."""
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.sessions.create.return_value = MagicMock(id="sess_2")

    result = client.create_session("agent_v1", "env_01",
                                    agent_id_override="agent_fable5_premium")

    _, kwargs = client.client.beta.sessions.create.call_args
    assert kwargs["agent"] == "agent_fable5_premium"
    assert result["agent_id"] == "agent_v1"
    assert result["agent_id_override"] == "agent_fable5_premium"


# ── v1.22.0: Credential Injection Location ───────────────────────────────


def test_add_credential_env_var_default_injection_location(agents_sdk):
    """Finding 2: Default injection_location is 'headers' for backward
    compatibility."""
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.vaults.credentials.create.return_value = MagicMock(id="cred_1")

    result = client.add_credential(
        "vault_1", "environment_variable",
        secret_name="DB_PASSWORD", secret_value="super-secret",
        allowed_domains=["db.example.com"],
    )

    _, kwargs = client.client.beta.vaults.credentials.create.call_args
    assert kwargs["auth"]["injection_location"] == "headers"
    assert result["injection_location"] == "headers"


def test_add_credential_env_var_custom_injection_location(agents_sdk):
    """Finding 2: injection_location can be set to 'body' or 'both'."""
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.vaults.credentials.create.return_value = MagicMock(id="cred_2")

    result = client.add_credential(
        "vault_1", "environment_variable",
        secret_name="API_KEY", secret_value="token123",
        allowed_domains=["api.example.com"],
        injection_location="body",
    )

    _, kwargs = client.client.beta.vaults.credentials.create.call_args
    assert kwargs["auth"]["injection_location"] == "body"
    assert result["injection_location"] == "body"


def test_add_credential_env_var_invalid_injection_location(agents_sdk):
    """Finding 2: Invalid injection_location raises ValueError."""
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    with pytest.raises(ValueError, match="Invalid injection_location"):
        client.add_credential(
            "vault_1", "environment_variable",
            secret_name="BAD", secret_value="val",
            allowed_domains=["x.com"],
            injection_location="query_params",
        )


def test_add_credential_non_env_var_injection_location_is_none(agents_sdk):
    """Finding 2: injection_location is None for non-environment_variable
    credential types."""
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.vaults.credentials.create.return_value = MagicMock(id="cred_3")

    result = client.add_credential(
        "vault_1", "static_bearer",
        mcp_server_url="https://mcp.example.com", secret_value="tok",
    )

    assert result["injection_location"] is None


# ── v1.22.0: Streamed Event Deltas ────────────────────────────────────────


class FakeEventDelta:
    """Simulate an event_delta stream event with a delta text fragment."""
    type = "event_delta"

    def __init__(self, delta_text: str):
        self.delta = delta_text


class FakeAgentMessage:
    """Simulate an agent.message event with content blocks."""
    type = "agent.message"

    def __init__(self, text: str):
        self.content = [MagicMock(text=text)]


class FakeAgentToolUse:
    type = "agent.tool_use"

    def __init__(self, name: str):
        self.name = name


class FakeStatusIdle:
    type = "session.status_idle"


def test_run_task_accumulates_delta_events(agents_sdk):
    """Finding 3: event_delta fragments are accumulated and returned in
    the 'deltas' field."""
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    stream_events = [
        FakeEventDelta("Hello "),
        FakeEventDelta("World!"),
        FakeAgentMessage("Hello World!"),
        FakeStatusIdle(),
    ]
    client.client.beta.sessions.events.stream.return_value.__enter__.return_value = stream_events
    client.client.beta.sessions.events.send.return_value = None

    result = client.run_task("sess_1", "task")

    assert result["deltas"] == "Hello World!"
    assert result["text"] == "Hello World!"


def test_run_task_no_deltas_returns_none(agents_sdk):
    """Finding 3: When no event_delta events occur, deltas is None."""
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    stream_events = [
        FakeAgentMessage("Direct result"),
        FakeStatusIdle(),
    ]
    client.client.beta.sessions.events.stream.return_value.__enter__.return_value = stream_events
    client.client.beta.sessions.events.send.return_value = None

    result = client.run_task("sess_1", "task")

    assert result["deltas"] is None
    assert result["text"] == "Direct result"


# ── v1.22.0: Code Execution Version Bump ──────────────────────────────────


def test_code_execution_tool_uses_ga_version(agents_sdk):
    """Finding 4: The code_execution tool type and beta header use the
    GA version (20260120) instead of the legacy preview version."""
    import claude_code_exec
    assert claude_code_exec.CODE_EXEC_TOOL["type"] == "code_execution_20260120"
    assert claude_code_exec.BETA_HEADER == "code-execution-2026-01-20"


# ── 2026-07-09 research: Deployment runs ─────────────────────────────────


def test_list_deployment_runs_sends_filter_params(agents_sdk):
    """Deployment runs list supports deployment_id and has_error filters."""
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    run_mock = MagicMock(id="run_1", deployment_id="dep_1", status="completed",
                         created_at="2026-07-09T10:00:00Z", has_error=False,
                         trigger_type="schedule")
    client.client.beta.deployment_runs.list.return_value = [run_mock]

    result = client.list_deployment_runs(deployment_id="dep_1", has_error=False)

    _, kwargs = client.client.beta.deployment_runs.list.call_args
    assert kwargs["deployment_id"] == "dep_1"
    assert kwargs["has_error"] is False
    assert kwargs["betas"] == [agents_sdk.MANAGED_AGENTS_BETA]
    assert len(result) == 1
    assert result[0]["id"] == "run_1"
    assert result[0]["deployment_id"] == "dep_1"
    assert result[0]["status"] == "completed"


def test_list_deployment_runs_without_filters(agents_sdk):
    """Deployment runs list omits optional params when not provided."""
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.deployment_runs.list.return_value = []

    result = client.list_deployment_runs()

    _, kwargs = client.client.beta.deployment_runs.list.call_args
    assert "deployment_id" not in kwargs
    assert "has_error" not in kwargs
    assert result == []


def test_get_deployment_run(agents_sdk):
    """Single deployment run retrieval returns structured dict."""
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    client.client.beta.deployment_runs.retrieve.return_value = MagicMock(
        id="run_2", deployment_id="dep_1", status="failed",
        created_at="2026-07-09T12:00:00Z", has_error=True,
        trigger_type="manual")

    result = client.get_deployment_run("run_2")

    client.client.beta.deployment_runs.retrieve.assert_called_once_with(
        "run_2", betas=[agents_sdk.MANAGED_AGENTS_BETA])
    assert result["id"] == "run_2"
    assert result["has_error"] is True
    assert result["trigger_type"] == "manual"


# ── 2026-07-09 research: User profiles CRUD ──────────────────────────────


def test_create_user_profile_sends_expected_payload(agents_sdk):
    """User profile creation sends name, external_id, relationship, and beta."""
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    profile_mock = MagicMock()
    profile_mock.id = "up_1"
    profile_mock.name = "Acme Corp"
    profile_mock.external_id = "acme-123"
    client.client.beta.user_profiles.create.return_value = profile_mock

    result = client.create_user_profile(
        name="Acme Corp", external_id="acme-123", relationship="external")

    _, kwargs = client.client.beta.user_profiles.create.call_args
    assert kwargs["name"] == "Acme Corp"
    assert kwargs["external_id"] == "acme-123"
    assert kwargs["relationship"] == "external"
    assert kwargs["betas"] == ["user-profiles"]
    assert result["id"] == "up_1"
    assert result["name"] == "Acme Corp"


def test_list_user_profiles(agents_sdk):
    """User profile list returns structured dicts."""
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    p1 = MagicMock()
    p1.id = "up_1"
    p1.name = "Acme"
    p1.external_id = "a-1"
    p2 = MagicMock()
    p2.id = "up_2"
    p2.name = "Beta Inc"
    p2.external_id = "b-2"
    client.client.beta.user_profiles.list.return_value = [p1, p2]

    result = client.list_user_profiles(limit=10)

    _, kwargs = client.client.beta.user_profiles.list.call_args
    assert kwargs["limit"] == 10
    assert kwargs["betas"] == ["user-profiles"]
    assert len(result) == 2
    assert result[0]["id"] == "up_1"
    assert result[1]["name"] == "Beta Inc"


def test_get_user_profile(agents_sdk):
    """Single user profile retrieval includes relationship and metadata."""
    client = agents_sdk.ManagedAgentsClient(api_key="sk-test")
    profile_mock = MagicMock()
    profile_mock.id = "up_1"
    profile_mock.name = "Acme"
    profile_mock.external_id = "a-1"
    profile_mock.relationship = "external"
    profile_mock.metadata = {"tier": "enterprise"}
    client.client.beta.user_profiles.retrieve.return_value = profile_mock

    result = client.get_user_profile("up_1")

    client.client.beta.user_profiles.retrieve.assert_called_once_with(
        "up_1", betas=["user-profiles"])
    assert result["id"] == "up_1"
    assert result["relationship"] == "external"
    assert result["metadata"] == {"tier": "enterprise"}


# ── 2026-07-09 research: Effort xhigh, display omitted, tool versions ────


def test_effort_xhigh_maps_to_24000_budget():
    """xhigh effort level maps to 24000 thinking tokens."""
    from claude_thinking import EFFORT_BUDGETS
    assert EFFORT_BUDGETS["xhigh"] == 24_000


def test_thinking_display_omitted_in_generate():
    """display='omitted' is included in thinking config."""
    from claude_thinking import ThinkingCoder
    from unittest.mock import patch, MagicMock

    tc = ThinkingCoder(api_key="sk-test", model="claude-opus-4-8")
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(type="text", text="answer")]
    mock_resp.usage = MagicMock()
    mock_resp.usage.model_dump.return_value = {"input_tokens": 10, "output_tokens": 5}

    with patch.object(tc.client.messages, "create", return_value=mock_resp) as mock_create:
        tc.generate_with_thinking("hello", display="omitted")
        _, kwargs = mock_create.call_args
        assert kwargs["thinking"]["display"] == "omitted"


def test_thinking_display_none_omits_field():
    """display=None does not add display to thinking config."""
    from claude_thinking import ThinkingCoder
    from unittest.mock import patch, MagicMock

    tc = ThinkingCoder(api_key="sk-test", model="claude-opus-4-8")
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(type="text", text="answer")]
    mock_resp.usage = MagicMock()
    mock_resp.usage.model_dump.return_value = {}

    with patch.object(tc.client.messages, "create", return_value=mock_resp) as mock_create:
        tc.generate_with_thinking("hello")
        _, kwargs = mock_create.call_args
        assert "display" not in kwargs["thinking"]


def test_web_search_tool_uses_20260318():
    """web_search tool type is the latest 20260318 version."""
    from claude_search import WEB_SEARCH_TOOL
    from claude_tools import SERVER_TOOLS
    assert WEB_SEARCH_TOOL["type"] == "web_search_20260318"
    assert SERVER_TOOLS["web_search"]["type"] == "web_search_20260318"


def test_web_fetch_tool_uses_20260318():
    """web_fetch tool type is the latest 20260318 version."""
    from claude_search import WEB_FETCH_TOOL
    from claude_tools import SERVER_TOOLS
    assert WEB_FETCH_TOOL["type"] == "web_fetch_20260318"
    assert SERVER_TOOLS["web_fetch"]["type"] == "web_fetch_20260318"


def test_build_web_search_tool_with_response_inclusion():
    """build_web_search_tool adds response_inclusion when specified."""
    from claude_tools import build_web_search_tool
    t = build_web_search_tool(response_inclusion="excluded")
    assert t["response_inclusion"] == "excluded"
    assert t["type"] == "web_search_20260318"

    # None should not add the field
    t2 = build_web_search_tool()
    assert "response_inclusion" not in t2


def test_build_web_fetch_tool_with_use_cache():
    """build_web_fetch_tool adds use_cache when specified."""
    from claude_tools import build_web_fetch_tool
    t = build_web_fetch_tool(use_cache=False)
    assert t["use_cache"] is False
    assert t["type"] == "web_fetch_20260318"

    # None should not add the field
    t2 = build_web_fetch_tool()
    assert "use_cache" not in t2


def test_embeddings_default_model_is_voyage_4():
    """Embeddings default model updated from voyage-3.5 to voyage-4."""
    from claude_embeddings import DEFAULT_MODEL
    assert DEFAULT_MODEL == "voyage-4"


def test_mythos_preview_in_model_catalog():
    """claude-mythos-preview is in the model catalog."""
    from claude_models import MODEL_CATALOG
    assert "claude-mythos-preview" in MODEL_CATALOG
    entry = MODEL_CATALOG["claude-mythos-preview"]
    assert entry["tier"] == "mythos"
    assert entry["thinking"] == "adaptive"


def test_opus_41_upcoming_retirement():
    """Opus 4.1 has upcoming retirement flag."""
    from claude_models import check_retired
    r = check_retired("claude-opus-4-1-20250514")
    assert r is not None
    assert r["upcoming"] is True
    assert r["retired"] == "2026-08-05"
    assert r["replacement"] == "claude-opus-4-8"
