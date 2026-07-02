"""
claude_agents.py — Claude Agent SDK / Managed Agents
AI Model Coder CLI v1.8.0

Implements the Claude Agent SDK patterns:
  • Stateful sessions with persistent event history
  • Subagent spawning and orchestration
  • MCP server connections (stdio / SSE / HTTP)
  • MCP tunnels (research preview) — expose a local-only MCP server via a
    public Anthropic-routed URL, so it can be wired up as an mcp_servers
    entry without deploying it publicly first. See McpTunnel.
  • Tool search and on-demand tool loading
  • Session resume
  • Permission modes
  • Claude Managed Agents (beta) via API

CLI flags:
  --agent-session ID       Resume or create a named session
  --agent-mcp URL          Connect an MCP server
  --agent-mcp-stdio CMD    Connect stdio MCP server
  --agent-mcp-tunnel PORT  Open an MCP tunnel to a local MCP server on PORT
                           and print its public URL (research preview)
  --agent-tools TOOLS      Comma-separated tool preset
  --agent-permission MODE  acceptEdits | askPermission | supervised
  --agent-subagent PROMPT  Spawn a subagent for a sub-task
  --agent-list-sessions    List saved sessions
  --agent-resume ID        Resume a session
"""

import os
import json
import uuid
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


SESSIONS_DIR = Path(os.path.expanduser("~/.ai-coder/agent_sessions"))
ENDPOINT     = "https://api.anthropic.com/v1/messages"


# ── Permission modes ───────────────────────────────────────────────────────

class PermissionMode:
    ACCEPT_EDITS   = "acceptEdits"      # auto-approve all tool calls
    ASK_PERMISSION = "askPermission"    # ask user for each tool call
    SUPERVISED     = "supervised"       # auto-approve reads, ask for writes


# ── Tool presets ───────────────────────────────────────────────────────────

TOOL_PRESETS = {
    "all":          ["bash", "text_editor", "web_search", "code_execution"],
    "code":         ["bash", "text_editor", "code_execution"],
    "web":          ["web_search", "web_fetch"],
    "readonly":     ["web_search", "web_fetch", "code_execution"],
    "filesystem":   ["bash", "text_editor"],
}


# ── AgentSession ──────────────────────────────────────────────────────────

class AgentSession:
    """Persistent session with message history and tool state."""

    def __init__(self, session_id: str = None, name: str = "",
                 permission_mode: str = PermissionMode.ASK_PERMISSION):
        self.id              = session_id or str(uuid.uuid4())[:12]
        self.name            = name or f"session-{self.id}"
        self.permission_mode = permission_mode
        self.history: list   = []
        self.mcp_servers: list = []
        self.created_at      = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.updated_at      = self.created_at
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls, session_id: str) -> "AgentSession":
        p = SESSIONS_DIR / f"{session_id}.json"
        if not p.exists():
            raise FileNotFoundError(f"Session {session_id} not found.")
        data = json.loads(p.read_text())
        s = cls.__new__(cls)
        s.__dict__.update(data)
        return s

    def save(self):
        self.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        p = SESSIONS_DIR / f"{self.id}.json"
        p.write_text(json.dumps(self.__dict__, indent=2))

    def add_turn(self, role: str, content: str):
        self.history.append({"role": role, "content": content,
                              "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ")})

    def messages(self) -> list[dict]:
        return [{"role": t["role"], "content": t["content"]} for t in self.history]


# ── MCP connector config ───────────────────────────────────────────────────

class McpServerConfig:
    def __init__(self, type: str, name: str, **kwargs):
        self.type = type
        self.name = name
        self.extra = kwargs

    def to_dict(self) -> dict:
        return {"type": self.type, "name": self.name, **self.extra}

    @classmethod
    def stdio(cls, name: str, command: str, args: list = None) -> "McpServerConfig":
        return cls("stdio", name, command=command, args=args or [])

    @classmethod
    def sse(cls, name: str, url: str, headers: dict = None) -> "McpServerConfig":
        return cls("sse", name, url=url, headers=headers or {})

    @classmethod
    def http(cls, name: str, url: str, headers: dict = None) -> "McpServerConfig":
        return cls("http", name, url=url, headers=headers or {})


