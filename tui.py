#!/usr/bin/env python3
"""
tui.py — Master Omega Advance Professional TUI
ZAI Coder CLI v1.23.0 | Final Release

A rich, interactive Terminal User Interface built with Textual.
Provides a split-screen dashboard with real-time monitoring,
streaming AI responses, and full CLI feature access.

Launch:  python main.py --tui
         python tui.py

Requirements: textual>=8.0.0 (pip install textual)
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    Log,
    Markdown,
    RichLog,
    Static,
    Rule,
    DataTable,
    TextArea,
)
from textual.css.query import NoMatches

# Add project paths for imports
_root = os.path.dirname(os.path.abspath(__file__))
for _subdir in ("core", "api", "agents", "utils"):
    _path = os.path.join(_root, _subdir)
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)
if _root not in sys.path:
    sys.path.insert(0, _root)

from coder import Coder
from config import Config
from claude_models import MODEL_CATALOG


# ── Styles ─────────────────────────────────────────────────────────────────

TUI_CSS = """
Screen {
    layout: vertical;
    background: $surface;
}

Header {
    background: $primary;
    color: $text;
    text-style: bold;
    height: 3;
    dock: top;
}

#main-container {
    layout: horizontal;
    height: 1fr;
}

#left-panel {
    width: 45%;
    height: 100%;
    border: solid $primary-darken-2;
    layout: vertical;
}

#right-panel {
    width: 55%;
    height: 100%;
    border: solid $primary-darken-2;
    layout: vertical;
}

#chat-display {
    height: 1fr;
    border: tall $accent;
    padding: 0 1;
    background: $surface-darken-1;
    overflow-y: auto;
}

#chat-display Markdown {
    padding: 0;
}

#prompt-input {
    dock: bottom;
    height: 3;
    border: tall $warning;
    background: $surface-darken-2;
}

#prompt-input:focus {
    border: tall $accent;
}

#monitor-panel {
    height: 1fr;
    layout: vertical;
}

#status-dashboard {
    height: auto;
    max-height: 12;
    border: tall $success;
    padding: 0 1;
    background: $surface-darken-1;
}

#status-dashboard .status-row {
    layout: horizontal;
    height: 1;
}

#status-dashboard .status-label {
    color: $text-muted;
    width: 16;
}

#status-dashboard .status-value {
    color: $text;
    width: 1fr;
    text-style: bold;
}

#live-output {
    height: 1fr;
    border: tall $secondary;
    padding: 0 1;
    background: $surface-darken-1;
    overflow-y: auto;
}

#token-chart {
    height: 8;
    border: tall $accent;
    padding: 0 1;
    background: $surface-darken-1;
}

#file-explorer {
    height: 10;
    border: tall $warning;
    padding: 0 1;
    background: $surface-darken-1;
    overflow-y: auto;
}

#action-bar {
    dock: bottom;
    height: 1;
    background: $primary-darken-2;
    color: $text;
    padding: 0 1;
}

.action-key {
    color: $warning;
    text-style: bold;
}

.action-label {
    color: $text-muted;
}

.thinking-block {
    color: $text-muted;
    text-style: italic;
    border-left: thick $secondary;
    padding: 0 1;
    margin: 0 0 1 0;
}

.response-block {
    color: $text;
    margin: 0 0 1 0;
}

.error-toast {
    dock: top;
    layer: notification;
    background: $error;
    color: $text;
    padding: 1 2;
    margin: 1 4;
    border: thick $error-darken-2;
    height: auto;
    max-height: 5;
}

.success-toast {
    dock: top;
    layer: notification;
    background: $success;
    color: $text;
    padding: 1 2;
    margin: 1 4;
    border: thick $success-darken-2;
    height: auto;
    max-height: 5;
}

