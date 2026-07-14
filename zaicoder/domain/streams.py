"""Canonical Product API stream-event vocabulary and sequence validation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, Mapping, Optional


class StreamEventType(str, Enum):
    STREAM_STARTED = "stream.started"
    MESSAGE_STARTED = "message.started"
    CONTENT_DELTA = "content.delta"
    TOOL_STARTED = "tool.started"
    TOOL_INPUT_DELTA = "tool.input.delta"
    TOOL_COMPLETED = "tool.completed"
    USAGE_UPDATED = "usage.updated"
    MESSAGE_COMPLETED = "message.completed"
    STREAM_COMPLETED = "stream.completed"
    STREAM_FAILED = "stream.failed"
    STREAM_CANCELLED = "stream.cancelled"
    HEARTBEAT = "heartbeat"


TERMINAL_EVENT_TYPES = {
    StreamEventType.STREAM_COMPLETED,
    StreamEventType.STREAM_FAILED,
    StreamEventType.STREAM_CANCELLED,
}


@dataclass(frozen=True)
class StreamEvent:
    type: StreamEventType
    sequence: int
    request_id: str
    correlation_id: str
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise ValueError("stream sequence must be non-negative")
        if not self.request_id or not self.correlation_id:
            raise ValueError("request_id and correlation_id are required")

    @property
    def terminal(self) -> bool:
        return self.type in TERMINAL_EVENT_TYPES

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "sequence": self.sequence,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "data": dict(self.data),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StreamEvent":
        return cls(
            type=StreamEventType(str(value["type"])),
            sequence=int(value["sequence"]),
            request_id=str(value["request_id"]),
            correlation_id=str(value["correlation_id"]),
            data=dict(value.get("data", {})),
        )


class StreamSequenceValidator:
    """Enforce ordering and exactly-one-terminal-event semantics."""

    def __init__(self) -> None:
        self._last_sequence: Optional[int] = None
        self._terminal_seen = False

    def accept(self, event: StreamEvent) -> None:
        if self._terminal_seen:
            raise ValueError("events cannot follow a terminal event")
        if self._last_sequence is not None and event.sequence <= self._last_sequence:
            raise ValueError("stream sequence must increase monotonically")
        self._last_sequence = event.sequence
        self._terminal_seen = event.terminal

    def finalize(self) -> None:
        if not self._terminal_seen:
            raise ValueError("stream must contain exactly one terminal event")

    @classmethod
    def validate(cls, events: Iterable[StreamEvent]) -> None:
        validator = cls()
        for event in events:
            validator.accept(event)
        validator.finalize()
