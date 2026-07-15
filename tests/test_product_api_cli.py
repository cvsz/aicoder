import io

from zaicoder.cli import ExitCode, run
from zaicoder.domain import (
    ContentBlock,
    ContentType,
    Message,
    MessageRole,
    ModelCapabilities,
    ModelDescriptor,
    StreamEvent,
    StreamEventType,
)


class FakeClient:
    def __init__(self, *, response=None, events=None, models=None):
        self.response = response
        self.events = list(events or [])
        self.models = list(models or [])
        self.payloads = []

    def create_message(self, payload, **request_context):
        self.payloads.append(payload)
        self.request_context = request_context
        return self.response

    def stream_message(self, payload, **request_context):
        self.payloads.append(payload)
        self.request_context = request_context
        return iter(self.events)

    def list_models(self, **request_context):
        self.request_context = request_context
        return self.models


def event(kind, sequence, data=None):
    return StreamEvent(kind, sequence, "req", "corr", data or {})


def test_non_streaming_prompt_uses_product_api():
    client = FakeClient(
        response={
            "message": Message(
                MessageRole.ASSISTANT, [ContentBlock(ContentType.TEXT, text="hello")]
            ).to_dict()
        }
    )
    stdout = io.StringIO()
    assert run(["-p", "hi", "--model", "model-a"], client=client, stdout=stdout) == ExitCode.OK
    assert stdout.getvalue() == "hello\n"
    assert client.payloads[0]["model"] == "model-a"


def test_streaming_outputs_deltas_and_terminal_newline():
    client = FakeClient(
        events=[
            event(StreamEventType.STREAM_STARTED, 0),
            event(StreamEventType.CONTENT_DELTA, 1, {"text": "hel"}),
            event(StreamEventType.CONTENT_DELTA, 2, {"text": "lo"}),
            event(StreamEventType.STREAM_COMPLETED, 3),
        ]
    )
    stdout = io.StringIO()
    assert run(["-p", "hi", "--stream"], client=client, stdout=stdout) == ExitCode.OK
    assert stdout.getvalue() == "hello\n"


def test_cancelled_stream_returns_shell_interrupt_code():
    client = FakeClient(events=[event(StreamEventType.STREAM_CANCELLED, 0)])
    assert run(["-p", "hi", "--stream"], client=client) == ExitCode.CANCELLED


def test_json_output_is_machine_readable():
    client = FakeClient(response={"message": {"role": "assistant", "content": []}})
    stdout = io.StringIO()
    assert run(["-p", "hi", "--json"], client=client, stdout=stdout) == ExitCode.OK
    assert stdout.getvalue().strip() == '{"message":{"role":"assistant","content":[]}}'


def test_list_models_uses_product_catalog():
    client = FakeClient(models=[ModelDescriptor("model-a", "Model A", ModelCapabilities())])
    stdout = io.StringIO()
    assert run(["--list-models"], client=client, stdout=stdout) == ExitCode.OK
    assert stdout.getvalue() == "model-a\n"


def test_cli_forwards_explicit_request_and_correlation_ids():
    client = FakeClient(response={"message": {"role": "assistant", "content": []}})

    assert (
        run(["-p", "hi", "--request-id", "req-cli", "--correlation-id", "corr-cli"], client=client)
        == ExitCode.OK
    )

    assert client.request_context == {"request_id": "req-cli", "correlation_id": "corr-cli"}


def test_debug_diagnostics_redact_product_access_token():
    client = FakeClient(response={"message": {"role": "assistant", "content": []}})
    stderr = io.StringIO()

    assert run(["-p", "hi", "--debug"], client=client, stderr=stderr) == ExitCode.OK

    assert "request_id=" in stderr.getvalue()
    assert "correlation_id=" in stderr.getvalue()
    assert "token" not in stderr.getvalue().lower()


def test_missing_prompt_is_validation_error():
    stderr = io.StringIO()
    assert run([], client=FakeClient(), stderr=stderr) == ExitCode.VALIDATION
    assert "--prompt is required" in stderr.getvalue()


def test_invalid_runtime_overrides_are_validation_errors():
    stderr = io.StringIO()

    assert run(["-p", "hi", "--api-timeout", "0"], client=FakeClient(), stderr=stderr) == ExitCode.VALIDATION
    assert "--api-timeout must be positive" in stderr.getvalue()

    stderr = io.StringIO()
    assert (
        run(["-p", "hi", "--api-max-retries", "-1"], client=FakeClient(), stderr=stderr)
        == ExitCode.VALIDATION
    )
    assert "--api-max-retries must be non-negative" in stderr.getvalue()


def test_cli_source_has_no_provider_credential_or_sdk_import():
    from pathlib import Path

    source = Path("zaicoder/cli.py").read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY" not in source
    assert "import anthropic" not in source
    assert "from coder import" not in source
