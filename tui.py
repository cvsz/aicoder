"""Interactive Textual UI backed exclusively by the Product API."""
from __future__ import annotations

import time
from typing import Optional

try:
    from textual import work
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.widgets import Button, Footer, Header, Input, Label, Select, Static, Switch
except ImportError as exc:  # pragma: no cover
    raise ImportError("The --tui flag needs textual>=0.80.0") from exc

from claude_models import MODEL_CATALOG
from personalities import PersonalityManager
from skills import SkillManager
from tui_streaming import StreamRenderGate
from zaicoder.client import ProductAPIClient
from zaicoder.client.runtime import build_product_api_client
from zaicoder.domain import StreamEventType

DEFAULT_MODEL = "claude-sonnet-5"


def _agent_prompts() -> dict:
    from main import AGENT_SYSTEM_PROMPTS
    return AGENT_SYSTEM_PROMPTS


class ChatMessage(Static):
    def __init__(self, role: str, text: str = ""):
        super().__init__(self._format(role, text), markup=False)
        self.role = role
        self.raw_text = text
        self.add_class(f"msg-{role}")

    @staticmethod
    def _format(role: str, text: str) -> str:
        symbol = {"user": "$", "assistant": ">", "error": "!", "system": "·"}.get(role, ">")
        return f"{symbol} {text}"

    def update_text(self, text: str) -> None:
        self.raw_text = text
        self.update(self._format(self.role, text))


class SessionSidebar(Vertical):
    def compose(self) -> ComposeResult:
        model_options = [(f"{info.get('display_name', mid)} ({info.get('tier', '')})", mid) for mid, info in MODEL_CATALOG.items()]
        personalities = [("none", "")] + [(p["name"], p["name"]) for p in PersonalityManager().list_personalities()]
        agents = [("none", "")] + [(name, name) for name in _agent_prompts()]
        skills = [("none", "")] + [(s["name"], s["name"]) for s in SkillManager().list_skills()]
        yield Label("model", classes="side-label")
        yield Select(model_options, value=DEFAULT_MODEL, id="model_select")
        yield Label("personality", classes="side-label")
        yield Select(personalities, value="", id="personality_select")
        yield Label("agent role", classes="side-label")
        yield Select(agents, value="", id="agent_select")
        yield Label("skill focus", classes="side-label")
        yield Select(skills, value="", id="skill_select")
        yield Label("temperature: 0.3", classes="side-label")
        yield Input(value="0.3", id="temp_input")
        with Horizontal(classes="stream-row"):
            yield Label("stream", classes="side-label")
            yield Switch(value=True, id="stream_switch")


