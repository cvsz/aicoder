"""Typed high-level Product API methods."""

from dataclasses import dataclass
from typing import Any, List, Mapping

from zaicoder.domain import ModelDescriptor

from .transport import ProductAPITransport


@dataclass
class ProductAPIClient:
    transport: ProductAPITransport

    def health(self) -> Mapping[str, Any]:
        return self.transport.request_json("GET", "/health")

    def readiness(self) -> Mapping[str, Any]:
        return self.transport.request_json("GET", "/ready")

    def version(self) -> Mapping[str, Any]:
        return self.transport.request_json("GET", "/version")

    def list_models(self) -> List[ModelDescriptor]:
        payload = self.transport.request_json("GET", "/models")
        data = payload.get("data") if isinstance(payload, Mapping) else None
        if not isinstance(data, list):
            raise ValueError("models response requires a data list")
        return [ModelDescriptor.from_dict(item) for item in data]
