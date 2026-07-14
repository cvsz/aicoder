"""Framework-independent Product API application for deterministic routing tests."""

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from zaicoder.domain import ErrorEnvelope, Message, ModelDescriptor, ProductError, StreamEventType
from zaicoder.providers import GenerationRequest, ProviderError
from zaicoder.services import GenerationService, ModelCatalogService


@dataclass(frozen=True)
class ProductAPIRequest:
    method: str
    path: str
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8")) if self.body else None


@dataclass(frozen=True)
class ProductAPIResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


class ProductAPIApplication:
    """Versioned provider-neutral Product API application boundary."""

    def __init__(
        self,
        *,
        product_version: str,
        api_version: str = "v1",
        models: Sequence[ModelDescriptor] = (),
        model_catalog: Optional[ModelCatalogService] = None,
        generation: Optional[GenerationService] = None,
        ready: bool = True,
    ) -> None:
        self.product_version = product_version
        self.api_version = api_version.strip("/")
        self.models = tuple(models)
        self.model_catalog = model_catalog
        self.generation = generation
        self.ready = ready

    def handle(self, request: ProductAPIRequest) -> ProductAPIResponse:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        correlation_id = request.headers.get("X-Correlation-ID") or request_id
        headers = self._headers(request_id, correlation_id)
        prefix = f"/{self.api_version}"

        if request.path == f"{prefix}/ready" and not self.ready:
            return self._error(503, "not_ready", "Service is not ready", request_id, correlation_id)

        if request.method.upper() == "GET":
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
                return self._provider_error(exc, request_id, correlation_id)
            except ValueError:
                return self._error(502, "provider_invalid_response", "Provider returned an invalid model catalog", request_id, correlation_id, retryable=False)
            return ProductAPIResponse(200, headers, self._json_bytes(payload))

        if request.method.upper() == "POST" and request.path in {
            f"{prefix}/messages",
            f"{prefix}/messages:stream",
        }:
            if self.generation is None:
                return self._error(503, "generation_unavailable", "Generation service is unavailable", request_id, correlation_id)
            try:
                generation_request = self._generation_request(request)
            except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                return self._error(422, "validation_error", "Invalid generation request", request_id, correlation_id, retryable=False)
            events = list(
                self.generation.stream(
                    generation_request,
                    request_id=request_id,
                    correlation_id=correlation_id,
                )
            )
            if request.path.endswith(":stream"):
                stream_headers = dict(headers)
                stream_headers["Content-Type"] = "text/event-stream"
                body = b"".join(
                    f"event: {event.type.value}\ndata: {json.dumps(event.to_dict(), separators=(',', ':'))}\n\n".encode("utf-8")
                    for event in events
                )
                return ProductAPIResponse(200, stream_headers, body)
            failed = next((event for event in events if event.type is StreamEventType.STREAM_FAILED), None)
            if failed is not None:
                data = failed.data
                return self._error(
                    503 if data.get("retryable") else 502,
                    str(data.get("code", "provider_unavailable")),
                    str(data.get("message", "Provider generation failed")),
                    request_id,
                    correlation_id,
                    retryable=bool(data.get("retryable")),
                )
            text = "".join(str(event.data.get("text", "")) for event in events if event.type is StreamEventType.CONTENT_DELTA)
            completed = next((event for event in events if event.type is StreamEventType.MESSAGE_COMPLETED), None)
            if completed is None:
                return self._error(502, "provider_invalid_response", "Generation did not complete", request_id, correlation_id, retryable=False)
            return ProductAPIResponse(
                200,
                headers,
                self._json_bytes({"message": {"role": "assistant", "content": [{"type": "text", "text": text}]}, **completed.data}),
            )

        if request.path.startswith(prefix):
            return self._error(405, "method_not_allowed", "Method not allowed", request_id, correlation_id)
        return self._error(404, "not_found", "Route not found", request_id, correlation_id)

    def _generation_request(self, request: ProductAPIRequest) -> GenerationRequest:
        payload = request.json()
        if not isinstance(payload, Mapping):
            raise ValueError("request body must be an object")
        raw_messages = payload.get("messages")
        if not isinstance(raw_messages, list):
            raise ValueError("messages must be a list")
        return GenerationRequest(
            model=str(payload["model"]),
            messages=[Message.from_dict(item) for item in raw_messages],
            max_output_tokens=int(payload.get("max_output_tokens", 1024)),
            metadata=dict(payload.get("metadata", {})),
        )

    def _models_payload(self) -> Mapping[str, Any]:
        models = self.model_catalog.list_models() if self.model_catalog is not None else self.models
        return {"data": [model.to_dict() for model in models]}

    def _provider_error(self, exc: ProviderError, request_id: str, correlation_id: str) -> ProductAPIResponse:
        return self._error(503 if exc.retryable else 502, exc.code.value, exc.message, request_id, correlation_id, retryable=exc.retryable)

    def _headers(self, request_id: str, correlation_id: str) -> Mapping[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
            "X-Correlation-ID": correlation_id,
            "X-API-Version": self.api_version,
        }

    @staticmethod
    def _json_bytes(payload: Mapping[str, Any]) -> bytes:
        return json.dumps(payload, separators=(",", ":")).encode("utf-8")

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
        return ProductAPIResponse(status_code, self._headers(request_id, correlation_id), self._json_bytes(envelope.to_dict()))
