"""Provider-neutral model descriptors and stop-reason contracts."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Tuple


class StopReason(str, Enum):
    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    TOOL_USE = "tool_use"
    REFUSAL = "refusal"
    CANCELLED = "cancelled"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ModelCapabilities:
    streaming: bool = True
    tools: bool = False
    vision: bool = False
    documents: bool = False
    structured_output: bool = False
    thinking: bool = False
    max_context_tokens: Optional[int] = None
    max_output_tokens: Optional[int] = None

    def __post_init__(self) -> None:
        for value in (self.max_context_tokens, self.max_output_tokens):
            if value is not None and value <= 0:
                raise ValueError("token limits must be positive")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "streaming": self.streaming,
            "tools": self.tools,
            "vision": self.vision,
            "documents": self.documents,
            "structured_output": self.structured_output,
            "thinking": self.thinking,
            "max_context_tokens": self.max_context_tokens,
            "max_output_tokens": self.max_output_tokens,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelCapabilities":
        return cls(
            streaming=bool(value.get("streaming", True)),
            tools=bool(value.get("tools", False)),
            vision=bool(value.get("vision", False)),
            documents=bool(value.get("documents", False)),
            structured_output=bool(value.get("structured_output", False)),
            thinking=bool(value.get("thinking", False)),
            max_context_tokens=value.get("max_context_tokens"),
            max_output_tokens=value.get("max_output_tokens"),
        )


@dataclass(frozen=True)
class ModelDescriptor:
    id: str
    display_name: str
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    aliases: Tuple[str, ...] = ()
    available: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.display_name.strip():
            raise ValueError("model id and display_name are required")
        if self.id in self.aliases:
            raise ValueError("model aliases must not repeat the canonical id")
        if len(set(self.aliases)) != len(self.aliases):
            raise ValueError("model aliases must be unique")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "capabilities": self.capabilities.to_dict(),
            "aliases": list(self.aliases),
            "available": self.available,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelDescriptor":
        return cls(
            id=str(value["id"]),
            display_name=str(value["display_name"]),
            capabilities=ModelCapabilities.from_dict(value.get("capabilities", {})),
            aliases=tuple(str(alias) for alias in value.get("aliases", [])),
            available=bool(value.get("available", True)),
            metadata=dict(value.get("metadata", {})),
        )
