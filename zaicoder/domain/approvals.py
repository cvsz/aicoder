"""Explicit approval states and transition validation."""

from enum import Enum
from typing import Dict, FrozenSet


class ApprovalState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    REVOKED = "revoked"


_TRANSITIONS: Dict[ApprovalState, FrozenSet[ApprovalState]] = {
    ApprovalState.PENDING: frozenset({ApprovalState.APPROVED, ApprovalState.DENIED, ApprovalState.EXPIRED}),
    ApprovalState.APPROVED: frozenset({ApprovalState.REVOKED, ApprovalState.EXPIRED}),
    ApprovalState.DENIED: frozenset(),
    ApprovalState.EXPIRED: frozenset(),
    ApprovalState.REVOKED: frozenset(),
}


def validate_approval_transition(current: ApprovalState, target: ApprovalState) -> None:
    if target not in _TRANSITIONS[current]:
        raise ValueError(f"invalid approval transition: {current.value} -> {target.value}")
