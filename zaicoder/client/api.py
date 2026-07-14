"""Typed high-level Product API methods."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Optional

from zaicoder.domain import ModelDescriptor, StreamEvent

from .live_stream import CancellationSignal, ProductAPIStreamTransport
from .transport import ProductAPITransport


@dataclass
class ProductAPIClient:
    transport: ProductAPITransport
    stream_transport: Optional[ProductAPIStreamTransport] = None

    def health(self) -> Mapping[str, Any]:
        return self.transport.request_json("GET", "/health")

    def readiness(self) -> Mapping[str, Any]:
        return self.transport.request_json("GET", "/ready")

    def version(self) -> Mapping[str, Any]:
        return self.transport.request_json("GET", "/version")

    def list_models(
        self,
        *,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> list[ModelDescriptor]:
        payload = self.transport.request_json(
            "GET", "/models", request_id=request_id, correlation_id=correlation_id
        )
        data = payload.get("data") if isinstance(payload, Mapping) else None
        if not isinstance(data, list):
            raise ValueError("models response requires a data list")
        return [ModelDescriptor.from_dict(item) for item in data]

    def create_message(
        self,
        payload: Mapping[str, Any],
        *,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Mapping[str, Any]:
        result = self.transport.request_json(
            "POST",
            "/messages",
            payload=payload,
            request_id=request_id,
            correlation_id=correlation_id,
        )
        if not isinstance(result, Mapping):
            raise ValueError("message response must be an object")
        return result

    def stream_message(
        self,
        payload: Mapping[str, object],
        *,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        cancellation: Optional[CancellationSignal] = None,
    ) -> Iterator[StreamEvent]:
        if self.stream_transport is None:
            raise RuntimeError("stream transport is not configured")
        return self.stream_transport.stream_events(
            "/messages:stream",
            payload,
            request_id=request_id,
            correlation_id=correlation_id,
            cancellation=cancellation,
        )
