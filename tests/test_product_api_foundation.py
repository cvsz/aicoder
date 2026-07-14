from urllib.parse import urlsplit

import pytest

from zaicoder.api import ProductAPIApplication, ProductAPIRequest
from zaicoder.client import ClientConfig, ProductAPIClient, ProductAPIError, ProductAPITransport, TransportResponse
from zaicoder.domain import ModelCapabilities, ModelDescriptor


def _sender_for(app):
    def sender(request, timeout):
        del timeout
        parsed = urlsplit(request.full_url)
        response = app.handle(
            ProductAPIRequest(
                method=request.get_method(),
                path=parsed.path,
                headers=dict(request.header_items()),
            )
        )
        return TransportResponse(response.status_code, response.headers, response.body)

    return sender


def _client(app):
    config = ClientConfig(base_url="https://product.invalid", api_version="v1")
    return ProductAPIClient(ProductAPITransport(config, sender=_sender_for(app)))


def test_health_version_and_models_work_end_to_end():
    model = ModelDescriptor(
        id="model-a",
        display_name="Model A",
        capabilities=ModelCapabilities(streaming=True, tools=True, max_context_tokens=1000),
    )
    client = _client(ProductAPIApplication(product_version="1.23.0", models=[model]))

    assert client.health() == {"status": "ok"}
    assert client.version() == {"product_version": "1.23.0", "api_version": "v1"}
    assert client.list_models() == [model]


def test_readiness_failure_uses_typed_error_envelope():
    client = _client(ProductAPIApplication(product_version="1.23.0", ready=False))

    with pytest.raises(ProductAPIError) as exc_info:
        client.readiness()

    assert exc_info.value.status_code == 503
    assert exc_info.value.envelope.error.code == "not_ready"
    assert exc_info.value.envelope.error.retryable is True


def test_unknown_route_preserves_request_and_correlation_ids():
    app = ProductAPIApplication(product_version="1.23.0")
    response = app.handle(
        ProductAPIRequest(
            method="GET",
            path="/v1/missing",
            headers={"X-Request-ID": "req-1", "X-Correlation-ID": "corr-1"},
        )
    )

    payload = response.json()
    assert response.status_code == 404
    assert payload["error"]["request_id"] == "req-1"
    assert payload["error"]["correlation_id"] == "corr-1"


def test_non_get_route_is_rejected():
    app = ProductAPIApplication(product_version="1.23.0")
    response = app.handle(ProductAPIRequest(method="POST", path="/v1/health"))

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
