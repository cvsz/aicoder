"""Application service for provider-neutral generation and canonical stream events."""

from dataclasses import dataclass
from typing import Iterable, Iterator, Optional

from zaicoder.domain import StreamEvent, StreamEventType, StreamSequenceValidator
from zaicoder.providers import ProviderError
from zaicoder.providers.generation import CancellationSignal, GenerationProvider, GenerationRequest


@dataclass
class CancellationToken:
    _cancelled: bool = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True


class GenerationService:
    def __init__(self, provider: GenerationProvider) -> None:
        self.provider = provider

    def stream(
        self,
        request: GenerationRequest,
        *,
        request_id: str,
        correlation_id: str,
        cancellation: Optional[CancellationSignal] = None,
    ) -> Iterable[StreamEvent]:
        signal = cancellation or CancellationToken()
        return self._events(request, request_id, correlation_id, signal)

    def _events(
        self,
        request: GenerationRequest,
        request_id: str,
        correlation_id: str,
        cancellation: CancellationSignal,
    ) -> Iterator[StreamEvent]:
        sequence = 0
        validator = StreamSequenceValidator()

        def emit(event_type: StreamEventType, data=None) -> StreamEvent:
            nonlocal sequence
            event = StreamEvent(event_type, sequence, request_id, correlation_id, data or {})
            validator.accept(event)
            sequence += 1
            return event

        yield emit(StreamEventType.STREAM_STARTED, {"model": request.model})
        yield emit(StreamEventType.MESSAGE_STARTED, {})
        try:
            for delta in self.provider.stream(request, cancellation):
                if cancellation.cancelled:
                    yield emit(StreamEventType.STREAM_CANCELLED, {})
                    validator.finalize()
                    return
                if delta.text:
                    yield emit(StreamEventType.CONTENT_DELTA, {"text": delta.text})
                if delta.usage.total_tokens or delta.usage.cache_read_tokens or delta.usage.cache_write_tokens:
                    yield emit(StreamEventType.USAGE_UPDATED, delta.usage.to_dict())
                if delta.completed:
                    yield emit(
                        StreamEventType.MESSAGE_COMPLETED,
                        {"stop_reason": delta.stop_reason.value, "usage": delta.usage.to_dict()},
                    )
                    yield emit(StreamEventType.STREAM_COMPLETED, {})
                    validator.finalize()
                    return
        except ProviderError as exc:
            yield emit(
                StreamEventType.STREAM_FAILED,
                {"code": exc.code.value, "message": exc.message, "retryable": exc.retryable},
            )
            validator.finalize()
            return
        except Exception:
            yield emit(
                StreamEventType.STREAM_FAILED,
                {"code": "provider_unavailable", "message": "Provider generation failed", "retryable": True},
            )
            validator.finalize()
            return

        if cancellation.cancelled:
            yield emit(StreamEventType.STREAM_CANCELLED, {})
        else:
            yield emit(
                StreamEventType.STREAM_FAILED,
                {"code": "provider_invalid_response", "message": "Provider stream ended without completion", "retryable": False},
            )
        validator.finalize()
