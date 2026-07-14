"""Incremental parser for Product API server-sent events."""

import codecs
import json
from typing import Any, Dict, Iterable, List

from zaicoder.domain import StreamEvent


class StreamProtocolError(ValueError):
    """Raised when the Product API stream violates its wire contract."""


class EventStreamParser:
    """Parse fragmented UTF-8 SSE frames into canonical StreamEvent objects."""

    def __init__(self) -> None:
        self._decoder = codecs.getincrementaldecoder("utf-8")()
        self._buffer = ""
        self._closed = False

    def feed(self, chunk: bytes) -> List[StreamEvent]:
        if self._closed:
            raise StreamProtocolError("cannot feed a closed stream parser")
        self._buffer += self._decoder.decode(chunk, final=False)
        return self._drain_complete_frames()

    def finalize(self) -> List[StreamEvent]:
        if self._closed:
            return []
        self._closed = True
        self._buffer += self._decoder.decode(b"", final=True)
        events = self._drain_complete_frames()
        if self._buffer.strip():
            raise StreamProtocolError("stream ended with an incomplete frame")
        return events

    def _drain_complete_frames(self) -> List[StreamEvent]:
        events: List[StreamEvent] = []
        while "\n\n" in self._buffer:
            frame, self._buffer = self._buffer.split("\n\n", 1)
            event = self._parse_frame(frame)
            if event is not None:
                events.append(event)
        return events

    @staticmethod
    def _parse_frame(frame: str) -> StreamEvent:
        data_lines = []
        for raw_line in frame.splitlines():
            line = raw_line.strip("\r")
            if not line or line.startswith(":"):
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if not data_lines:
            raise StreamProtocolError("SSE frame does not contain data")
        try:
            value: Dict[str, Any] = json.loads("\n".join(data_lines))
        except (json.JSONDecodeError, TypeError) as exc:
            raise StreamProtocolError("SSE data is not valid JSON") from exc
        try:
            return StreamEvent.from_dict(value)
        except (KeyError, TypeError, ValueError) as exc:
            raise StreamProtocolError("SSE data is not a valid stream event") from exc


def parse_event_chunks(chunks: Iterable[bytes]) -> List[StreamEvent]:
    parser = EventStreamParser()
    result: List[StreamEvent] = []
    for chunk in chunks:
        result.extend(parser.feed(chunk))
    result.extend(parser.finalize())
    return result
