"""Incremental Product API stream transport with explicit resource ownership."""

import json
import uuid
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Callable, Optional, Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from zaicoder.domain import ErrorEnvelope, StreamEvent, StreamSequenceValidator

from .config import ClientConfig
from .streaming import EventStreamParser
from .transport import ProductAPIError


class CancellationSignal(Protocol):
    @property
    def cancelled(self) -> bool: ...


class StreamHandle(Protocol):
    status: int
    headers: Mapping[str, str]

    def read(self, size: int = -1) -> bytes: ...

    def close(self) -> None: ...


StreamOpener = Callable[[Request, float], StreamHandle]


def _default_opener(request: Request, timeout: float) -> StreamHandle:
    return urlopen(request, timeout=timeout)  # nosec B310 - URL constrained by ClientConfig


@dataclass
class ProductAPIStreamTransport:
    config: ClientConfig
    opener: StreamOpener = _default_opener
    chunk_size: int = 4096

    def stream_events(
        self,
        path: str,
        payload: Mapping[str, object],
        *,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        cancellation: Optional[CancellationSignal] = None,
    ) -> Iterator[StreamEvent]:
        resolved_request_id = request_id or str(uuid.uuid4())
        headers: dict[str, str] = {
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
            "User-Agent": self.config.user_agent,
            "X-API-Version": self.config.api_version,
            "X-Request-ID": resolved_request_id,
            "X-Correlation-ID": correlation_id or resolved_request_id,
        }
        if self.config.access_token:
            headers["Authorization"] = f"Bearer {self.config.access_token}"
        request = Request(
            self.config.endpoint(path),
            data=json.dumps(dict(payload), separators=(",", ":")).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            response = self.opener(request, self.config.timeout_seconds)
        except HTTPError as exc:
            try:
                envelope = ErrorEnvelope.from_dict(json.loads(exc.read().decode("utf-8")))
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as parse_error:
                raise RuntimeError(
                    f"Product API stream returned HTTP {exc.code} without a valid error envelope"
                ) from parse_error
            raise ProductAPIError(envelope, int(exc.code)) from exc
        parser = EventStreamParser()
        validator = StreamSequenceValidator()
        try:
            status = int(getattr(response, "status", 200))
            if status < 200 or status >= 300:
                raise RuntimeError(f"Product API stream returned HTTP {status}")
            while True:
                if cancellation is not None and cancellation.cancelled:
                    return
                chunk = response.read(self.chunk_size)
                if not chunk:
                    break
                for event in parser.feed(chunk):
                    validator.accept(event)
                    yield event
                    if event.terminal:
                        validator.finalize()
                        return
            for event in parser.finalize():
                validator.accept(event)
                yield event
            validator.finalize()
        finally:
            response.close()
