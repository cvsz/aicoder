# Design Spec: TUI Full Feature for ai-coder-cli
Date: 2026-07-03
Status: Draft (Pending User Review)

## 1. Overview
The goal is to transform `ai-coder-cli` from a purely command-line interface into a rich, interactive Text User Interface (TUI). This will improve the user experience by providing real-time feedback, a structured dashboard for monitoring agent activity, and a more intuitive way to interact with the AI.

## 2. Architecture & Technical Approach

### 2.1 Engine: Pure Textual (Async)
To achieve a fluid, non-blocking UI, the project will transition to an asynchronous architecture using the **Textual** library.

- **Async Transformation**: 
    - The `Coder` class will be refactored to use `async def generate(...)`.
    - `urllib.request` will be replaced with `httpx` to support asynchronous HTTP requests and streaming responses.
    - `CoreEngine` will act as an async orchestrator, managing a task queue and emitting events to the UI.
- **Event Loop**: The TUI entry point will initialize the `asyncio` event loop, allowing the UI to remain responsive while the AI processes requests in the background.
- **CLI Compatibility**: A synchronous wrapper will be maintained for the existing `main.py` entry point, ensuring that traditional CLI usage remains unbroken.

## 3. UI/UX Design

### 3.1 Hybrid Layout
The interface will use a split-screen layout that balances control and monitoring.

- **Left Panel (Control Center - 40%)**:
    - **Chat History**: A scrollable area displaying interactions in Markdown format (with syntax highlighting for code blocks).
    - **Prompt Input**: A dedicated input field at the bottom for entering prompts and commands.
    - **Quick-Command Palette**: Integration of `--skill` and `--agent` selections via shortcut menus.
- **Right Panel (Monitor Hub - 60%)**:
    - **Status Dashboard**: Real-time display of:
        - `Current Model`
        - `Token Usage` (Input/Output/Total)
        - `API Latency` (ms)
    - **Live Output/Logs**: A streaming log window showing the agent's internal thoughts, tool calls, and system outputs.
    - **File Explorer**: A list of recently modified or created artifacts in the project.

### 3.2 Interactive Features
- **Expandable Views**: A hotkey (e.g., `Ctrl+L`) to toggle the Live Logs to full-screen mode for detailed debugging.
- **Visual Feedback**: 
    - Use of color-coded status indicators (Green: Success, Red: Error, Yellow: Processing).
    - Animated spinners and progress bars for long-running tasks.
- **Quick-Action Bar**: A footer bar with essential shortcuts (e.g., `F1: Help`, `F2: New Session`, `F3: Clear`).

## 4. Reliability & Validation

### 4.1 Error Handling
- **Async Guard**: Every async task will be wrapped in an exception handler to prevent UI freezes. Errors will be displayed as non-intrusive toast notifications.
- **Resilience**:
    - Implementation of request timeouts with an automatic "Retry" prompt.
    - Human-readable mapping of API error codes (e.g., 429 -> "Rate limit exceeded, retrying in X seconds").
    - **Session Recovery**: Automatic saving of the current session state to a temporary JSON file for restoration after an unexpected crash.

### 4.2 Testing Strategy
- **Mock API**: A mock server will be used to simulate various API behaviors (latency, timeouts, failures) to verify UI stability.
- **Responsive Layout Testing**: Validation across multiple terminal sizes to ensure the hybrid layout scales correctly.
- **Resource Profiling**: Monitoring CPU/RAM usage to ensure the TUI remains lightweight.

## 5. Success Criteria
- [ ] User can send prompts and see streaming responses in the TUI.
- [ ] Right panel updates tokens and latency in real-time.
- [ ] Layout remains stable during terminal resizing.
- [ ] CLI mode continues to function without regressions.
- [ ] API errors are caught and displayed without crashing the UI.