# ── MCP tunnels (research preview) ─────────────────────────────────────────
# New surface (checked platform.claude.com/docs, 2026-07-02) for exposing a
# local MCP server — one only reachable on your machine/private network —
# to the Claude API without deploying it publicly first. Distinct from
# McpServerConfig above, which connects to an MCP server that's already
# reachable at a URL (sse/http) or spawnable as a local subprocess (stdio):
# a tunnel is what makes a *local* server reachable in the first place, so
# you can then hand its public tunnel URL to McpServerConfig.sse/http.
# Moved off the Admin API onto its own /v1/tunnels surface in the last
# couple of months per the release notes; research preview, so this can
# still change shape — re-verify before depending on it for anything but
# local dev/testing.
MCP_TUNNELS_BETA = "mcp-tunnels-2026-06-22"
TUNNELS_ENDPOINT = "https://api.anthropic.com/v1/tunnels"


class McpTunnel:
    """Client for the MCP tunnels research preview. Opens a public,
    Anthropic-routed URL that forwards to a local MCP server, so a server
    only reachable on localhost/your private network can still be handed to
    McpServerConfig.sse()/http() as an mcp_servers entry in a Messages API
    request. Local-only MCP dev servers, or servers behind a firewall that
    you don't want to expose directly, are the intended use case."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.tunnel_id: Optional[str] = None
        self.public_url: Optional[str] = None

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": MCP_TUNNELS_BETA,
        }

    def open(self, local_port: int, name: Optional[str] = None) -> dict:
        """Open a tunnel to a local MCP server listening on local_port.
        Returns the API response, which includes the tunnel id and the
        public URL to hand to McpServerConfig.sse()/http()."""
        payload = {"local_port": local_port}
        if name:
            payload["name"] = name
        req = urllib.request.Request(
            TUNNELS_ENDPOINT, data=json.dumps(payload).encode(),
            headers=self._headers(), method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.read().decode(), "status": e.code}
        except Exception as e:
            return {"error": str(e)}
        self.tunnel_id = data.get("id")
        self.public_url = data.get("url")
        return data

    def close(self) -> dict:
        """Close a previously opened tunnel."""
        if not self.tunnel_id:
            return {"error": "No open tunnel to close"}
        req = urllib.request.Request(
            f"{TUNNELS_ENDPOINT}/{self.tunnel_id}",
            headers=self._headers(), method="DELETE",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return {"status": r.status}
        except urllib.error.HTTPError as e:
            return {"error": e.read().decode(), "status": e.code}
        except Exception as e:
            return {"error": str(e)}

    def as_mcp_server(self, name: str, transport: str = "sse") -> McpServerConfig:
        """Build an McpServerConfig pointing at this tunnel's public URL,
        once open() has succeeded. transport is "sse" or "http" — whichever
        the local MCP server actually speaks."""
        if not self.public_url:
            raise RuntimeError("Tunnel not open yet — call open() first")
        return McpServerConfig(transport, name, url=self.public_url)


def cmd_mcp_tunnel_open(api_key: str, local_port: int, name: Optional[str] = None):
    """CLI entry: open a tunnel and print the public URL."""
    tunnel = McpTunnel(api_key)
    result = tunnel.open(local_port, name=name)
    if result.get("error"):
        print(f"\033[91m✗ Failed to open tunnel: {result['error']}\033[0m")
        return result
    print(f"\033[92m✓ Tunnel open: {tunnel.public_url}  (id={tunnel.tunnel_id})\033[0m")
    print(f"  Forwarding to local port {local_port}. Use this URL with "
          f"McpServerConfig.sse()/http() as an mcp_servers entry.")
    return result


# ── ManagedAgent ──────────────────────────────────────────────────────────
# NOTE: despite the name, this class does NOT call Anthropic's Claude
# Managed Agents API (/v1/agents, /v1/environments, /v1/sessions). It's a
# local agent loop built on the plain synchronous Messages API — an "agent"
# system prompt plus this module's own AgentSession for history/persistence.
# That's why _post() never sends the managed-agents-2026-04-01 beta header:
# there was nothing to attach it to, since ENDPOINT is /v1/messages, not a
# Managed Agents endpoint. For the actual hosted Managed Agents product
# (server-run sandbox, session persistence, SSE event streaming, webhooks),
# see ManagedAgentsClient below, which does call those endpoints and does
# send the beta header. Kept this class as-is (renaming would break
# cmd_agent_chat/cmd_agent_orchestrate call sites) but be aware it's really
# a lightweight local alternative, not a wrapper around the real product.

class ManagedAgent:
    """
    Claude Managed Agents via the Messages API.
    Uses agentic tool loops with session persistence.
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-5",
                 max_tokens: int = 8192, system_prompt: str = None):
        self.api_key     = api_key
        self.model       = model
        self.max_tokens  = max_tokens
        self.system      = system_prompt or (
            "You are an expert software agent. You have access to tools for "
            "reading files, running code, and searching the web. "
            "Complete tasks step-by-step, using tools as needed. "
            "Always verify your work before finishing."
        )

    def _post(self, payload: dict, beta: str = "") -> dict:
        headers = {
            "Content-Type":      "application/json",
            "x-api-key":         self.api_key,
            "anthropic-version": "2023-06-01",
        }
        if beta:
            headers["anthropic-beta"] = beta
        req = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.read().decode(), "status": e.code}
        except Exception as e:
            return {"error": str(e)}

    # ── Simple session-aware call ──────────────────────────────────────────

    def chat(self, prompt: str, session: AgentSession,
             tools: list[dict] = None) -> str:
        """Add a turn to the session and get a response."""
        session.add_turn("user", prompt)

        payload: dict = {
            "model":      self.model,
            "max_tokens": self.max_tokens,
            "system":     self.system,
            "messages":   session.messages(),
        }
        if tools:
            payload["tools"] = tools

        data = self._post(payload)
        if "error" in data:
            return f"[ERROR] {data['error']}"

        resp = "".join(
            b.get("text", "") for b in data.get("content", [])
            if b.get("type") == "text"
        )
        session.add_turn("assistant", resp)
        session.save()
        return resp

    # ── Subagent spawner ──────────────────────────────────────────────────

    def spawn_subagent(self, task: str, context: str = "",
                       tools: list[dict] = None) -> str:
        """
        Spawn a focused subagent for a specific sub-task.
        Returns the subagent's result as a string.
        """
        sub_system = (
            "You are a focused subagent. Complete ONLY the specific task given. "
            "Be thorough but concise. Return just the result, no preamble."
        )
        prompt = f"Context: {context}\n\nTask: {task}" if context else task
        payload: dict = {
            "model":      self.model,
            "max_tokens": self.max_tokens,
            "system":     sub_system,
            "messages":   [{"role": "user", "content": prompt}],
        }
        if tools:
            payload["tools"] = tools

        data = self._post(payload)
        if "error" in data:
            return f"[SUBAGENT ERROR] {data['error']}"
        return "".join(
            b.get("text", "") for b in data.get("content", [])
            if b.get("type") == "text"
        )

    # ── Orchestrator ──────────────────────────────────────────────────────

    def orchestrate(self, goal: str, session: AgentSession,
                    max_steps: int = 8) -> dict:
        """
        High-level orchestrator: decompose goal into steps, run subagents,
        synthesise results.
        """
        # Step 1: Decompose
        print(f"\033[94mℹ Orchestrating: {goal[:60]}\033[0m")
        decomp_prompt = (
            f"Break this goal into 3-7 concrete, parallel or sequential steps. "
            f"Return as JSON array: [{{'step': int, 'task': str, 'depends_on': [int]}}]\n\n"
            f"Goal: {goal}"
        )
        raw = self.chat(decomp_prompt, session)

        steps = []
        try:
            import re
            m = re.search(r'\[.*\]', raw, re.DOTALL)
            if m:
                steps = json.loads(m.group(0))
        except Exception:
            steps = [{"step": 1, "task": goal, "depends_on": []}]

        print(f"  Decomposed into {len(steps)} steps")

        # Step 2: Execute steps as subagents
        step_results: dict[int, str] = {}
        for s in steps[:max_steps]:
            step_n = s.get("step", 0)
            task   = s.get("task", "")
            deps   = s.get("depends_on", [])

            context = "\n".join(
                f"Step {d} result: {step_results.get(d, '')[:500]}"
                for d in deps if d in step_results
            )
            print(f"  → Step {step_n}: {task[:60]}")
            result = self.spawn_subagent(task, context=context)
            step_results[step_n] = result

        # Step 3: Synthesise
        synthesis_prompt = (
            f"Goal: {goal}\n\nSubagent results:\n"
            + "\n\n".join(f"Step {k}: {v[:800]}" for k, v in step_results.items())
            + "\n\nSynthesise the above into a coherent, complete final answer."
        )
        final = self.chat(synthesis_prompt, session)

        return {
            "goal":         goal,
            "steps":        steps,
            "step_results": step_results,
            "final":        final,
        }


