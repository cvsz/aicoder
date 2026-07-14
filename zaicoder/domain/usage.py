"""Provider-neutral usage accounting contract."""

from dataclasses import dataclass
from typing import Any, Dict, Mapping


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    thinking_tokens: int = 0

    def __post_init__(self) -> None:
        for name, value in self.to_dict().items():
            if value < 0:
                raise ValueError(f"{name} must be non-negative")

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> Dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "thinking_tokens": self.thinking_tokens,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Usage":
        return cls(
            input_tokens=int(value.get("input_tokens", 0)),
            output_tokens=int(value.get("output_tokens", 0)),
            cache_read_tokens=int(value.get("cache_read_tokens", 0)),
            cache_write_tokens=int(value.get("cache_write_tokens", 0)),
            thinking_tokens=int(value.get("thinking_tokens", 0)),
        )
