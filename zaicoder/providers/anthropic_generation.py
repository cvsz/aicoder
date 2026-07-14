"""Server-only Anthropic generation adapter with injected SDK stream boundary."""

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

from zaicoder.domain import StopReason, Usage

from .base import ProviderError, ProviderErrorCode
from .generation import CancellationSignal, GenerationRequest, ProviderDelta

AnthropicStream = Callable[[Mapping[str, Any]], Iterable[Mapping[str, Any]]]


@dataclass
class AnthropicGenerationAdapter:
    """Translate Anthropic-style stream records into provider-neutral deltas.

    The actual SDK call is injected so this module never imports the Anthropic SDK
    and can be tested without network access or credentials.
    """

    event_streamer: AnthropicStream

    @property
    def name(self) -> str:
        return "anthropic"

    def stream(self, request: GenerationRequest, cancellation: CancellationSignal):
        payload = {
            "model": request.model,
            "max_tokens": request.max_output_tokens,
            "messages": [message.to_dict() for message in request.messages],
            "metadata": dict(request.metadata),
            "stream": True,
        }
        try:
            for event in self.event_streamer(payload):
                if cancellation.cancelled:
                    return
                event_type = str(event.get("type", ""))
                if event_type == "content_block_delta":
                    delta = event.get("delta", {})
                    text = delta.get("text") if isinstance(delta, Mapping) else None
                    if text:
                        yield ProviderDelta(text=str(text))
                elif event_type == "message_delta":
                    usage = event.get("usage", {})
                    stop = str(event.get("stop_reason") or "unknown")
                    yield ProviderDelta(
                        usage=Usage(
                            input_tokens=int(usage.get("input_tokens", 0)),
                            output_tokens=int(usage.get("output_tokens", 0)),
                        ),
                        completed=bool(event.get("completed", False)),
                        stop_reason=_stop_reason(stop),
                    )
                elif event_type == "message_stop":
                    usage = event.get("usage", {})
                    yield ProviderDelta(
                        completed=True,
                        stop_reason=_stop_reason(str(event.get("stop_reason") or "end_turn")),
                        usage=Usage(
                            input_tokens=int(usage.get("input_tokens", 0)),
                            output_tokens=int(usage.get("output_tokens", 0)),
                        ),
                    )
        except PermissionError as exc:
            raise ProviderError(ProviderErrorCode.AUTHENTICATION, "Provider authentication failed", False) from exc
        except TimeoutError as exc:
            raise ProviderError(ProviderErrorCode.UNAVAILABLE, "Provider stream timed out", True) from exc
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(ProviderErrorCode.UNAVAILABLE, "Provider stream is unavailable", True) from exc


def _stop_reason(value: str) -> StopReason:
    try:
        return StopReason(value)
    except ValueError:
        return StopReason.UNKNOWN
