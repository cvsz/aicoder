"""Runtime construction for client-facing Product API surfaces."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional

from .api import ProductAPIClient
from .config import ClientConfig
from .live_stream import ProductAPIStreamTransport
from .transport import ProductAPITransport


@dataclass(frozen=True)
class ProductAPIRuntimeConfig:
    base_url: str
    access_token: str
    api_version: str = "v1"
    timeout_seconds: float = 30.0
    max_retries: int = 3

    @classmethod
    def from_environment(cls, environ: Optional[Mapping[str, str]] = None) -> "ProductAPIRuntimeConfig":
        source = os.environ if environ is None else environ
        base_url = source.get("ZAICODER_API_URL", "").strip()
        access_token = source.get("ZAICODER_ACCESS_TOKEN", "").strip()
        if not base_url:
            raise ValueError("ZAICODER_API_URL is required")
        if not access_token:
            raise ValueError("ZAICODER_ACCESS_TOKEN is required")
        return cls(
            base_url=base_url,
            access_token=access_token,
            api_version=source.get("ZAICODER_API_VERSION", "v1").strip() or "v1",
            timeout_seconds=float(source.get("ZAICODER_API_TIMEOUT", "30")),
            max_retries=int(source.get("ZAICODER_API_MAX_RETRIES", "3")),
        )

    def client_config(self) -> ClientConfig:
        return ClientConfig(
            base_url=self.base_url,
            access_token=self.access_token,
            api_version=self.api_version,
            timeout_seconds=self.timeout_seconds,
            max_retries=self.max_retries,
            user_agent="zaicoder-tui/1",
        )


def build_product_api_client(runtime: Optional[ProductAPIRuntimeConfig] = None) -> ProductAPIClient:
    resolved = runtime or ProductAPIRuntimeConfig.from_environment()
    config = resolved.client_config()
    return ProductAPIClient(
        ProductAPITransport(config),
        stream_transport=ProductAPIStreamTransport(config),
    )
