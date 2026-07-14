"""Authentication and authorization middleware for the Product API."""

from __future__ import annotations

import hmac
import json
import uuid
from dataclasses import dataclass
from typing import Dict, FrozenSet, Mapping, Optional, Protocol

from zaicoder.domain import ErrorEnvelope, ProductError

from .application import ProductAPIRequest, ProductAPIResponse


class ProductAPIHandler(Protocol):
    def handle(self, request: ProductAPIRequest) -> ProductAPIResponse:
        ...


@dataclass(frozen=True)
class Principal:
    subject: str
    scopes: FrozenSet[str]
    organization_id: Optional[str] = None
    workspace_id: Optional[str] = None


@dataclass(frozen=True)
class TokenRecord:
    token: str
    principal: Principal
    active: bool = True


class StaticTokenAuthenticator:
    """Deterministic token authenticator suitable for tests and local deployment."""

    def __init__(self, records: Mapping[str, TokenRecord]) -> None:
        self._records = tuple(records.values())

    def authenticate(self, authorization: Optional[str]) -> Optional[Principal]:
        if not authorization or not authorization.startswith("Bearer "):
            return None
        candidate = authorization[7:]
        for record in self._records:
            if hmac.compare_digest(candidate, record.token):
                return record.principal if record.active else None
        return None


class AuthMiddleware:
    """Enforce public/private route policy before dispatching to the application."""

    PUBLIC_PATHS = frozenset({"/v1/health", "/v1/live", "/v1/ready", "/v1/version"})
    REQUIRED_SCOPES: Mapping[str, FrozenSet[str]] = {"/v1/models": frozenset({"models:read"})}

    def __init__(self, app: ProductAPIHandler, authenticator: StaticTokenAuthenticator) -> None:
        self.app = app
        self.authenticator = authenticator

    def handle(self, request: ProductAPIRequest) -> ProductAPIResponse:
        if request.path in self.PUBLIC_PATHS:
            return self.app.handle(request)

        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        correlation_id = request.headers.get("X-Correlation-ID") or request_id
        principal = self.authenticator.authenticate(request.headers.get("Authorization"))
        if principal is None:
            return self._error(
                401,
                "unauthenticated",
                "A valid bearer token is required",
                request_id,
                correlation_id,
                www_authenticate=True,
            )

        required = self.REQUIRED_SCOPES.get(request.path, frozenset())
        missing = required.difference(principal.scopes)
        if missing:
            return self._error(
                403,
                "forbidden",
                "The authenticated principal lacks required permissions",
                request_id,
                correlation_id,
                details={"required_scopes": sorted(required)},
            )
        return self.app.handle(request)

    @staticmethod
    def _error(
        status_code: int,
        code: str,
        message: str,
        request_id: str,
        correlation_id: str,
        *,
        details: Optional[Mapping[str, object]] = None,
        www_authenticate: bool = False,
    ) -> ProductAPIResponse:
        envelope = ErrorEnvelope(
            ProductError(
                code=code,
                message=message,
                request_id=request_id,
                correlation_id=correlation_id,
                retryable=False,
                details=details or {},
            )
        )
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
            "X-Correlation-ID": correlation_id,
            "X-API-Version": "v1",
        }
        if www_authenticate:
            headers["WWW-Authenticate"] = 'Bearer realm="zaicoder-product-api"'
        return ProductAPIResponse(
            status_code,
            headers,
            json.dumps(envelope.to_dict(), separators=(",", ":")).encode("utf-8"),
        )
