"""Provider-neutral server-side message generation contracts."""

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Protocol, Sequence

from zaicoder.domain import Message, StopReason, Usage


@dataclass(frozen=True)
class GenerationRequest:
    model: str
    messages: Sequence[Message]
    max_output_tokens: int = 1024
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise ValueError("model is required")
        if not self.messages:
            raise ValueError("at least one message is required")
        if self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")


@dataclass(frozen=True)
class ProviderDelta:
    text: str = ""
    usage: Usage = field(default_factory=Usage)
    stop_reason: StopReason = StopReason.UNKNOWN
    completed: bool = False


class CancellationSignal(Protocol):
    @property
    def cancelled(self) -> bool:
        ...


class GenerationProvider(Protocol):
    """Server-only generation contract implemented by provider adapters."""

    @property
    def name(self) -> str:
        ...

    def stream(self, request: GenerationRequest, cancellation: CancellationSignal) -> Iterable[ProviderDelta]:
        ...
