import pytest

from zaicoder.api import ProductAPIApplication, ProductAPIRequest
from zaicoder.providers import AnthropicProviderAdapter, ProviderError, ProviderErrorCode
from zaicoder.services import ModelCatalogService


def _app(lister):
    return ProductAPIApplication(
        product_version="1.23.0",
        model_catalog=ModelCatalogService(AnthropicProviderAdapter(lister)),
    )


def test_anthropic_adapter_maps_models_to_provider_neutral_contracts():
    app = _app(
        lambda: [
            {
                "id": "claude-test",
                "display_name": "Claude Test",
                "tools": True,
                "vision": True,
                "max_context_tokens": 200000,
            }
        ]
    )

    response = app.handle(ProductAPIRequest("GET", "/v1/models"))

    assert response.status_code == 200
    model = response.json()["data"][0]
    assert model["id"] == "claude-test"
    assert model["capabilities"]["tools"] is True
    assert model["metadata"] == {"provider": "anthropic"}
    assert "api_key" not in repr(response.json()).lower()


def test_model_catalog_is_sorted_and_rejects_duplicate_ids():
    service = ModelCatalogService(
        AnthropicProviderAdapter(
            lambda: [
                {"id": "model-z"},
                {"id": "model-a"},
            ]
        )
    )
    assert [model.id for model in service.list_models()] == ["model-a", "model-z"]

    duplicate = ModelCatalogService(
        AnthropicProviderAdapter(lambda: [{"id": "same"}, {"id": "same"}])
    )
    with pytest.raises(ValueError, match="unique"):
        duplicate.list_models()


def test_provider_timeout_becomes_retryable_typed_error():
    def timeout():
        raise TimeoutError("secret provider detail")

    response = _app(timeout).handle(
        ProductAPIRequest(
            "GET",
            "/v1/models",
            headers={"X-Request-ID": "req-1", "X-Correlation-ID": "corr-1"},
        )
    )

    error = response.json()["error"]
    assert response.status_code == 503
    assert error["code"] == "provider_unavailable"
    assert error["retryable"] is True
    assert error["request_id"] == "req-1"
    assert "secret provider detail" not in repr(error)


def test_provider_authentication_failure_is_non_retryable_and_redacted():
    def denied():
        raise PermissionError("bad-key-123")

    response = _app(denied).handle(ProductAPIRequest("GET", "/v1/models"))

    error = response.json()["error"]
    assert response.status_code == 502
    assert error["code"] == "provider_authentication_failed"
    assert error["retryable"] is False
    assert "bad-key-123" not in repr(error)


def test_invalid_provider_model_is_rejected_without_raw_payload_leakage():
    response = _app(lambda: [{"display_name": "missing id", "secret": "value"}]).handle(
        ProductAPIRequest("GET", "/v1/models")
    )

    error = response.json()["error"]
    assert response.status_code == 502
    assert error["code"] == ProviderErrorCode.INVALID_RESPONSE.value
    assert "secret" not in repr(error)


def test_custom_api_version_builds_dynamic_routes():
    app = ProductAPIApplication(product_version="1.23.0", api_version="v2")

    assert app.handle(ProductAPIRequest("GET", "/v2/health")).status_code == 200
    assert app.handle(ProductAPIRequest("GET", "/v1/health")).status_code == 404
