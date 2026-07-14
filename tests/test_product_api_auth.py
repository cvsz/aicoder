from zaicoder.api import (
    AuthMiddleware,
    Principal,
    ProductAPIApplication,
    ProductAPIRequest,
    StaticTokenAuthenticator,
    TokenRecord,
)
from zaicoder.domain import ModelDescriptor


def _middleware():
    app = ProductAPIApplication(
        product_version="1.23.0",
        models=[ModelDescriptor(id="model-a", display_name="Model A")],
    )
    authenticator = StaticTokenAuthenticator(
        {
            "reader": TokenRecord(
                token="reader-token",
                principal=Principal(subject="user-1", scopes=frozenset({"models:read"})),
            ),
            "limited": TokenRecord(
                token="limited-token",
                principal=Principal(subject="user-2", scopes=frozenset()),
            ),
            "inactive": TokenRecord(
                token="inactive-token",
                principal=Principal(subject="user-3", scopes=frozenset({"models:read"})),
                active=False,
            ),
        }
    )
    return AuthMiddleware(app, authenticator)


def test_public_routes_do_not_require_token():
    response = _middleware().handle(ProductAPIRequest("GET", "/v1/health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_route_rejects_missing_token_with_typed_error():
    response = _middleware().handle(
        ProductAPIRequest(
            "GET",
            "/v1/models",
            headers={"X-Request-ID": "req-1", "X-Correlation-ID": "corr-1"},
        )
    )
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"].startswith("Bearer")
    assert response.json()["error"]["code"] == "unauthenticated"
    assert response.json()["error"]["request_id"] == "req-1"
    assert response.json()["error"]["correlation_id"] == "corr-1"
    assert response.json()["error"]["retryable"] is False


def test_invalid_and_inactive_tokens_are_rejected_identically():
    middleware = _middleware()
    for token in ("wrong-token", "inactive-token"):
        response = middleware.handle(
            ProductAPIRequest("GET", "/v1/models", headers={"Authorization": f"Bearer {token}"})
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthenticated"


def test_valid_token_without_scope_is_forbidden_without_leaking_granted_scopes():
    response = _middleware().handle(
        ProductAPIRequest(
            "GET",
            "/v1/models",
            headers={"Authorization": "Bearer limited-token"},
        )
    )
    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "forbidden"
    assert error["details"] == {"required_scopes": ["models:read"]}


def test_valid_scoped_token_reaches_provider_neutral_application():
    response = _middleware().handle(
        ProductAPIRequest(
            "GET",
            "/v1/models",
            headers={"Authorization": "Bearer reader-token"},
        )
    )
    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "model-a"
    assert "anthropic" not in repr(response.json()).lower()


def test_malformed_authorization_scheme_is_not_accepted():
    response = _middleware().handle(
        ProductAPIRequest("GET", "/v1/models", headers={"Authorization": "Basic reader-token"})
    )
    assert response.status_code == 401
