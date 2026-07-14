"""Canonical typed Product API client foundation."""

from .api import ProductAPIClient
from .config import ClientConfig
from .retries import RetryPolicy
from .streaming import EventStreamParser, StreamProtocolError, parse_event_chunks
from .transport import ProductAPIError, ProductAPITransport, TransportResponse

__all__ = [
    "ClientConfig",
    "EventStreamParser",
    "ProductAPIClient",
    "ProductAPIError",
    "ProductAPITransport",
    "RetryPolicy",
    "StreamProtocolError",
    "TransportResponse",
    "parse_event_chunks",
]
