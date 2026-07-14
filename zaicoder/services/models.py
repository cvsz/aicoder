"""Provider-neutral model catalog application service."""

from dataclasses import dataclass
from typing import Sequence

from zaicoder.domain import ModelDescriptor
from zaicoder.providers import ModelProvider


@dataclass
class ModelCatalogService:
    provider: ModelProvider

    def list_models(self) -> Sequence[ModelDescriptor]:
        models = tuple(self.provider.list_models())
        ids = [model.id for model in models]
        if len(ids) != len(set(ids)):
            raise ValueError("provider model ids must be unique")
        return tuple(sorted(models, key=lambda model: model.id))
