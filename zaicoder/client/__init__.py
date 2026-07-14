"""Canonical typed Product API client foundation."""

from .api import ProductAPIClient
from .config import ClientConfig
from .live_stream import CancellationSignal, ProductAPIStreamTransport
from .retries import RetryPolicy
from .runtime import ProductAPIRuntimeConfig, build_product_api_client
from .streaming import EventStreamParser, StreamProtocolError, parse_event_chunks
from .transport import ProductAPIError, ProductAPITransport, TransportResponse

__all__ = [
    "CancellationSignal",
    "ClientConfig",
    "EventStreamParser",
    "ProductAPIClient",
    "ProductAPIError",
    "ProductAPIRuntimeConfig",
    "ProductAPIStreamTransport",
    "ProductAPITransport",
    "RetryPolicy",
    "StreamProtocolError",
    "TransportResponse",
    "build_product_api_client",
    "parse_event_chunks",
]