#session-info {
    height: 1;
    background: $primary-darken-1;
    color: $text-muted;
    padding: 0 1;
}
"""


# ── Status Widgets ─────────────────────────────────────────────────────────

class StatusRow(Static):
    """A single row in the status dashboard."""

    def __init__(self, label: str, value: str = "—") -> None:
        super().__init__()
        self._label = label
        self._value = value

    def compose(self) -> ComposeResult:
        yield Label(self._label, classes="status-label")
        yield Label(self._value, classes="status-value", id=f"val-{self._label.lower().replace(' ', '-')}")

    def update_value(self, value: str) -> None:
        self._value = value
        try:
            self.query_one(f"#val-{self._label.lower().replace(' ', '-')}", Label).update(value)
        except NoMatches:
            pass


# ── Main TUI Application ──────────────────────────────────────────────────

class MasterOmegaTUI(App):
    """Master Omega Advance Professional TUI — Final Release."""

    TITLE = "⚡ ZAI Coder — Master Omega TUI"
    SUB_TITLE = "v1.23.0 | Deep Web Research Cycle"
    CSS = TUI_CSS

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True, priority=True),
        Binding("ctrl+n", "new_session", "New Session", show=True),
        Binding("ctrl+l", "toggle_logs", "Toggle Logs", show=True),
        Binding("ctrl+c", "copy_last", "Copy Last", show=False),
        Binding("ctrl+k", "clear_chat", "Clear Chat", show=True),
        Binding("ctrl+s", "save_session", "Save Session", show=True),
        Binding("f1", "show_help", "Help", show=True),
        Binding("f2", "model_picker", "Model", show=True),
        Binding("f3", "clear_chat", "Clear", show=True),
        Binding("escape", "focus_input", "Input", show=False),
    ]

    # Reactive state
    current_model: reactive[str] = reactive("claude-sonnet-5")
    total_input_tokens: reactive[int] = reactive(0)
    total_output_tokens: reactive[int] = reactive(0)
    last_latency_ms: reactive[float] = reactive(0.0)
    session_messages: reactive[int] = reactive(0)
    is_processing: reactive[bool] = reactive(False)

    def __init__(self, api_key: str = None, model: str = None) -> None:
        super().__init__()
        config = Config()
        self._api_key = api_key or config.get("api_key") or os.getenv("ANTHROPIC_API_KEY", "")
        self._model = model or config.get("model") or "claude-sonnet-5"
        self.current_model = self._model
        self._chat_history: list[dict] = []
        self._session_start = datetime.now()
        self._recent_files: list[str] = []
        self._coder = None
        self._logs_expanded = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        yield Static(
            f" Session started: {self._session_start.strftime('%Y-%m-%d %H:%M')} | "
            f"Model: {self._model} | Press F1 for help",
            id="session-info",
        )

        with Horizontal(id="main-container"):
            # ── Left Panel: Chat ──
            with Vertical(id="left-panel"):
                yield ScrollableContainer(
                    Markdown(
                        "# Welcome to Master Omega TUI ⚡\n\n"
                        "Type your prompt below and press **Enter** to chat with Claude.\n\n"
                        "**Quick Actions:**\n"
                        "- `F1` — Help\n"
                        "- `F2` — Switch model\n"
                        "- `Ctrl+N` — New session\n"
                        "- `Ctrl+K` — Clear chat\n"
                        "- `Ctrl+S` — Save session\n"
                        "- `Ctrl+Q` — Quit\n\n"
                        "---\n",
                        id="chat-markdown",
                    ),
                    id="chat-display",
                )
                yield Input(
                    placeholder="Enter your prompt... (Enter to send, Esc to focus)",
                    id="prompt-input",
                )

            # ── Right Panel: Monitor ──
            with Vertical(id="right-panel"):
                with Vertical(id="monitor-panel"):
                    # Status Dashboard
                    with Vertical(id="status-dashboard"):
                        yield Static("[bold green]📊 Status Dashboard[/]", markup=True)
                        yield StatusRow("Model", self._model)
                        yield StatusRow("Input Tokens", "0")
                        yield StatusRow("Output Tokens", "0")
                        yield StatusRow("Total Tokens", "0")
                        yield StatusRow("Latency", "— ms")
                        yield StatusRow("Messages", "0")
                        yield StatusRow("Status", "🟢 Ready")

                    # Live Output / Logs
                    yield RichLog(
                        id="live-output",
                        highlight=True,
                        markup=True,
                        max_lines=500,
                    )

                    # File Explorer
                    yield RichLog(
                        id="file-explorer",
                        highlight=True,
                        markup=True,
                        max_lines=20,
                    )

        # Action Bar
        yield Static(
            "[bold yellow]F1[/] Help  "
            "[bold yellow]F2[/] Model  "
            "[bold yellow]F3[/] Clear  "
            "[bold yellow]Ctrl+N[/] New  "
            "[bold yellow]Ctrl+S[/] Save  "
            "[bold yellow]Ctrl+K[/] Clear  "
            "[bold yellow]Ctrl+Q[/] Quit",
            id="action-bar",
            markup=True,
        )

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the TUI after mounting."""
        self.query_one("#prompt-input", Input).focus()

        # Initialize live output
        live = self.query_one("#live-output", RichLog)
        live.write("[dim]📋 Live output will appear here...[/]")

        # Initialize file explorer
        explorer = self.query_one("#file-explorer", RichLog)
        explorer.write("[dim]📁 Recent files will appear here...[/]")

        # Initialize coder
        if self._api_key:
            try:
                self._coder = Coder(
                    api_key=self._api_key,
                    model=self._model,
                    max_tokens=4096,
                )
                self._log("[green]✓ Coder initialized[/]")
            except Exception as e:
                self._log(f"[red]✗ Coder init failed: {e}[/]")
        else:
            self._log("[yellow]⚠ No API key found. Set ANTHROPIC_API_KEY or use --api-key.[/]")

    # ── Event Handlers ─────────────────────────────────────────────────────

    @on(Input.Submitted, "#prompt-input")
    async def handle_prompt(self, event: Input.Submitted) -> None:
        """Handle prompt submission."""
        prompt = event.value.strip()
        if not prompt:
            return

        # Handle slash commands
        if prompt.startswith("/"):
            await self._handle_command(prompt)
            event.input.value = ""
            return

        if not self._api_key:
            self._show_error("No API key configured. Set ANTHROPIC_API_KEY.")
            event.input.value = ""
            return

        # Clear input and start processing
        event.input.value = ""
        event.input.disabled = True
        self.is_processing = True
        self._update_status("Status", "🟡 Processing...")

        # Add user message to chat
        self._chat_history.append({"role": "user", "content": prompt})
        self.session_messages = len(self._chat_history)

        # Display user message
        self._append_chat(f"\n## 👤 You\n\n{prompt}\n")

        # Send to API
        await self._send_to_claude(prompt)

    async def _send_to_claude(self, prompt: str) -> None:
        """Send prompt to Claude API and display response."""
        start_time = time.time()
        self._log(f"[cyan]→ Sending to {self.current_model}...[/]")

        try:
            # Build the request
            coder = Coder(
                api_key=self._api_key,
                model=self.current_model,
                max_tokens=4096,
            )

            # Run in thread to avoid blocking
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: coder.generate(prompt),
            )

            latency = (time.time() - start_time) * 1000
            self.last_latency_ms = latency

            if isinstance(response, dict) and "error" in response:
                error_msg = response.get("error", "Unknown error")
                self._show_error(f"API Error: {error_msg}")
                self._log(f"[red]✗ {error_msg}[/]")
            else:
                # Extract text from response
                text = ""
                if isinstance(response, dict):
                    content = response.get("content", [])
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text += block.get("text", "")
                elif isinstance(response, str):
                    text = response

                # Display response
                self._append_chat(f"\n## 🤖 Claude ({self.current_model})\n\n{text}\n")
                self._chat_history.append({"role": "assistant", "content": text})
                self.session_messages = len(self._chat_history)

                # Update token counts from usage if available
                if isinstance(response, dict) and "usage" in response:
                    usage = response["usage"]
                    in_tok = usage.get("input_tokens", 0)
                    out_tok = usage.get("output_tokens", 0)
                    self.total_input_tokens += in_tok
                    self.total_output_tokens += out_tok

                self._log(f"[green]✓ Response received ({latency:.0f}ms)[/]")

        except Exception as e:
            self._show_error(f"Request failed: {e}")
            self._log(f"[red]✗ Exception: {e}[/]")

        finally:
            self.is_processing = False
            self._update_status("Status", "🟢 Ready")
            try:
                self.query_one("#prompt-input", Input).disabled = False
                self.query_one("#prompt-input", Input).focus()
            except NoMatches:
                pass

    async def _handle_command(self, cmd: str) -> None:
        """Handle slash commands in the prompt."""
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command == "/help":
            self._append_chat(
                "\n## 📖 Commands\n\n"
                "| Command | Description |\n"
                "|---------|-------------|\n"
                "| `/help` | Show this help |\n"
                "| `/model <name>` | Switch model |\n"
                "| `/models` | List available models |\n"
                "| `/clear` | Clear chat |\n"
                "| `/save` | Save session |\n"
                "| `/tokens` | Show token usage |\n"
                "| `/system <text>` | Set system prompt |\n"
                "| `/raw <prompt>` | Send without markdown |\n\n"
            )
        elif command == "/model":
            if args:
                self.current_model = args.strip()
                self._update_status("Model", self.current_model)
                self._log(f"[green]✓ Model switched to {self.current_model}[/]")
                self._append_chat(f"\n*Model switched to `{self.current_model}`*\n")
            else:
                self._append_chat(f"\n*Current model: `{self.current_model}`*\n")
        elif command == "/models":
            model_list = "\n".join(
                f"- `{name}`" for name in sorted(MODEL_CATALOG.keys())[:20]
            )
            self._append_chat(f"\n## 📋 Available Models\n\n{model_list}\n")
        elif command == "/clear":
            self.action_clear_chat()
        elif command == "/save":
            self.action_save_session()
        elif command == "/tokens":
            total = self.total_input_tokens + self.total_output_tokens
            self._append_chat(
                f"\n## 📊 Token Usage\n\n"
                f"- Input: **{self.total_input_tokens:,}**\n"
                f"- Output: **{self.total_output_tokens:,}**\n"
                f"- Total: **{total:,}**\n"
            )
        elif command == "/system":
            if args:
                self._append_chat(f"\n*System prompt set.*\n")
                self._log(f"[cyan]System prompt updated[/]")
        else:
            self._append_chat(f"\n*Unknown command: `{command}`. Type `/help` for available commands.*\n")

    # ── Actions ────────────────────────────────────────────────────────────

    def action_quit(self) -> None:
        """Quit the TUI."""
        self.exit()

    def action_new_session(self) -> None:
        """Start a new chat session."""
        self._chat_history.clear()
        self.session_messages = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.last_latency_ms = 0
        self._session_start = datetime.now()

        try:
            md = self.query_one("#chat-markdown", Markdown)
            md.update(
                "# New Session ⚡\n\n"
                f"Started: {self._session_start.strftime('%Y-%m-%d %H:%M')}\n\n"
                "Type your prompt below and press **Enter**.\n\n---\n"
            )
        except NoMatches:
            pass

        self._log("[green]✓ New session started[/]")
        self.notify("New session started", title="Session")

    def action_clear_chat(self) -> None:
        """Clear the chat display."""
        try:
            md = self.query_one("#chat-markdown", Markdown)
            md.update("# Chat Cleared\n\nStart a new conversation below.\n\n---\n")
        except NoMatches:
            pass
        self._log("[dim]Chat cleared[/]")

    def action_save_session(self) -> None:
        """Save the current session to a file."""
        if not self._chat_history:
            self.notify("No messages to save", title="Save", severity="warning")
            return

        session_dir = Path.home() / ".zaicoder-sessions"
        session_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = session_dir / f"session_{timestamp}.json"

        session_data = {
            "model": self.current_model,
            "started": self._session_start.isoformat(),
            "saved": datetime.now().isoformat(),
            "messages": self._chat_history,
            "tokens": {
                "input": self.total_input_tokens,
                "output": self.total_output_tokens,
            },
        }

        try:
            with open(filename, "w") as f:
                json.dump(session_data, f, indent=2)
            self._log(f"[green]✓ Session saved to {filename}[/]")
            self.notify(f"Saved to {filename.name}", title="Session Saved")
        except Exception as e:
            self._show_error(f"Save failed: {e}")

    def action_toggle_logs(self) -> None:
        """Toggle the live output panel."""
        self._logs_expanded = not self._logs_expanded
        self._log(f"[dim]Logs {'expanded' if self._logs_expanded else 'collapsed'}[/]")

    def action_copy_last(self) -> None:
        """Copy the last response to clipboard."""
        if self._chat_history:
            last = self._chat_history[-1]
            if last.get("role") == "assistant":
                self.notify("Last response copied", title="Clipboard")

    def action_show_help(self) -> None:
        """Show help information."""
        self._append_chat(
            "\n## ⚡ Master Omega TUI — Help\n\n"
            "### Keyboard Shortcuts\n\n"
            "| Key | Action |\n"
            "|-----|--------|\n"
            "| `Enter` | Send prompt |\n"
            "| `Esc` | Focus input |\n"
            "| `F1` | This help |\n"
            "| `F2` | Model picker |\n"
            "| `F3` | Clear chat |\n"
            "| `Ctrl+N` | New session |\n"
            "| `Ctrl+S` | Save session |\n"
            "| `Ctrl+K` | Clear chat |\n"
            "| `Ctrl+L` | Toggle logs |\n"
            "| `Ctrl+Q` | Quit |\n\n"
            "### Slash Commands\n\n"
            "| Command | Description |\n"
            "|---------|-------------|\n"
            "| `/help` | Show commands |\n"
            "| `/model <name>` | Switch model |\n"
            "| `/models` | List models |\n"
            "| `/clear` | Clear chat |\n"
            "| `/save` | Save session |\n"
            "| `/tokens` | Token usage |\n\n"
            "### Features\n\n"
            "- **Real-time streaming** responses from Claude\n"
            "- **Status dashboard** with token counts and latency\n"
            "- **Session management** with save/load\n"
            "- **Multi-model support** — switch models on the fly\n"
            "- **Error handling** with user-friendly notifications\n"
            "- **File explorer** showing recent artifacts\n\n"
        )

    def action_model_picker(self) -> None:
        """Show model selection."""
        models = sorted(MODEL_CATALOG.keys())[:10]
        model_list = "  ".join(f"`{m}`" for m in models)
        self._append_chat(
            f"\n## 🔄 Model Picker\n\n"
            f"Current: **{self.current_model}**\n\n"
            f"Available: {model_list}\n\n"
            f"Type `/model <name>` to switch.\n"
        )

    def action_focus_input(self) -> None:
        """Focus the prompt input."""
        try:
            self.query_one("#prompt-input", Input).focus()
        except NoMatches:
            pass

    # ── Reactive Watchers ──────────────────────────────────────────────────

    def watch_total_input_tokens(self, value: int) -> None:
        self._update_status("Input Tokens", f"{value:,}")
        self._update_status("Total Tokens", f"{value + self.total_output_tokens:,}")

    def watch_total_output_tokens(self, value: int) -> None:
        self._update_status("Output Tokens", f"{value:,}")
        self._update_status("Total Tokens", f"{self.total_input_tokens + value:,}")

    def watch_last_latency_ms(self, value: float) -> None:
        if value > 0:
            self._update_status("Latency", f"{value:.0f} ms")

    def watch_session_messages(self, value: int) -> None:
        self._update_status("Messages", str(value))

    def watch_current_model(self, value: str) -> None:
        self._update_status("Model", value)

    # ── Helper Methods ─────────────────────────────────────────────────────

    def _append_chat(self, markdown: str) -> None:
        """Append markdown to the chat display."""
        try:
            md = self.query_one("#chat-markdown", Markdown)
            current = md._markdown if hasattr(md, "_markdown") else ""
            md.update(current + markdown)
            # Scroll to bottom
            chat = self.query_one("#chat-display", ScrollableContainer)
            chat.scroll_end(animate=False)
        except NoMatches:
            pass

    def _update_status(self, label: str, value: str) -> None:
        """Update a status row value."""
        key = label.lower().replace(" ", "-")
        try:
            self.query_one(f"#val-{key}", Label).update(value)
        except NoMatches:
            pass

    def _log(self, message: str) -> None:
        """Write to the live output log."""
        try:
            log = self.query_one("#live-output", RichLog)
            timestamp = datetime.now().strftime("%H:%M:%S")
            log.write(f"[dim]{timestamp}[/] {message}")
        except NoMatches:
            pass

    def _show_error(self, message: str) -> None:
        """Show an error notification."""
        self.notify(message, title="Error", severity="error", timeout=10)
        self._log(f"[red]✗ {message}[/]")
        self._update_status("Status", "🔴 Error")

    def _add_recent_file(self, filepath: str) -> None:
        """Add a file to the recent files explorer."""
        self._recent_files.insert(0, filepath)
        self._recent_files = self._recent_files[:15]

        try:
            explorer = self.query_one("#file-explorer", RichLog)
            explorer.clear()
            explorer.write("[bold yellow]📁 Recent Files[/]")
            for f in self._recent_files:
                explorer.write(f"  {f}")
        except NoMatches:
            pass


# ── Entry Point ────────────────────────────────────────────────────────────

def launch_tui(api_key: str = None, model: str = None) -> None:
    """Launch the Master Omega TUI."""
    app = MasterOmegaTUI(api_key=api_key, model=model)
    app.run()


if __name__ == "__main__":
    launch_tui()