# ── ManagedAgentsClient (the actual hosted Managed Agents API) ─────────────
# Was missing entirely — nothing in this module talked to the real
# /v1/agents, /v1/environments, /v1/sessions endpoints. Per
# platform.claude.com/docs/en/managed-agents/quickstart (checked
# 2026-07-02): all Managed Agents endpoints require the
# managed-agents-2026-04-01 beta header (the official SDK sets it
# automatically for client.beta.{agents,environments,sessions}.* calls,
# which is what this wraps). Managed Agents is stateful server-side —
# sessions, sandbox filesystem state, and history all live on Anthropic's
# infrastructure — and is currently public beta, not GA, and not eligible
# for Zero Data Retention.
MANAGED_AGENTS_BETA = "managed-agents-2026-04-01"


class ManagedAgentsClient:
    """Thin wrapper around the real Claude Managed Agents API
    (agent → environment → session), as distinct from the local
    Messages-API-based ManagedAgent class above. Requires the `anthropic`
    SDK to be new enough to expose client.beta.agents/environments/sessions
    — older pinned SDK versions won't have these."""

    def __init__(self, api_key: str):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)

    def create_agent(self, name: str, model: str = "claude-opus-4-8",
                     system: str = "You are a helpful coding assistant.",
                     tools: Optional[list] = None) -> dict:
        """Create a persisted, versioned Agent config. tools defaults to the
        full pre-built agent_toolset_20260401 (bash, file ops, web search,
        etc.) if not given."""
        tools = tools or [{"type": "agent_toolset_20260401"}]
        agent = self.client.beta.agents.create(
            name=name, model={"id": model}, system=system, tools=tools,
            betas=[MANAGED_AGENTS_BETA],
        )
        return {"id": agent.id, "name": name, "model": model}

    def create_environment(self, name: str, networking: str = "unrestricted") -> dict:
        """Create a cloud sandbox environment for an agent to run in.
        networking: "unrestricted" or "limited" (safer if the agent only
        needs to touch its own filesystem)."""
        env = self.client.beta.environments.create(
            name=name, config={"type": "cloud", "networking": {"type": networking}},
            betas=[MANAGED_AGENTS_BETA],
        )
        return {"id": env.id, "name": name}

    def create_session(self, agent_id: str, environment_id: str, title: str = "") -> dict:
        session = self.client.beta.sessions.create(
            agent=agent_id, environment_id=environment_id, title=title,
            betas=[MANAGED_AGENTS_BETA],
        )
        return {"id": session.id, "agent_id": agent_id, "environment_id": environment_id}

    def run_task(self, session_id: str, task: str) -> dict:
        """Send a task as a user.message event and stream until the session
        goes idle. Returns the accumulated assistant text and tool calls."""
        text_parts: list[str] = []
        tool_calls: list[dict] = []
        with self.client.beta.sessions.events.stream(session_id, betas=[MANAGED_AGENTS_BETA]) as stream:
            self.client.beta.sessions.events.send(
                session_id,
                events=[{"type": "user.message", "content": [{"type": "text", "text": task}]}],
                betas=[MANAGED_AGENTS_BETA],
            )
            for event in stream:
                if event.type == "agent.message":
                    for block in event.content:
                        if getattr(block, "text", None):
                            text_parts.append(block.text)
                elif event.type == "agent.tool_use":
                    tool_calls.append({"name": event.name})
                elif event.type == "session.status_idle":
                    break
        return {"text": "".join(text_parts), "tool_calls": tool_calls}


