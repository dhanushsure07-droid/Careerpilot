"""Deterministic checks that must not depend on model output."""

from collections.abc import Iterable

from app.models.approval import ActionApproval
from app.models.evidence import CandidateEvidence, ResumeClaim, VerificationStatus


class ValidationError(ValueError):
    """Raised when a proposed claim or action fails a domain rule."""


def validate_resume_claim(
    claim: ResumeClaim, evidence_items: Iterable[CandidateEvidence]
) -> None:
    """Reject claims without matching, verified evidence.

    This checks the evidence references supplied by the application. It cannot
    prove that the wording of a resume claim is entailed by that evidence; a
    future review workflow must address that stronger semantic check.
    """

    evidence_by_id = {item.id: item for item in evidence_items}
    for evidence_id in claim.evidence_ids:
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            raise ValidationError(f"Evidence {evidence_id} was not found.")
        if evidence.verification_status is not VerificationStatus.VERIFIED:
            raise ValidationError(f"Evidence {evidence_id} is not verified.")


def require_action_approval(
    proposed_action: str,
    scope: dict[str, str],
    approvals: Iterable[ActionApproval],
) -> None:
    """Allow an external action only for an explicitly approved exact scope."""

    for approval in approvals:
        if (
            approval.approved
            and approval.proposed_action == proposed_action
            and approval.scope == scope
        ):
            return

    raise ValidationError("No explicit approval exists for this action and scope.")
