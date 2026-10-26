from uuid import uuid4

import pytest

from app.models.approval import ActionApproval
from app.models.evidence import (
    CandidateEvidence,
    ResumeClaim,
    VerificationStatus,
)
from app.services.validation import (
    ValidationError,
    require_action_approval,
    validate_resume_claim,
)


def test_verified_evidence_can_support_resume_claim() -> None:
    evidence = CandidateEvidence(
        claim="Built a reporting dashboard",
        source="Project portfolio, project alpha",
        verification_status=VerificationStatus.VERIFIED,
    )
    claim = ResumeClaim(claim=evidence.claim, evidence_ids=[evidence.id])

    validate_resume_claim(claim, [evidence])


def test_unverified_evidence_is_rejected_for_resume_claim() -> None:
    evidence = CandidateEvidence(
        claim="Built a reporting dashboard",
        source="Project portfolio, project alpha",
    )
    claim = ResumeClaim(claim=evidence.claim, evidence_ids=[evidence.id])

    with pytest.raises(ValidationError, match="not verified"):
        validate_resume_claim(claim, [evidence])


def test_resume_claim_with_unknown_evidence_is_rejected() -> None:
    claim = ResumeClaim(claim="Built a dashboard", evidence_ids=[uuid4()])

    with pytest.raises(ValidationError, match="was not found"):
        validate_resume_claim(claim, [])


def test_explicit_approval_for_exact_action_and_scope_is_allowed() -> None:
    scope = {"destination": "demo.example/apply/123", "draft_id": "draft-1"}
    approval = ActionApproval(
        proposed_action="submit_application", scope=scope, approved=True
    )

    require_action_approval("submit_application", scope, [approval])


def test_unapproved_action_is_rejected() -> None:
    scope = {"destination": "demo.example/apply/123"}
    approval = ActionApproval(
        proposed_action="submit_application", scope=scope, approved=False
    )

    with pytest.raises(ValidationError, match="No explicit approval"):
        require_action_approval("submit_application", scope, [approval])


@pytest.mark.parametrize(
    ("requested_action", "requested_scope"),
    [
        ("send_message", {"destination": "demo.example/apply/123"}),
        ("submit_application", {"destination": "demo.example/apply/456"}),
        (
            "submit_application",
            {"destination": "demo.example/apply/123", "draft_id": "draft-2"},
        ),
    ],
)
def test_approval_cannot_be_reused_for_different_action_or_scope(
    requested_action: str, requested_scope: dict[str, str]
) -> None:
    approval = ActionApproval(
        proposed_action="submit_application",
        scope={"destination": "demo.example/apply/123", "draft_id": "draft-1"},
        approved=True,
    )

    with pytest.raises(ValidationError, match="No explicit approval"):
        require_action_approval(requested_action, requested_scope, [approval])
