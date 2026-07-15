import io
from pathlib import Path

from zaicoder.domain import ModelCapabilities, ModelDescriptor
from zaicoder.main_cli import MainCLIExitCode, run_model_listing


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
