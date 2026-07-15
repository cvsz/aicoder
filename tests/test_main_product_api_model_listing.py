import io
from pathlib import Path

from zaicoder.domain import ModelCapabilities, ModelDescriptor, StreamEvent, StreamEventType
from zaicoder.main_cli import MainCLIExitCode, run_model_listing, run_prompt, run_stream


class FakeClient:
    def __init__(self):
        self.request_context = None

    def list_models(self, **request_context):
        self.request_context = request_context
        return [
            ModelDescriptor(
                "model-a",
                "Model A",
                ModelCapabilities(max_context_tokens=200_000),
            )
        ]

    def create_message(self, payload, **request_context):
        self.payload = payload
        self.request_context = request_context
        return {"message": {"content": [{"type": "text", "text": "hello"}]}}

    def stream_message(self, payload, **request_context):
        self.payload = payload
        self.request_context = request_context
        return iter(
            [
                StreamEvent(StreamEventType.CONTENT_DELTA, 0, "req", "corr", {"text": "hel"}),
                StreamEvent(StreamEventType.CONTENT_DELTA, 1, "req", "corr", {"text": "lo"}),
                StreamEvent(StreamEventType.STREAM_COMPLETED, 2, "req", "corr"),
            ]
        )


def test_main_model_listing_uses_product_api_and_legacy_layout():
    client = FakeClient()
    stdout = io.StringIO()

    result = run_model_listing(
        client=client,
        stdout=stdout,
        request_id="req-main",
        correlation_id="corr-main",
    )

    assert result == MainCLIExitCode.OK
    assert "MODEL ID" in stdout.getvalue()
    assert "model-a" in stdout.getvalue()
    assert "200K" in stdout.getvalue()
    assert client.request_context == {"request_id": "req-main", "correlation_id": "corr-main"}


def test_main_simple_prompt_uses_product_api_and_preserves_output_file(tmp_path):
    client = FakeClient()
    stdout = io.StringIO()
    output = tmp_path / "answer.txt"

    result = run_prompt(
        "hi",
        model="model-a",
        max_tokens=99,
        output_path=str(output),
        client=client,
        stdout=stdout,
        request_id="req-prompt",
        correlation_id="corr-prompt",
    )

    assert result == MainCLIExitCode.OK
    assert stdout.getvalue() == "hello\n"
    assert output.read_text(encoding="utf-8") == "hello"
    assert client.payload == {
        "model": "model-a",
        "max_output_tokens": 99,
        "messages": [{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
    }
    assert client.request_context == {"request_id": "req-prompt", "correlation_id": "corr-prompt"}


def test_main_simple_stream_uses_product_api_events_and_final_newline():
    client = FakeClient()
    stdout = io.StringIO()

    result = run_stream(
        "hi",
        model="model-a",
        max_tokens=99,
        client=client,
        stdout=stdout,
        request_id="req-stream",
        correlation_id="corr-stream",
    )

    assert result == MainCLIExitCode.OK
    assert stdout.getvalue() == "hello\n"
    assert client.payload["model"] == "model-a"
    assert client.request_context == {"request_id": "req-stream", "correlation_id": "corr-stream"}


def test_main_product_api_debug_reports_only_request_metadata():
    client = FakeClient()
    stderr = io.StringIO()

    result = run_prompt(
        "hi",
        model="model-a",
        max_tokens=99,
        client=client,
        stderr=stderr,
        request_id="req-debug",
        correlation_id="corr-debug",
        debug=True,
    )

    assert result == MainCLIExitCode.OK
    assert stderr.getvalue() == "[DEBUG] Product API request_id=req-debug correlation_id=corr-debug\n"
    assert "token" not in stderr.getvalue().lower()


def test_migrated_main_adapter_has_no_provider_credentials_or_sdk_imports():
    source = Path("zaicoder/main_cli.py").read_text(encoding="utf-8")

    assert "ANTHROPIC_API_KEY" not in source
    assert "import anthropic" not in source
    assert "from coder import" not in source


def test_main_dispatches_default_model_listing_before_legacy_key_resolution():
    source = Path("main.py").read_text(encoding="utf-8")

    dispatch = source.index("if args.list_models and not args.list_models_legacy:")
    legacy_key = source.index("key   = _api_key(args)")
    assert dispatch < legacy_key


def test_main_dispatches_simple_prompt_before_legacy_key_resolution():
    source = Path("main.py").read_text(encoding="utf-8")

    dispatch = source.index("if _is_simple_product_api_prompt(sys.argv[1:]):")
    legacy_key = source.index("key   = _api_key(args)")
    assert dispatch < legacy_key


def test_main_dispatches_simple_stream_before_legacy_key_resolution():
    source = Path("main.py").read_text(encoding="utf-8")

    dispatch = source.index("if _is_simple_product_api_stream(sys.argv[1:]):")
    legacy_key = source.index("key   = _api_key(args)")
    assert dispatch < legacy_key
