"""Server-only Anthropic model adapter with provider-neutral output."""

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

from zaicoder.domain import ModelCapabilities, ModelDescriptor

from .base import ProviderError, ProviderErrorCode

ModelLister = Callable[[], Iterable[Mapping[str, Any]]]


@dataclass
class AnthropicProviderAdapter:
    """Map Anthropic model metadata into canonical product contracts.

    The SDK/network call is injected so tests and client-facing packages never
    import the provider SDK or require provider credentials.
    """

    model_lister: ModelLister

    @property
    def name(self) -> str:
        return "anthropic"

    def list_models(self) -> Sequence[ModelDescriptor]:
        try:
            raw_models = list(self.model_lister())
        except PermissionError as exc:
            raise ProviderError(
                ProviderErrorCode.AUTHENTICATION,
                "Provider authentication failed",
                retryable=False,
            ) from exc
        except TimeoutError as exc:
            raise ProviderError(
                ProviderErrorCode.UNAVAILABLE,
                "Provider request timed out",
                retryable=True,
            ) from exc
        except Exception as exc:
            raise ProviderError(
                ProviderErrorCode.UNAVAILABLE,
                "Provider model catalog is unavailable",
                retryable=True,
            ) from exc

        models = []
        for raw in raw_models:
            model_id = str(raw.get("id", "")).strip()
            if not model_id:
                raise ProviderError(
                    ProviderErrorCode.INVALID_RESPONSE,
                    "Provider returned a model without an id",
                    retryable=False,
                )
            display_name = str(raw.get("display_name") or raw.get("displayName") or model_id)
            models.append(
                ModelDescriptor(
                    id=model_id,
                    display_name=display_name,
                    capabilities=ModelCapabilities(
                        streaming=bool(raw.get("streaming", True)),
                        tools=bool(raw.get("tools", True)),
                        vision=bool(raw.get("vision", True)),
                        documents=bool(raw.get("documents", True)),
                        structured_output=bool(raw.get("structured_output", False)),
                        thinking=bool(raw.get("thinking", False)),
                        max_context_tokens=raw.get("max_context_tokens"),
                        max_output_tokens=raw.get("max_output_tokens"),
                    ),
                    aliases=tuple(str(alias) for alias in raw.get("aliases", ())),
                    available=bool(raw.get("available", True)),
                    metadata={"provider": self.name},
                )
            )
        return tuple(models)
