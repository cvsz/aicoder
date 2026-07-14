"""Provider-neutral server-side provider contracts."""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Sequence

from zaicoder.domain import ModelDescriptor


class ProviderErrorCode(str, Enum):
    UNAVAILABLE = "provider_unavailable"
    AUTHENTICATION = "provider_authentication_failed"
    RATE_LIMITED = "provider_rate_limited"
    INVALID_RESPONSE = "provider_invalid_response"
    CONFIGURATION = "provider_configuration_error"


@dataclass(frozen=True)
class ProviderError(RuntimeError):
    code: ProviderErrorCode
    message: str
    retryable: bool = False

    def __str__(self) -> str:
        return self.message


class ModelProvider(Protocol):
    """Server-only provider contract exposed to application services."""

    @property
    def name(self) -> str:
        ...

    def list_models(self) -> Sequence[ModelDescriptor]:
        ...
