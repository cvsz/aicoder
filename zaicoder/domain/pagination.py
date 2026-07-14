"""Provider-neutral cursor pagination contracts."""

from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Mapping, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class PageInfo:
    next_cursor: Optional[str] = None
    previous_cursor: Optional[str] = None
    has_more: bool = False

    def __post_init__(self) -> None:
        if self.has_more and not self.next_cursor:
            raise ValueError("has_more requires next_cursor")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "next_cursor": self.next_cursor,
            "previous_cursor": self.previous_cursor,
            "has_more": self.has_more,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PageInfo":
        return cls(
            next_cursor=value.get("next_cursor"),
            previous_cursor=value.get("previous_cursor"),
            has_more=bool(value.get("has_more", False)),
        )


@dataclass(frozen=True)
class Page(Generic[T]):
    items: List[T]
    page: PageInfo

    def __post_init__(self) -> None:
        if not isinstance(self.items, list):
            raise ValueError("page items must be a list")
