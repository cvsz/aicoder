import json

from zaicoder.api import AuthMiddleware, Principal, ProductAPIApplication, ProductAPIRequest, StaticTokenAuthenticator, TokenRecord
from zaicoder.domain import ContentBlock, ContentType, Message, MessageRole, StopReason, StreamEventType, Usage
from zaicoder.providers import GenerationRequest, ProviderDelta, ProviderError, ProviderErrorCode
from zaicoder.services import CancellationToken, GenerationService


class FakeProvider:
    name = "fake"

    def __init__(self, deltas):
        self.deltas = list(deltas)

    def stream(self, request, cancellation):
        del request
        for delta in self.deltas:
            yield delta


def _request():
    return GenerationRequest(
        model="model-a",
        messages=[Message(MessageRole.USER, [ContentBlock(ContentType.TEXT, text="hello")])],
    )


def _payload():
    return json.dumps(
        {
            "model": "model-a",
            "messages": [{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
        }
    ).encode()


def test_service_emits_ordered_terminal_stream():
    service = GenerationService(
        FakeProvider(
            [
                ProviderDelta(text="hel"),
                ProviderDelta(text="lo", usage=Usage(input_tokens=2, output_tokens=1)),
                ProviderDelta(completed=True, stop_reason=StopReason.END_TURN, usage=Usage(input_tokens=2, output_tokens=2)),
            ]
        )
    )
    events = list(service.stream(_request(), request_id="req", correlation_id="corr"))
    assert [event.sequence for event in events] == list(range(len(events)))
    assert events[-1].type is StreamEventType.STREAM_COMPLETED
    assert sum(event.terminal for event in events) == 1
    assert "".join(event.data.get("text", "") for event in events) == "hello"


def test_service_turns_cancellation_into_terminal_event():
    token = CancellationToken()

    class CancellingProvider:
        name = "fake"

        def stream(self, request, cancellation):
            del request, cancellation
            yield ProviderDelta(text="partial")
            token.cancel()
            yield ProviderDelta(text="ignored")

    events = list(
        GenerationService(CancellingProvider()).stream(
            _request(), request_id="req", correlation_id="corr", cancellation=token
        )
    )
    assert events[-1].type is StreamEventType.STREAM_CANCELLED
    assert "ignored" not in repr([event.to_dict() for event in events])


def test_provider_failure_is_redacted_and_terminal():
    class FailingProvider:
        name = "fake"

        def stream(self, request, cancellation):
            del request, cancellation
            raise ProviderError(ProviderErrorCode.UNAVAILABLE, "Provider temporarily unavailable", True)
            yield

    events = list(GenerationService(FailingProvider()).stream(_request(), request_id="req", correlation_id="corr"))
    assert events[-1].type is StreamEventType.STREAM_FAILED
    assert events[-1].data["retryable"] is True


def test_product_api_supports_non_streaming_generation():
    service = GenerationService(
        FakeProvider(
            [
                ProviderDelta(text="hello"),
                ProviderDelta(completed=True, stop_reason=StopReason.END_TURN, usage=Usage(output_tokens=1)),
            ]
        )
    )
    response = ProductAPIApplication(product_version="1.23.0", generation=service).handle(
        ProductAPIRequest("POST", "/v1/messages", body=_payload())
    )
    assert response.status_code == 200
    assert response.json()["message"]["content"][0]["text"] == "hello"
    assert response.json()["stop_reason"] == "end_turn"


def test_product_api_returns_canonical_sse_events():
    service = GenerationService(
        FakeProvider([ProviderDelta(text="hi"), ProviderDelta(completed=True, stop_reason=StopReason.END_TURN)])
    )
    response = ProductAPIApplication(product_version="1.23.0", generation=service).handle(
        ProductAPIRequest(
            "POST",
            "/v1/messages:stream",
            headers={"X-Request-ID": "req-1", "X-Correlation-ID": "corr-1"},
            body=_payload(),
        )
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/event-stream"
    text = response.body.decode()
    assert "event: stream.started" in text
    assert "event: content.delta" in text
    assert "event: stream.completed" in text
    assert '"request_id":"req-1"' in text


def test_generation_routes_require_messages_write_scope():
    app = ProductAPIApplication(
        product_version="1.23.0",
        generation=GenerationService(FakeProvider([ProviderDelta(completed=True, stop_reason=StopReason.END_TURN)])),
    )
    middleware = AuthMiddleware(
        app,
        StaticTokenAuthenticator(
            {
                "limited": TokenRecord("limited", Principal("user", frozenset())),
                "writer": TokenRecord("writer", Principal("user", frozenset({"messages:write"}))),
            }
        ),
    )
    denied = middleware.handle(
        ProductAPIRequest("POST", "/v1/messages", headers={"Authorization": "Bearer limited"}, body=_payload())
    )
    allowed = middleware.handle(
        ProductAPIRequest("POST", "/v1/messages", headers={"Authorization": "Bearer writer"}, body=_payload())
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["details"] == {"required_scopes": ["messages:write"]}
    assert allowed.status_code == 200


def test_invalid_generation_payload_is_typed_validation_error():
    response = ProductAPIApplication(
        product_version="1.23.0", generation=GenerationService(FakeProvider([]))
    ).handle(ProductAPIRequest("POST", "/v1/messages", body=b"{}"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["retryable"] is False
