"""Durable job states and transition validation."""

from enum import Enum
from typing import Dict, FrozenSet


class JobState(str, Enum):
    QUEUED = "queued"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPIRED = "expired"


_TRANSITIONS: Dict[JobState, FrozenSet[JobState]] = {
    JobState.QUEUED: frozenset({JobState.AWAITING_APPROVAL, JobState.APPROVED, JobState.RUNNING, JobState.CANCELLED, JobState.EXPIRED}),
    JobState.AWAITING_APPROVAL: frozenset({JobState.APPROVED, JobState.CANCELLED, JobState.EXPIRED}),
    JobState.APPROVED: frozenset({JobState.RUNNING, JobState.CANCELLED, JobState.EXPIRED}),
    JobState.RUNNING: frozenset({JobState.CANCELLING, JobState.SUCCEEDED, JobState.FAILED, JobState.RETRYING}),
    JobState.CANCELLING: frozenset({JobState.CANCELLED, JobState.FAILED}),
    JobState.RETRYING: frozenset({JobState.QUEUED, JobState.RUNNING, JobState.FAILED}),
    JobState.CANCELLED: frozenset(),
    JobState.SUCCEEDED: frozenset(),
    JobState.FAILED: frozenset({JobState.RETRYING}),
    JobState.EXPIRED: frozenset(),
}


def validate_job_transition(current: JobState, target: JobState) -> None:
    if target not in _TRANSITIONS[current]:
        raise ValueError(f"invalid job transition: {current.value} -> {target.value}")
