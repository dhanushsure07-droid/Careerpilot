"""HTTP entry point for the minimal CareerPilot API."""

from uuid import UUID

from fastapi import FastAPI, HTTPException, status

from app.models.evidence import (
    EvidenceCreate,
    PersistedCandidateEvidence,
    VerificationUpdate,
)
from app.services.evidence_store import EvidenceStore


def create_app(evidence_store: EvidenceStore | None = None) -> FastAPI:
    """Build the API; tests can supply an isolated SQLite store."""

    application = FastAPI(
        title="CareerPilot API",
        description=(
            "Learning foundation API. Candidate IDs scope records but are not "
            "authentication; this API is not production-secure."
        ),
        version="0.2.0",
    )
    store = evidence_store or EvidenceStore()

    @application.get("/health")
    def health() -> dict[str, str]:
        """Report that this API process is responding."""

        return {"status": "ok"}

    @application.post(
        "/candidates/{candidate_id}/evidence",
        response_model=PersistedCandidateEvidence,
        status_code=status.HTTP_201_CREATED,
    )
    def create_evidence(
        candidate_id: UUID, payload: EvidenceCreate
    ) -> PersistedCandidateEvidence:
        return store.create(
            candidate_id,
            claim=payload.claim,
            source=payload.source,
            metadata=payload.metadata,
        )

    @application.get(
        "/candidates/{candidate_id}/evidence",
        response_model=list[PersistedCandidateEvidence],
    )
    def list_evidence(candidate_id: UUID) -> list[PersistedCandidateEvidence]:
        return store.list_for_candidate(candidate_id)

    @application.get(
        "/candidates/{candidate_id}/evidence/{evidence_id}",
        response_model=PersistedCandidateEvidence,
    )
    def get_evidence(
        candidate_id: UUID, evidence_id: UUID
    ) -> PersistedCandidateEvidence:
        evidence = store.get(candidate_id, evidence_id)
        if evidence is None:
            raise HTTPException(status_code=404, detail="Evidence not found")
        return evidence

    @application.patch(
        "/candidates/{candidate_id}/evidence/{evidence_id}/verification",
        response_model=PersistedCandidateEvidence,
    )
    def update_verification(
        candidate_id: UUID, evidence_id: UUID, payload: VerificationUpdate
    ) -> PersistedCandidateEvidence:
        evidence = store.update_verification(
            candidate_id, evidence_id, payload.verification_status
        )
        if evidence is None:
            raise HTTPException(status_code=404, detail="Evidence not found")
        return evidence

    return application


app = create_app()
