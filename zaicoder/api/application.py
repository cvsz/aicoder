"""Framework-independent Product API application for deterministic routing tests."""

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

from zaicoder.domain import ErrorEnvelope, ModelDescriptor, ProductError


@dataclass(frozen=True)
class ProductAPIRequest:
    method: str
    path: str
    headers: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProductAPIResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


class ProductAPIApplication:
    """Minimal versioned application boundary with provider-neutral schemas."""

    def __init__(
        self,
        *,
        product_version: str,
        api_version: str = "v1",
        models: Sequence[ModelDescriptor] = (),
        ready: bool = True,
    ) -> None:
        self.product_version = product_version
        self.api_version = api_version
        self.models = tuple(models)
        self.ready = ready

    def handle(self, request: ProductAPIRequest) -> ProductAPIResponse:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        correlation_id = request.headers.get("X-Correlation-ID") or request_id
        headers = {
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
            "X-Correlation-ID": correlation_id,
            "X-API-Version": self.api_version,
        }
        if request.method.upper() != "GET":
            return self._error(405, "method_not_allowed", "Method not allowed", request_id, correlation_id)

        routes = {
            "/v1/health": lambda: {"status": "ok"},
            "/v1/live": lambda: {"status": "ok"},
            "/v1/ready": lambda: {"status": "ready" if self.ready else "not_ready"},
            "/v1/version": lambda: {
                "product_version": self.product_version,
                "api_version": self.api_version,
            },
            "/v1/models": lambda: {"data": [model.to_dict() for model in self.models]},
        }
        handler = routes.get(request.path)
        if handler is None:
            return self._error(404, "not_found", "Route not found", request_id, correlation_id)
        payload = handler()
        status = 200
        if request.path == "/v1/ready" and not self.ready:
            status = 503
        return ProductAPIResponse(status, headers, json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    @staticmethod
    def _error(
        status_code: int,
        code: str,
        message: str,
        request_id: str,
        correlation_id: str,
    ) -> ProductAPIResponse:
        envelope = ErrorEnvelope(
            ProductError(
                code=code,
                message=message,
                request_id=request_id,
                correlation_id=correlation_id,
                retryable=status_code >= 500,
            )
        )
        return ProductAPIResponse(
            status_code,
            {
                "Content-Type": "application/json",
                "X-Request-ID": request_id,
                "X-Correlation-ID": correlation_id,
                "X-API-Version": "v1",
            },
            json.dumps(envelope.to_dict(), separators=(",", ":")).encode("utf-8"),
        )
