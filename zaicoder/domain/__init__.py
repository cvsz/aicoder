"""Canonical provider-neutral domain contracts."""

from .approvals import ApprovalState, validate_approval_transition
from .content import ContentBlock, ContentType, Message, MessageRole
from .errors import ErrorEnvelope, ProductError, redact_details
from .jobs import JobState, validate_job_transition
from .models import ModelCapabilities, ModelDescriptor, StopReason
from .pagination import Page, PageInfo
from .streams import StreamEvent, StreamEventType, StreamSequenceValidator
from .usage import Usage

__all__ = [
    "ApprovalState",
    "ContentBlock",
    "ContentType",
    "ErrorEnvelope",
    "JobState",
    "Message",
    "MessageRole",
    "ModelCapabilities",
    "ModelDescriptor",
    "Page",
    "PageInfo",
    "ProductError",
    "StopReason",
    "StreamEvent",
    "StreamEventType",
    "StreamSequenceValidator",
    "Usage",
    "redact_details",
    "validate_approval_transition",
    "validate_job_transition",
]
