import json
from pathlib import Path

from zaicoder.api import ProductAPIApplication, ProductAPIWSGI, build_openapi_schema


def _call_wsgi(app, *, method="GET", path="/v1/health", headers=None):
    captured = {}

    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = dict(response_headers)

    environ = {"REQUEST_METHOD": method, "PATH_INFO": path}
    for name, value in (headers or {}).items():
        environ["HTTP_" + name.upper().replace("-", "_")] = value
    body = b"".join(app(environ, start_response))
    return captured, json.loads(body.decode("utf-8"))


def test_wsgi_adapter_propagates_request_context():
    app = ProductAPIWSGI(ProductAPIApplication(product_version="1.23.0"))
    captured, payload = _call_wsgi(
        app,
        headers={"X-Request-ID": "req-1", "X-Correlation-ID": "corr-1"},
    )

    assert captured["status"] == "200 OK"
    assert captured["headers"]["X-Request-ID"] == "req-1"
    assert captured["headers"]["X-Correlation-ID"] == "corr-1"
    assert int(captured["headers"]["Content-Length"]) > 0
    assert payload == {"status": "ok"}


def test_wsgi_adapter_preserves_typed_errors():
    app = ProductAPIWSGI(ProductAPIApplication(product_version="1.23.0", ready=False))
    captured, payload = _call_wsgi(app, path="/v1/ready")

    assert captured["status"] == "503 Service Unavailable"
    assert payload["error"]["code"] == "not_ready"
    assert payload["error"]["retryable"] is True


def test_checked_in_openapi_matches_generator():
    checked_in = json.loads(Path("docs/api/openapi.json").read_text(encoding="utf-8"))
    assert checked_in == build_openapi_schema("1.23.0")


def test_openapi_contains_all_versioned_product_routes():
    schema = build_openapi_schema()
    assert set(schema["paths"]) == {
        "/v1/health",
        "/v1/live",
        "/v1/ready",
        "/v1/version",
        "/v1/models",
        "/v1/messages",
        "/v1/messages:stream",
    }
    assert schema["components"]["schemas"]["ProductError"]["required"] == ["error"]