def cmd_managed_agent_run(task: str, api_key: str, model: str = "claude-opus-4-8"):
    """End-to-end convenience: create a throwaway agent + environment +
    session, run one task, print the result. For anything beyond a single
    one-off task, create the agent/environment once and reuse them across
    sessions instead — see ManagedAgentsClient methods."""
    mac = ManagedAgentsClient(api_key)
    print("\033[94mℹ Creating Managed Agent, environment, and session…\033[0m")
    agent = mac.create_agent(name=f"ai-coder-task-{uuid.uuid4().hex[:8]}", model=model)
    env   = mac.create_environment(name=f"ai-coder-env-{uuid.uuid4().hex[:8]}")
    sess  = mac.create_session(agent["id"], env["id"], title=task[:60])
    print(f"\033[92m✓ session {sess['id']}\033[0m — running task…\n")
    result = mac.run_task(sess["id"], task)
    print(result["text"])
    if result["tool_calls"]:
        print(f"\n\033[90m[tools used: {', '.join(t['name'] for t in result['tool_calls'])}]\033[0m")
    return result


# ── CLI entry points ───────────────────────────────────────────────────────

def cmd_agent_chat(prompt: str, api_key: str, model: str,
                   session_id: str = None, new: bool = False):
    if session_id and not new:
        try:
            session = AgentSession.load(session_id)
            print(f"\033[94mℹ Resumed session: {session.name} ({len(session.history)} turns)\033[0m\n")
        except FileNotFoundError:
            session = AgentSession(session_id=session_id)
            print(f"\033[94mℹ Created new session: {session.id}\033[0m\n")
    else:
        session = AgentSession()
        print(f"\033[94mℹ New session: {session.id}\033[0m\n")

    agent  = ManagedAgent(api_key=api_key, model=model)
    result = agent.chat(prompt, session)
    print(result)
    print(f"\n\033[90m[session: {session.id}  turns: {len(session.history)//2}]\033[0m")
    print(f"\033[90m  Resume: ai-coder --agent-session {session.id} -p \"follow-up\"\033[0m")
    return result


def cmd_agent_orchestrate(goal: str, api_key: str, model: str, session_id: str = None):
    session = AgentSession(session_id=session_id) if session_id else AgentSession()
    agent   = ManagedAgent(api_key=api_key, model=model)
    result  = agent.orchestrate(goal, session)
    print(f"\n\033[92m✓ Orchestration complete\033[0m\n")
    print(result["final"])
    return result


def cmd_agent_list_sessions():
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    sessions = sorted(SESSIONS_DIR.glob("*.json"))
    if not sessions:
        print("No saved sessions.")
        return
    print(f"\n{'ID':<16}{'NAME':<25}{'TURNS':<8}{'UPDATED'}")
    print("─" * 60)
    for sf in sessions[-20:]:
        try:
            d     = json.loads(sf.read_text())
            turns = len(d.get("history", [])) // 2
            print(f"{d['id']:<16}{d.get('name','')[:24]:<25}{turns:<8}{d.get('updated_at','')[:10]}")
        except Exception:
            pass


def cmd_list_tool_presets():
    print("\nAgent tool presets:")
    for name, tools in TOOL_PRESETS.items():
        print(f"  {name:<14} — {', '.join(tools)}")