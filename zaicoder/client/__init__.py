"""Canonical typed Product API client foundation."""

from .api import ProductAPIClient
from .config import ClientConfig
from .live_stream import CancellationSignal, ProductAPIStreamTransport
from .retries import RetryPolicy
from .streaming import EventStreamParser, StreamProtocolError, parse_event_chunks
from .transport import ProductAPIError, ProductAPITransport, TransportResponse

__all__ = [
    "CancellationSignal",
    "ClientConfig",
    "EventStreamParser",
    "ProductAPIClient",
    "ProductAPIError",
    "ProductAPIStreamTransport",
    "ProductAPITransport",
    "RetryPolicy",
    "StreamProtocolError",
    "TransportResponse",
    "parse_event_chunks",
]
