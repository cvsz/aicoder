import pytest

from zaicoder.domain import (
    ContentBlock,
    ContentType,
    ErrorEnvelope,
    Message,
    MessageRole,
    ProductError,
    StreamEvent,
    StreamEventType,
    StreamSequenceValidator,
    Usage,
)


def test_message_round_trip_is_provider_neutral():
    message = Message(
        role=MessageRole.USER,
        content=[ContentBlock(type=ContentType.TEXT, text="hello")],
        id="msg-1",
        conversation_id="conv-1",
    )

    assert Message.from_dict(message.to_dict()) == message
    assert "anthropic" not in repr(message.to_dict()).lower()


def test_content_validation_rejects_incomplete_blocks():
    with pytest.raises(ValueError, match="requires text"):
        ContentBlock(type=ContentType.TEXT)
    with pytest.raises(ValueError, match="tool_call_id"):
        ContentBlock(type=ContentType.TOOL_RESULT)


def test_usage_rejects_negative_values():
    with pytest.raises(ValueError, match="non-negative"):
        Usage(input_tokens=-1)


def test_error_envelope_redacts_nested_secrets():
    envelope = ErrorEnvelope(
        ProductError(
            code="provider_error",
            message="request failed",
            request_id="req-1",
            correlation_id="corr-1",
            details={
                "authorization": "Bearer secret",
                "nested": {"api-key": "secret", "safe": "visible"},
            },
        )
    )

    serialized = envelope.to_dict()
    assert serialized["error"]["details"]["authorization"] == "[REDACTED]"
    assert serialized["error"]["details"]["nested"]["api-key"] == "[REDACTED]"
    assert serialized["error"]["details"]["nested"]["safe"] == "visible"


def _event(event_type, sequence):
    return StreamEvent(
        type=event_type,
        sequence=sequence,
        request_id="req-1",
        correlation_id="corr-1",
    )


def test_stream_sequence_accepts_exactly_one_terminal_event():
    StreamSequenceValidator.validate(
        [
            _event(StreamEventType.STREAM_STARTED, 0),
            _event(StreamEventType.CONTENT_DELTA, 1),
            _event(StreamEventType.STREAM_COMPLETED, 2),
        ]
    )


def test_stream_sequence_rejects_missing_terminal_event():
    with pytest.raises(ValueError, match="terminal"):
        StreamSequenceValidator.validate([_event(StreamEventType.STREAM_STARTED, 0)])


def test_stream_sequence_rejects_events_after_terminal():
    with pytest.raises(ValueError, match="follow"):
        StreamSequenceValidator.validate(
            [
                _event(StreamEventType.STREAM_STARTED, 0),
                _event(StreamEventType.STREAM_COMPLETED, 1),
                _event(StreamEventType.HEARTBEAT, 2),
            ]
        )


def test_stream_sequence_rejects_non_monotonic_sequence():
    with pytest.raises(ValueError, match="monotonically"):
        StreamSequenceValidator.validate(
            [
                _event(StreamEventType.STREAM_STARTED, 1),
                _event(StreamEventType.STREAM_COMPLETED, 1),
            ]
        )
