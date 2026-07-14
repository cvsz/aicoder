import json
from urllib.error import URLError

import pytest

from zaicoder.client import (
    ClientConfig,
    EventStreamParser,
    ProductAPIError,
    ProductAPITransport,
    RetryPolicy,
    StreamProtocolError,
    TransportResponse,
)
from zaicoder.domain import StreamEventType, StreamSequenceValidator


def test_client_config_normalizes_endpoint():
    config = ClientConfig(base_url="https://product.example/", api_version="v1")
    assert config.endpoint("models") == "https://product.example/v1/models"


def test_retry_policy_requires_safe_request():
    policy = RetryPolicy(max_retries=2)
    assert policy.should_retry(method="GET", attempt=0, status_code=503)
    assert not policy.should_retry(method="POST", attempt=0, status_code=503)
    assert policy.should_retry(
        method="POST", attempt=0, status_code=503, idempotency_key="idem-1"
    )
    assert not policy.should_retry(method="GET", attempt=0, status_code=401)
    assert not policy.should_retry(method="GET", attempt=2, status_code=503)


def test_transport_sets_product_headers_and_returns_json():
    captured = {}

    def sender(request, timeout):
        captured["headers"] = dict(request.header_items())
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return TransportResponse(200, {}, b'{"status":"ok"}')

    transport = ProductAPITransport(
        ClientConfig(base_url="https://product.example", access_token="product-token"),
        sender=sender,
    )
    result = transport.request_json("GET", "/health", correlation_id="corr-1")

    assert result == {"status": "ok"}
    assert captured["url"].endswith("/v1/health")
    headers = {key.lower(): value for key, value in captured["headers"].items()}
    assert headers["authorization"] == "Bearer product-token"
    assert headers["x-correlation-id"] == "corr-1"
    assert "x-request-id" in headers
    assert headers["x-api-version"] == "v1"


def test_transport_retries_connection_error_for_get():
    calls = []
    sleeps = []

    def sender(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise URLError("temporary")
        return TransportResponse(200, {}, b'{"ok":true}')

    transport = ProductAPITransport(
        ClientConfig(base_url="https://product.example", max_retries=1),
        sender=sender,
        sleeper=sleeps.append,
    )
    assert transport.request_json("GET", "/version") == {"ok": True}
    assert len(calls) == 2
    assert sleeps == [0.25]


def test_transport_raises_typed_product_error():
    body = json.dumps(
        {
            "error": {
                "code": "forbidden",
                "message": "denied",
                "request_id": "req-1",
                "correlation_id": "corr-1",
                "retryable": False,
                "details": {},
            }
        }
    ).encode()

    def sender(request, timeout):
        return TransportResponse(403, {}, body)

    transport = ProductAPITransport(
        ClientConfig(base_url="https://product.example"), sender=sender
    )
    with pytest.raises(ProductAPIError) as exc_info:
        transport.request_json("GET", "/models")
    assert exc_info.value.status_code == 403
    assert exc_info.value.envelope.error.code == "forbidden"


def _wire_event(event_type, sequence, payload=None):
    value = {
        "type": event_type,
        "sequence": sequence,
        "request_id": "req-1",
        "correlation_id": "corr-1",
        "payload": payload or {},
    }
    return f"data: {json.dumps(value)}\n\n".encode("utf-8")


def test_stream_parser_handles_fragmented_utf8_and_multiple_frames():
    wire = _wire_event("stream.started", 0) + _wire_event(
        "content.delta", 1, {"text": "สวัสดี"}
    ) + _wire_event("stream.completed", 2)
    parser = EventStreamParser()
    events = []
    for chunk in (wire[:17], wire[17:61], wire[61:93], wire[93:]):
        events.extend(parser.feed(chunk))
    events.extend(parser.finalize())

    assert [event.type for event in events] == [
        StreamEventType.STREAM_STARTED,
        StreamEventType.CONTENT_DELTA,
        StreamEventType.STREAM_COMPLETED,
    ]
    StreamSequenceValidator.validate(events)


def test_stream_parser_rejects_malformed_and_incomplete_frames():
    parser = EventStreamParser()
    with pytest.raises(StreamProtocolError, match="valid JSON"):
        parser.feed(b"data: not-json\n\n")

    parser = EventStreamParser()
    parser.feed(b'data: {"type":"stream.started"}')
    with pytest.raises(StreamProtocolError, match="incomplete"):
        parser.finalize()
