"""Provider-neutral command-line interface for the ZAI Coder Product API."""

from __future__ import annotations

import argparse
import json
import sys
from enum import IntEnum
from typing import Any, Iterable, Mapping, Optional, Sequence, TextIO

from zaicoder.client import ProductAPIError, build_product_api_client
from zaicoder.domain import StreamEventType


class ExitCode(IntEnum):
    OK = 0
    VALIDATION = 2
    UNAUTHENTICATED = 3
    FORBIDDEN = 4
    UNAVAILABLE = 5
    TIMEOUT = 6
    PROTOCOL = 7
    CANCELLED = 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zai-coder-api", description="ZAI Coder Product API CLI")
    parser.add_argument("-p", "--prompt")
    parser.add_argument("--model", default="claude-sonnet-5")
    parser.add_argument("--max-tokens", type=int, default=4096, dest="max_tokens")
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--list-models", action="store_true")
    return parser


def _request_payload(args: argparse.Namespace) -> Mapping[str, Any]:
    if not args.prompt:
        raise ValueError("--prompt is required")
    if args.max_tokens <= 0:
        raise ValueError("--max-tokens must be positive")
    return {
        "model": args.model,
        "max_output_tokens": args.max_tokens,
        "messages": [{"role": "user", "content": [{"type": "text", "text": args.prompt}]}],
    }


def _exit_for_error(error: ProductAPIError) -> ExitCode:
    code = error.envelope.error.code
    if code in {"validation_error", "invalid_request"}:
        return ExitCode.VALIDATION
    if code == "unauthenticated":
        return ExitCode.UNAUTHENTICATED
    if code == "forbidden":
        return ExitCode.FORBIDDEN
    if code in {"provider_unavailable", "service_unavailable", "not_ready"}:
        return ExitCode.UNAVAILABLE
    if code in {"timeout", "provider_timeout"}:
        return ExitCode.TIMEOUT
    return ExitCode.PROTOCOL


def _assistant_text(payload: Mapping[str, Any]) -> str:
    message = payload.get("message")
    if not isinstance(message, Mapping):
        raise ValueError("message response requires a message object")
    blocks = message.get("content")
    if not isinstance(blocks, list):
        raise ValueError("message response requires content blocks")
    return "".join(
        str(block.get("text", ""))
        for block in blocks
        if isinstance(block, Mapping) and block.get("type") == "text"
    )


def run(
    argv: Optional[Sequence[str]] = None,
    *,
    client: Any = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        api = client or build_product_api_client()
        if args.list_models:
            models = [model.to_dict() for model in api.list_models()]
            print(json.dumps({"data": models}, separators=(",", ":")) if args.json_output else "\n".join(m["id"] for m in models), file=stdout)
            return int(ExitCode.OK)

        payload = _request_payload(args)
        if args.stream:
            output = ""
            terminal = None
            for event in api.stream_message(payload):
                if event.type is StreamEventType.CONTENT_DELTA:
                    text = str(event.data.get("text", ""))
                    output += text
                    if not args.quiet and not args.json_output:
                        print(text, end="", flush=True, file=stdout)
                if event.terminal:
                    terminal = event
            if terminal is None:
                raise ValueError("stream ended without a terminal event")
            if terminal.type is StreamEventType.STREAM_CANCELLED:
                return int(ExitCode.CANCELLED)
            if terminal.type is StreamEventType.STREAM_FAILED:
                print(str(terminal.data.get("message", "Product API stream failed")), file=stderr)
                return int(ExitCode.UNAVAILABLE if terminal.data.get("retryable") else ExitCode.PROTOCOL)
            if args.json_output:
                print(json.dumps({"text": output, "terminal": terminal.to_dict()}, separators=(",", ":")), file=stdout)
            elif not args.quiet:
                print(file=stdout)
            return int(ExitCode.OK)

        result = api.create_message(payload)
        if args.json_output:
            print(json.dumps(dict(result), separators=(",", ":")), file=stdout)
        elif not args.quiet:
            print(_assistant_text(result), file=stdout)
        return int(ExitCode.OK)
    except KeyboardInterrupt:
        return int(ExitCode.CANCELLED)
    except ProductAPIError as exc:
        print(exc.envelope.error.message, file=stderr)
        return int(_exit_for_error(exc))
    except (ValueError, RuntimeError) as exc:
        print(f"[ERROR] {exc}", file=stderr)
        return int(ExitCode.VALIDATION)


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