class ZCoderTUI(App):
    CSS = """
    Screen { layout: horizontal; }
    #sidebar { width: 32; border-right: solid $panel-darken-2; padding: 1 2; overflow-y: auto; }
    #main { width: 1fr; }
    #transcript { padding: 1 2; }
    .side-label { color: $text-muted; text-style: bold; margin-top: 1; }
    .stream-row { height: 3; align: left middle; }
    #input_row { height: 3; dock: bottom; padding: 0 1; }
    #prompt_input { width: 1fr; }
    .msg-user { color: $accent; margin: 1 0 0 0; }
    .msg-assistant { color: $success; margin: 1 0 0 0; }
    .msg-error { color: $error; margin: 1 0 0 0; }
    .msg-system { color: $text-muted; margin: 1 0 0 0; }
    """
    BINDINGS = [("ctrl+n", "new_session", "New session"), ("ctrl+q", "quit", "Quit"), ("ctrl+t", "toggle_dark", "Toggle theme")]

    def __init__(self, client: Optional[ProductAPIClient] = None):
        super().__init__()
        self.client = client
        self.client_error: Optional[str] = None
        if self.client is None:
            try:
                self.client = build_product_api_client()
            except ValueError as exc:
                self.client_error = str(exc)
        self.history: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with SessionSidebar(id="sidebar"):
                pass
            with Vertical(id="main"):
                yield VerticalScroll(id="transcript")
                with Horizontal(id="input_row"):
                    yield Input(placeholder="Ask ZAI Coder anything…", id="prompt_input")
                    yield Button("run", id="send_btn", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        transcript = self.query_one("#transcript")
        transcript.mount(ChatMessage("system", "ZAI Coder TUI ready via Product API."))
        if self.client_error:
            transcript.mount(ChatMessage("error", f"Product API unavailable: {self.client_error}"))
        self.query_one("#prompt_input").focus()

    def action_new_session(self) -> None:
        self.history = []
        transcript = self.query_one("#transcript")
        transcript.remove_children()
        transcript.mount(ChatMessage("system", "new session started."))

    def action_toggle_dark(self) -> None:
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "prompt_input": self._send()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send_btn": self._send()

    def _selected(self, widget_id: str) -> str:
        value = self.query_one(f"#{widget_id}", Select).value
        return value if value not in (None, Select.BLANK) else ""

    def _temperature(self) -> float:
        try: value = float(self.query_one("#temp_input", Input).value.strip())
        except ValueError: value = 0.3
        return max(0.0, min(1.0, value))

    def _build_system_prompt(self) -> Optional[str]:
        parts = []
        agent = self._selected("agent_select")
        if agent: parts.append(_agent_prompts().get(agent, ""))
        skill = self._selected("skill_select")
        if skill:
            info = SkillManager().get_skill(skill)
            if info: parts.append(f"Apply the '{info['name']}' skill: {info['description']}")
        personality = self._selected("personality_select")
        if personality: parts.append(PersonalityManager().build_prompt_addition(personality))
        return "\n\n".join(p for p in parts if p) or None

    def _send(self) -> None:
        prompt_input = self.query_one("#prompt_input", Input)
        text = prompt_input.value.strip()
        if not text or self.client is None: return
        prompt_input.value = ""
        transcript = self.query_one("#transcript")
        transcript.mount(ChatMessage("user", text))
        reply = ChatMessage("assistant", "…")
        transcript.mount(reply)
        self._run_generation(text, self._selected("model_select") or DEFAULT_MODEL, self._build_system_prompt(), self._temperature(), self.query_one("#stream_switch", Switch).value, reply)

    def _payload(self, prompt: str, model: str, system: Optional[str], temperature: float) -> dict:
        messages = list(self.history) + [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        if system:
            messages.insert(0, {"role": "system", "content": [{"type": "text", "text": system}]})
        return {"model": model, "messages": messages, "max_output_tokens": 4096, "metadata": {"temperature": temperature, "surface": "tui"}}

    @work(exclusive=False, thread=True)
    def _run_generation(self, prompt, model, system, temperature, streaming, reply_widget) -> None:
        payload = self._payload(prompt, model, system, temperature)
        try:
            full_text = self._stream_reply(payload, reply_widget) if streaming else self._create_reply(payload)
            self.call_from_thread(reply_widget.update_text, full_text)
        except Exception as exc:
            full_text = f"[ERROR] {exc}"
            self.call_from_thread(reply_widget.update_text, full_text)
            self.call_from_thread(reply_widget.add_class, "msg-error")
        self.history += [{"role": "user", "content": [{"type": "text", "text": prompt}]}, {"role": "assistant", "content": [{"type": "text", "text": full_text}]}]

    def _create_reply(self, payload: dict) -> str:
        assert self.client is not None
        result = self.client.create_message(payload)
        blocks = result.get("message", {}).get("content", [])
        return "".join(str(block.get("text", "")) for block in blocks if block.get("type") == "text")

    def _stream_reply(self, payload: dict, reply_widget) -> str:
        assert self.client is not None
        full_text = ""
        gate = StreamRenderGate()
        try:
            for event in self.client.stream_message(payload):
                if event.type is StreamEventType.CONTENT_DELTA:
                    text = str(event.data.get("text", ""))
                    full_text += text
                    if gate.should_render(text, time.monotonic()):
                        self.call_from_thread(reply_widget.update_text, full_text)
                elif event.type is StreamEventType.STREAM_FAILED:
                    raise RuntimeError(str(event.data.get("message", "Product API stream failed")))
                elif event.type is StreamEventType.STREAM_CANCELLED:
                    break
        finally:
            self.call_from_thread(reply_widget.update_text, full_text)
        return full_text


def run_tui(api_key: Optional[str] = None, client: Optional[ProductAPIClient] = None) -> None:
    """Backward-compatible entry point; api_key is intentionally ignored."""
    del api_key
    ZCoderTUI(client=client).run()


if __name__ == "__main__":  # pragma: no cover
    run_tui()
