import json

from zaicoder.client import ClientConfig, ProductAPIClient, ProductAPIStreamTransport, ProductAPITransport
from zaicoder.domain import ContentBlock, ContentType, Message, MessageRole, StreamEventType
from zaicoder.providers import AnthropicGenerationAdapter, GenerationRequest


class Flag:
    cancelled = False


class FakeHandle:
    status = 200
    headers = {"Content-Type": "text/event-stream"}

    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.closed = False

    def read(self, size=-1):
        del size
        return self.chunks.pop(0) if self.chunks else b""

    def close(self):
        self.closed = True


def _generation_request():
    return GenerationRequest(
        model="claude-test",
        messages=[Message(MessageRole.USER, [ContentBlock(ContentType.TEXT, text="hello")])],
    )


def test_anthropic_adapter_maps_text_usage_and_completion():
    captured = {}

    def streamer(payload):
        captured.update(payload)
        yield {"type": "content_block_delta", "delta": {"text": "hel"}}
        yield {"type": "content_block_delta", "delta": {"text": "lo"}}
        yield {
            "type": "message_stop",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 2, "output_tokens": 1},
        }

    deltas = list(AnthropicGenerationAdapter(streamer).stream(_generation_request(), Flag()))
    assert captured["stream"] is True
    assert captured["model"] == "claude-test"
    assert "hello" in repr(captured["messages"])
    assert "".join(delta.text or "" for delta in deltas) == "hello"
    assert deltas[-1].completed is True
    assert deltas[-1].usage.output_tokens == 1


def test_anthropic_adapter_stops_reading_after_cancellation():
    flag = Flag()

    def streamer(payload):
        del payload
        yield {"type": "content_block_delta", "delta": {"text": "first"}}
        flag.cancelled = True
        yield {"type": "content_block_delta", "delta": {"text": "ignored"}}

    deltas = list(AnthropicGenerationAdapter(streamer).stream(_generation_request(), flag))
    assert [delta.text for delta in deltas] == ["first"]


def test_live_stream_transport_parses_incrementally_and_closes_resource():
    frames = [
        {"type": "stream.started", "sequence": 0, "request_id": "r", "correlation_id": "c", "data": {}},
        {"type": "content.delta", "sequence": 1, "request_id": "r", "correlation_id": "c", "data": {"text": "hi"}},
        {"type": "stream.completed", "sequence": 2, "request_id": "r", "correlation_id": "c", "data": {}},
    ]
    wire = b"".join(b"data: " + json.dumps(frame).encode() + b"\n\n" for frame in frames)
    handle = FakeHandle([wire[:17], wire[17:43], wire[43:]])
    config = ClientConfig(base_url="https://product.invalid", access_token="product-token")
    transport = ProductAPIStreamTransport(config, opener=lambda request, timeout: handle)

    events = list(transport.stream_events("/messages:stream", {"model": "m", "messages": [{}]}))
    assert [event.type for event in events] == [
        StreamEventType.STREAM_STARTED,
        StreamEventType.CONTENT_DELTA,
        StreamEventType.STREAM_COMPLETED,
    ]
    assert handle.closed is True


def test_product_client_requires_configured_stream_transport():
    config = ClientConfig(base_url="https://product.invalid")
    client = ProductAPIClient(ProductAPITransport(config, sender=lambda request, timeout: None))
    try:
        list(client.stream_message({"model": "m", "messages": [{}]}))
    except RuntimeError as exc:
        assert "stream transport" in str(exc)
    else:
        raise AssertionError("streaming without a transport must fail")
