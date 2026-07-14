"""Authentication and authorization middleware for the Product API."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Mapping, Optional, Protocol, Sequence

from zaicoder.domain import ErrorEnvelope, ProductError

from .application import ProductAPIRequest, ProductAPIResponse


class ProductAPIHandler(Protocol):
    def handle(self, request: ProductAPIRequest) -> ProductAPIResponse:
        ...


@dataclass(frozen=True)
class AuthPrincipal:
    subject: str
    scopes: FrozenSet[str] = field(default_factory=frozenset)
    organization_id: Optional[str] = None
    workspace_ids: FrozenSet[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ProductToken:
    token: str
    principal: AuthPrincipal

    def __post_init__(self) -> None:
        if not self.token.strip():
            raise ValueError("product token must not be empty")
        if not self.principal.subject.strip():
            raise ValueError("principal subject must not be empty")


class StaticTokenValidator:
    """Deterministic token validator that stores only SHA-256 token digests."""

    def __init__(self, tokens: Sequence[ProductToken]) -> None:
        self._principals: Dict[str, AuthPrincipal] = {}
        for item in tokens:
            digest = self._digest(item.token)
            if digest in self._principals:
                raise ValueError("duplicate product token")
            self._principals[digest] = item.principal

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def validate(self, token: str) -> Optional[AuthPrincipal]:
        candidate = self._digest(token)
        for digest, principal in self._principals.items():
            if hmac.compare_digest(candidate, digest):
                return principal
        return None


@dataclass(frozen=True)
class RoutePolicy:
    public_paths: FrozenSet[str] = frozenset(
        {"/v1/health", "/v1/live", "/v1/ready", "/v1/version"}
    )
    required_scopes: Mapping[str, FrozenSet[str]] = field(
        default_factory=lambda: {"/v1/models": frozenset({"models:read"})}
    )

    def scopes_for(self, path: str) -> FrozenSet[str]:
        return self.required_scopes.get(path, frozenset())


class ProductAPIAuthMiddleware:
    """Enforce bearer-token authentication and route-level scopes."""

    def __init__(
        self,
        application: ProductAPIHandler,
        validator: StaticTokenValidator,
        *,
        policy: Optional[RoutePolicy] = None,
    ) -> None:
        self.application = application
        self.validator = validator
        self.policy = policy or RoutePolicy()

    def handle(self, request: ProductAPIRequest) -> ProductAPIResponse:
        if request.path in self.policy.public_paths:
            return self.application.handle(request)

        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        correlation_id = request.headers.get("X-Correlation-ID") or request_id
        authorization = request.headers.get("Authorization", "")
        scheme, separator, token = authorization.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            return self._error(
                401,
                "authentication_required",
                "A valid bearer token is required",
                request_id,
                correlation_id,
                authenticate=True,
            )

        principal = self.validator.validate(token.strip())
        if principal is None:
            return self._error(
                401,
                "invalid_token",
                "The bearer token is invalid",
                request_id,
                correlation_id,
                authenticate=True,
            )

        required = self.policy.scopes_for(request.path)
        missing = required.difference(principal.scopes)
        if missing:
            return self._error(
                403,
                "insufficient_scope",
                "The bearer token lacks required permissions",
                request_id,
                correlation_id,
                details={"required_scopes": sorted(required)},
            )
        return self.application.handle(request)

    @staticmethod
    def _error(
        status_code: int,
        code: str,
        message: str,
        request_id: str,
        correlation_id: str,
        *,
        authenticate: bool = False,
        details: Optional[Mapping[str, object]] = None,
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
        headers = {
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
            "X-Correlation-ID": correlation_id,
            "X-API-Version": "v1",
        }
        if authenticate:
            headers["WWW-Authenticate"] = 'Bearer realm="zaicoder-product-api"'
        return ProductAPIResponse(
            status_code=status_code,
            headers=headers,
            body=json.dumps(envelope.to_dict(), separators=(",", ":")).encode("utf-8"),
        )
