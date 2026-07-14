"""Retry classification and bounded exponential backoff."""

from dataclasses import dataclass
from typing import Optional


_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
_NEVER_RETRY_STATUS = {400, 401, 403, 404, 409, 422}
_IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 3
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 4.0

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.base_delay_seconds <= 0 or self.max_delay_seconds <= 0:
            raise ValueError("retry delays must be positive")
        if self.base_delay_seconds > self.max_delay_seconds:
            raise ValueError("base delay cannot exceed max delay")

    def should_retry(
        self,
        *,
        method: str,
        attempt: int,
        status_code: Optional[int] = None,
        connection_error: bool = False,
        idempotency_key: Optional[str] = None,
        cancelled: bool = False,
    ) -> bool:
        if cancelled or attempt >= self.max_retries:
            return False
        safe = method.upper() in _IDEMPOTENT_METHODS or bool(idempotency_key)
        if not safe:
            return False
        if connection_error:
            return True
        if status_code in _NEVER_RETRY_STATUS:
            return False
        return status_code in _RETRYABLE_STATUS

    def delay_seconds(self, attempt: int, jitter_fraction: float = 0.0) -> float:
        if attempt < 0:
            raise ValueError("attempt must be non-negative")
        if not 0.0 <= jitter_fraction <= 1.0:
            raise ValueError("jitter_fraction must be between 0 and 1")
        bounded = min(self.max_delay_seconds, self.base_delay_seconds * (2**attempt))
        return bounded * (1.0 + jitter_fraction)
