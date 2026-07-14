from zaicoder.api import (
    AuthPrincipal,
    ProductAPIApplication,
    ProductAPIAuthMiddleware,
    ProductAPIRequest,
    ProductAPIWSGI,
    ProductToken,
    StaticTokenValidator,
)


def _middleware():
    app = ProductAPIApplication(product_version="1.23.0")
    validator = StaticTokenValidator(
        [
            ProductToken(
                token="valid-token",
                principal=AuthPrincipal(
                    subject="user-1",
                    scopes=frozenset({"models:read"}),
                    organization_id="org-1",
                ),
            ),
            ProductToken(
                token="limited-token",
                principal=AuthPrincipal(subject="user-2"),
            ),
        ]
    )
    return ProductAPIAuthMiddleware(app, validator)


def test_public_route_does_not_require_token():
    response = _middleware().handle(ProductAPIRequest(method="GET", path="/v1/health"))
    assert response.status_code == 200


def test_private_route_requires_bearer_token():
    response = _middleware().handle(
        ProductAPIRequest(
            method="GET",
            path="/v1/models",
            headers={"X-Request-ID": "req-1", "X-Correlation-ID": "corr-1"},
        )
    )
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"].startswith("Bearer")
    assert response.json()["error"]["code"] == "authentication_required"
    assert response.json()["error"]["request_id"] == "req-1"


def test_invalid_token_is_rejected_without_leaking_token():
    response = _middleware().handle(
        ProductAPIRequest(
            method="GET",
            path="/v1/models",
            headers={"Authorization": "Bearer secret-invalid-token"},
        )
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"
    assert b"secret-invalid-token" not in response.body


def test_missing_scope_returns_typed_forbidden_error():
    response = _middleware().handle(
        ProductAPIRequest(
            method="GET",
            path="/v1/models",
            headers={"Authorization": "Bearer limited-token"},
        )
    )
    assert response.status_code == 403
    payload = response.json()["error"]
    assert payload["code"] == "insufficient_scope"
    assert payload["details"]["required_scopes"] == ["models:read"]
    assert payload["retryable"] is False


def test_authorized_scope_reaches_application():
    response = _middleware().handle(
        ProductAPIRequest(
            method="GET",
            path="/v1/models",
            headers={"Authorization": "Bearer valid-token"},
        )
    )
    assert response.status_code == 200
    assert response.json() == {"data": []}


def test_wsgi_preserves_401_status_and_challenge():
    statuses = []
    headers = []

    def start_response(status, response_headers):
        statuses.append(status)
        headers.extend(response_headers)

    body = b"".join(
        ProductAPIWSGI(_middleware())(
            {"REQUEST_METHOD": "GET", "PATH_INFO": "/v1/models"},
            start_response,
        )
    )
    assert statuses == ["401 Unauthorized"]
    assert ("WWW-Authenticate", 'Bearer realm="zaicoder-product-api"') in headers
    assert b"authentication_required" in body


def test_duplicate_tokens_are_rejected():
    principal = AuthPrincipal(subject="user-1")
    try:
        StaticTokenValidator(
            [ProductToken("duplicate", principal), ProductToken("duplicate", principal)]
        )
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate token should be rejected")
