import pytest

from zaicoder.domain import (
    ApprovalState,
    JobState,
    ModelCapabilities,
    ModelDescriptor,
    PageInfo,
    StopReason,
    validate_approval_transition,
    validate_job_transition,
)


def test_model_descriptor_round_trip():
    model = ModelDescriptor(
        id="model-1",
        display_name="Model One",
        capabilities=ModelCapabilities(tools=True, max_context_tokens=1000),
        aliases=("model-latest",),
    )
    assert ModelDescriptor.from_dict(model.to_dict()) == model


def test_model_contract_rejects_invalid_limits_and_aliases():
    with pytest.raises(ValueError, match="positive"):
        ModelCapabilities(max_output_tokens=0)
    with pytest.raises(ValueError, match="canonical"):
        ModelDescriptor(id="m", display_name="M", aliases=("m",))


def test_stop_reason_has_provider_neutral_unknown_value():
    assert StopReason.UNKNOWN.value == "unknown"


def test_page_info_requires_cursor_when_more_results_exist():
    with pytest.raises(ValueError, match="next_cursor"):
        PageInfo(has_more=True)
    assert PageInfo(next_cursor="cursor-2", has_more=True).has_more


def test_valid_job_transitions():
    validate_job_transition(JobState.QUEUED, JobState.RUNNING)
    validate_job_transition(JobState.RUNNING, JobState.SUCCEEDED)
    validate_job_transition(JobState.FAILED, JobState.RETRYING)


def test_terminal_job_state_rejects_transition():
    with pytest.raises(ValueError, match="invalid job transition"):
        validate_job_transition(JobState.SUCCEEDED, JobState.RUNNING)


def test_valid_approval_transitions():
    validate_approval_transition(ApprovalState.PENDING, ApprovalState.APPROVED)
    validate_approval_transition(ApprovalState.APPROVED, ApprovalState.REVOKED)


def test_denied_approval_is_terminal():
    with pytest.raises(ValueError, match="invalid approval transition"):
        validate_approval_transition(ApprovalState.DENIED, ApprovalState.APPROVED)
