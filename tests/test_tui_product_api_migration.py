import ast
from pathlib import Path

import pytest

from zaicoder.client.runtime import ProductAPIRuntimeConfig


def test_runtime_config_requires_product_api_url_and_token():
    with pytest.raises(ValueError, match="ZAICODER_API_URL"):
        ProductAPIRuntimeConfig.from_environment({})
    with pytest.raises(ValueError, match="ZAICODER_ACCESS_TOKEN"):
        ProductAPIRuntimeConfig.from_environment({"ZAICODER_API_URL": "https://api.example"})


def test_runtime_config_builds_client_configuration():
    runtime = ProductAPIRuntimeConfig.from_environment(
        {
            "ZAICODER_API_URL": "https://api.example/",
            "ZAICODER_ACCESS_TOKEN": "product-token",
            "ZAICODER_API_VERSION": "v1",
            "ZAICODER_API_TIMEOUT": "12",
            "ZAICODER_API_MAX_RETRIES": "2",
        }
    )
    config = runtime.client_config()
    assert config.base_url == "https://api.example"
    assert config.access_token == "product-token"
    assert config.timeout_seconds == 12
    assert config.max_retries == 2


def test_tui_has_no_provider_sdk_or_provider_key_dependency():
    source = Path("tui.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert "anthropic" not in imported
    assert "ANTHROPIC_API_KEY" not in source
    assert "from coder import Coder" not in source
    assert "build_product_api_client" in source
    assert ".stream_message(" in source
    assert ".create_message(" in source


def test_legacy_tui_entrypoint_does_not_forward_provider_key():
    source = Path("tui.py").read_text(encoding="utf-8")
    assert "del api_key" in source
    assert "ZCoderTUI(client=client).run()" in source
