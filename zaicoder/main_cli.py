"""Product API adapters used by the primary ``main.py`` CLI.

This module intentionally owns only migrated commands.  Legacy provider
commands remain in ``main.py`` until their Product API equivalents land.
"""

from __future__ import annotations

import sys
import uuid
from enum import IntEnum
from pathlib import Path
from typing import Any, Optional, TextIO

from zaicoder.client import ProductAPIError, build_product_api_client
from zaicoder.domain import StreamEventType


class MainCLIExitCode(IntEnum):
    OK = 0
    VALIDATION = 2
    UNAUTHENTICATED = 3
    FORBIDDEN = 4
    UNAVAILABLE = 5
    TIMEOUT = 6
    PROTOCOL = 7


def _exit_for_error(error: ProductAPIError) -> MainCLIExitCode:
    code = error.envelope.error.code
    if code in {"validation_error", "invalid_request"}:
        return MainCLIExitCode.VALIDATION
    if code == "unauthenticated":
        return MainCLIExitCode.UNAUTHENTICATED
    if code == "forbidden":
        return MainCLIExitCode.FORBIDDEN
    if code in {"provider_unavailable", "service_unavailable", "not_ready"}:
        return MainCLIExitCode.UNAVAILABLE
    if code in {"timeout", "provider_timeout"}:
        return MainCLIExitCode.TIMEOUT
    return MainCLIExitCode.PROTOCOL


def _assistant_text(payload: Any) -> str:
    message = payload.get("message") if isinstance(payload, dict) else None
    if not isinstance(message, dict) or not isinstance(message.get("content"), list):
        raise ValueError("message response requires assistant content")
    return "".join(
        str(block.get("text", ""))
        for block in message["content"]
        if isinstance(block, dict) and block.get("type") == "text"
    )


def run_prompt(
    prompt: str,
    *,
    model: str,
    max_tokens: int,
    output_path: Optional[str] = None,  # noqa: UP045 - Python 3.9 compatibility
    client: Any = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    request_id: Optional[str] = None,  # noqa: UP045 - Python 3.9 compatibility
    correlation_id: Optional[str] = None,  # noqa: UP045 - Python 3.9 compatibility
) -> int:
    """Run a simple primary CLI prompt through the canonical Product API."""
    if not prompt:
        print("[ERROR] --prompt is required", file=stderr)
        return int(MainCLIExitCode.VALIDATION)
    if max_tokens <= 0:
        print("[ERROR] --max-tokens must be positive", file=stderr)
        return int(MainCLIExitCode.VALIDATION)

    request_id = request_id or str(uuid.uuid4())
    correlation_id = correlation_id or request_id
    try:
        api = client or build_product_api_client()
        response = api.create_message(
            {
                "model": model,
                "max_output_tokens": max_tokens,
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            },
            request_id=request_id,
            correlation_id=correlation_id,
        )
        text = _assistant_text(response)
        print(text, file=stdout)
        if output_path:
            Path(output_path).write_text(text, encoding="utf-8")
        return int(MainCLIExitCode.OK)
    except ProductAPIError as exc:
        print(exc.envelope.error.message, file=stderr)
        return int(_exit_for_error(exc))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=stderr)
        return int(MainCLIExitCode.VALIDATION)


def run_stream(
    prompt: str,
    *,
    model: str,
    max_tokens: int,
    client: Any = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    request_id: Optional[str] = None,  # noqa: UP045 - Python 3.9 compatibility
    correlation_id: Optional[str] = None,  # noqa: UP045 - Python 3.9 compatibility
) -> int:
    """Stream a simple primary CLI prompt through canonical Product API events."""
    if not prompt:
        print("[ERROR] --prompt is required", file=stderr)
        return int(MainCLIExitCode.VALIDATION)
    if max_tokens <= 0:
        print("[ERROR] --max-tokens must be positive", file=stderr)
        return int(MainCLIExitCode.VALIDATION)

    request_id = request_id or str(uuid.uuid4())
    correlation_id = correlation_id or request_id
    try:
        api = client or build_product_api_client()
        terminal = None
        for event in api.stream_message(
            {
                "model": model,
                "max_output_tokens": max_tokens,
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            },
            request_id=request_id,
            correlation_id=correlation_id,
        ):
            if event.type is StreamEventType.CONTENT_DELTA:
                print(str(event.data.get("text", "")), end="", flush=True, file=stdout)
            if event.terminal:
                terminal = event

        if terminal is None:
            raise ValueError("stream ended without a terminal event")
        if terminal.type is StreamEventType.STREAM_CANCELLED:
            return 130
        if terminal.type is StreamEventType.STREAM_FAILED:
            print(str(terminal.data.get("message", "Product API stream failed")), file=stderr)
            return int(
                MainCLIExitCode.UNAVAILABLE if terminal.data.get("retryable") else MainCLIExitCode.PROTOCOL
            )
        print(file=stdout)
        return int(MainCLIExitCode.OK)
    except KeyboardInterrupt:
        return 130
    except ProductAPIError as exc:
        print(exc.envelope.error.message, file=stderr)
        return int(_exit_for_error(exc))
    except (RuntimeError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=stderr)
        return int(MainCLIExitCode.VALIDATION)


def run_model_listing(
    *,
    client: Any = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    request_id: Optional[str] = None,  # noqa: UP045 - Python 3.9 compatibility
    correlation_id: Optional[str] = None,  # noqa: UP045 - Python 3.9 compatibility
) -> int:
    """List Product API models using the legacy CLI's human-readable layout."""
    request_id = request_id or str(uuid.uuid4())
    correlation_id = correlation_id or request_id
    try:
        api = client or build_product_api_client()
        models = api.list_models(request_id=request_id, correlation_id=correlation_id)
        print(f"\n{'MODEL ID':<35}{'DISPLAY NAME':<35}{'CONTEXT'}", file=stdout)
        print("-" * 85, file=stdout)
        for model in models:
            context = model.capabilities.max_context_tokens
            context_display = f"{context // 1000}K" if context else "-"
            print(f"{model.id:<35}{model.display_name[:34]:<35}{context_display}", file=stdout)
        print(f"\n{len(models)} models available", file=stdout)
        return int(MainCLIExitCode.OK)
    except ProductAPIError as exc:
        print(exc.envelope.error.message, file=stderr)
        return int(_exit_for_error(exc))
    except (RuntimeError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=stderr)
        return int(MainCLIExitCode.VALIDATION)
