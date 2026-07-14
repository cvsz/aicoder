"""Provider-independent HTTP transport for the Product API client."""

import json
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from zaicoder.domain import ErrorEnvelope

from .config import ClientConfig
from .retries import RetryPolicy


@dataclass(frozen=True)
class TransportResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8")) if self.body else None


class ProductAPIError(RuntimeError):
    def __init__(self, envelope: ErrorEnvelope, status_code: int) -> None:
        self.envelope = envelope
        self.status_code = status_code
        super().__init__(envelope.error.message)


Sender = Callable[[Request, float], TransportResponse]
Sleeper = Callable[[float], None]


def _default_sender(request: Request, timeout: float) -> TransportResponse:
    try:
        with urlopen(request, timeout=timeout) as response:  # nosec B310 - URL is constrained by ClientConfig
            return TransportResponse(
                status_code=int(response.status),
                headers=dict(response.headers.items()),
                body=response.read(),
            )
    except HTTPError as exc:
        return TransportResponse(
            status_code=int(exc.code),
            headers=dict(exc.headers.items()) if exc.headers else {},
            body=exc.read(),
        )


class ProductAPITransport:
    def __init__(
        self,
        config: ClientConfig,
        *,
        sender: Sender = _default_sender,
        sleeper: Sleeper = time.sleep,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> None:
        self.config = config
        self._sender = sender
        self._sleeper = sleeper
        self.retry_policy = retry_policy or RetryPolicy(max_retries=config.max_retries)

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, Any]] = None,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        resolved_request_id = request_id or str(uuid.uuid4())
        headers: dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": self.config.user_agent,
            "X-API-Version": self.config.api_version,
            "X-Request-ID": resolved_request_id,
            "X-Correlation-ID": correlation_id or resolved_request_id,
        }
        if self.config.access_token:
            headers["Authorization"] = f"Bearer {self.config.access_token}"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        body = None
        if payload is not None:
            body = json.dumps(dict(payload), separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"

        attempt = 0
        while True:
            request = Request(self.config.endpoint(path), data=body, headers=headers, method=method.upper())
            try:
                response = self._sender(request, self.config.timeout_seconds)
            except URLError:
                if not self.retry_policy.should_retry(
                    method=method,
                    attempt=attempt,
                    connection_error=True,
                    idempotency_key=idempotency_key,
                ):
                    raise
                self._sleeper(self.retry_policy.delay_seconds(attempt))
                attempt += 1
                continue

            if 200 <= response.status_code < 300:
                return response.json()
            if self.retry_policy.should_retry(
                method=method,
                attempt=attempt,
                status_code=response.status_code,
                idempotency_key=idempotency_key,
            ):
                self._sleeper(self.retry_policy.delay_seconds(attempt))
                attempt += 1
                continue
            try:
                envelope = ErrorEnvelope.from_dict(response.json())
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                raise RuntimeError(
                    f"Product API returned HTTP {response.status_code} without a valid error envelope"
                ) from exc
            raise ProductAPIError(envelope, response.status_code)
