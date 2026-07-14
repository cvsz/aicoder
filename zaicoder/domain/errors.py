"""Typed Product API error contracts and secret-safe serialization."""

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

_REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "refresh_token",
    "secret",
    "token",
}


def redact_details(value: Any) -> Any:
    """Recursively redact values stored under sensitive keys."""
    if isinstance(value, Mapping):
        result: Dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            result[str(key)] = _REDACTED if normalized in _SENSITIVE_KEYS else redact_details(item)
        return result
    if isinstance(value, list):
        return [redact_details(item) for item in value]
    if isinstance(value, tuple):
        return [redact_details(item) for item in value]
    return value


@dataclass(frozen=True)
class ProductError:
    code: str
    message: str
    request_id: str
    correlation_id: str
    retryable: bool = False
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("error code must not be empty")
        if not self.message.strip():
            raise ValueError("error message must not be empty")
        if not self.request_id.strip() or not self.correlation_id.strip():
            raise ValueError("request_id and correlation_id are required")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "retryable": self.retryable,
            "details": redact_details(dict(self.details)),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProductError":
        return cls(
            code=str(value["code"]),
            message=str(value["message"]),
            request_id=str(value["request_id"]),
            correlation_id=str(value["correlation_id"]),
            retryable=bool(value.get("retryable", False)),
            details=dict(value.get("details", {})),
        )


@dataclass(frozen=True)
class ErrorEnvelope:
    error: ProductError

    def to_dict(self) -> Dict[str, Any]:
        return {"error": self.error.to_dict()}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ErrorEnvelope":
        raw_error: Optional[Any] = value.get("error")
        if not isinstance(raw_error, Mapping):
            raise ValueError("error envelope requires an error object")
        return cls(error=ProductError.from_dict(raw_error))
