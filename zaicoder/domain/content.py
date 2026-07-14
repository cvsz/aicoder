"""Provider-neutral message and content-block contracts."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ContentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


@dataclass(frozen=True)
class ContentBlock:
    type: ContentType
    text: Optional[str] = None
    media_type: Optional[str] = None
    data: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    input: Mapping[str, Any] = field(default_factory=dict)
    is_error: bool = False

    def __post_init__(self) -> None:
        if self.type is ContentType.TEXT and self.text is None:
            raise ValueError("text content requires text")
        if self.type in {ContentType.IMAGE, ContentType.DOCUMENT}:
            if not self.media_type or self.data is None:
                raise ValueError("binary content requires media_type and data")
        if self.type is ContentType.TOOL_USE:
            if not self.tool_call_id or not self.tool_name:
                raise ValueError("tool_use requires tool_call_id and tool_name")
        if self.type is ContentType.TOOL_RESULT and not self.tool_call_id:
            raise ValueError("tool_result requires tool_call_id")

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["type"] = self.type.value
        return {key: value for key, value in result.items() if value not in (None, {}, False)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ContentBlock":
        return cls(
            type=ContentType(str(value["type"])),
            text=value.get("text"),
            media_type=value.get("media_type"),
            data=value.get("data"),
            tool_call_id=value.get("tool_call_id"),
            tool_name=value.get("tool_name"),
            input=dict(value.get("input", {})),
            is_error=bool(value.get("is_error", False)),
        )


@dataclass(frozen=True)
class Message:
    role: MessageRole
    content: List[ContentBlock]
    id: Optional[str] = None
    conversation_id: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.content:
            raise ValueError("message content must not be empty")

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "role": self.role.value,
            "content": [block.to_dict() for block in self.content],
        }
        if self.id is not None:
            result["id"] = self.id
        if self.conversation_id is not None:
            result["conversation_id"] = self.conversation_id
        if self.metadata:
            result["metadata"] = dict(self.metadata)
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Message":
        raw_content = value.get("content")
        if not isinstance(raw_content, list):
            raise ValueError("message content must be a list")
        return cls(
            role=MessageRole(str(value["role"])),
            content=[ContentBlock.from_dict(item) for item in raw_content],
            id=value.get("id"),
            conversation_id=value.get("conversation_id"),
            metadata=dict(value.get("metadata", {})),
        )
