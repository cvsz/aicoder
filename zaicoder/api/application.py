"""Framework-independent Product API application for deterministic routing tests."""

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from zaicoder.domain import ErrorEnvelope, ModelDescriptor, ProductError
from zaicoder.providers import ProviderError
from zaicoder.services import ModelCatalogService


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
        model_catalog: Optional[ModelCatalogService] = None,
        ready: bool = True,
    ) -> None:
        self.product_version = product_version
        self.api_version = api_version.strip("/")
        self.models = tuple(models)
        self.model_catalog = model_catalog
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

        prefix = f"/{self.api_version}"
        if request.path == f"{prefix}/ready" and not self.ready:
            return self._error(503, "not_ready", "Service is not ready", request_id, correlation_id)

        routes = {
            f"{prefix}/health": lambda: {"status": "ok"},
            f"{prefix}/live": lambda: {"status": "ok"},
            f"{prefix}/ready": lambda: {"status": "ready"},
            f"{prefix}/version": lambda: {
                "product_version": self.product_version,
                "api_version": self.api_version,
            },
            f"{prefix}/models": self._models_payload,
        }
        handler = routes.get(request.path)
        if handler is None:
            return self._error(404, "not_found", "Route not found", request_id, correlation_id)
        try:
            payload = handler()
        except ProviderError as exc:
            return self._error(
                503 if exc.retryable else 502,
                exc.code.value,
                exc.message,
                request_id,
                correlation_id,
                retryable=exc.retryable,
            )
        except ValueError:
            return self._error(
                502,
                "provider_invalid_response",
                "Provider returned an invalid model catalog",
                request_id,
                correlation_id,
                retryable=False,
            )
        return ProductAPIResponse(200, headers, json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    def _models_payload(self) -> Mapping[str, Any]:
        models = self.model_catalog.list_models() if self.model_catalog is not None else self.models
        return {"data": [model.to_dict() for model in models]}

    def _error(
        self,
        status_code: int,
        code: str,
        message: str,
        request_id: str,
        correlation_id: str,
        *,
        retryable: Optional[bool] = None,
    ) -> ProductAPIResponse:
        envelope = ErrorEnvelope(
            ProductError(
                code=code,
                message=message,
                request_id=request_id,
                correlation_id=correlation_id,
                retryable=status_code >= 500 if retryable is None else retryable,
            )
        )
        return ProductAPIResponse(
            status_code,
            {
                "Content-Type": "application/json",
                "X-Request-ID": request_id,
                "X-Correlation-ID": correlation_id,
                "X-API-Version": self.api_version,
            },
            json.dumps(envelope.to_dict(), separators=(",", ":")).encode("utf-8"),
        )
