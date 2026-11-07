"""HTTP entry point for the minimal CareerPilot API."""

from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request

from app.models.evidence import (
    EvidenceCreate,
    PersistedCandidateEvidence,
    VerificationUpdate,
)
from app.services.auth import (
    AuthConfigurationError,
    AuthServiceUnavailable,
    InvalidAccessToken,
    SupabaseAuthConfig,
    SupabaseTokenVerifier,
    TokenVerifier,
)
from app.services.evidence_store import EvidenceStore

bearer_scheme = HTTPBearer(auto_error=False)


def authenticated_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UUID:
    """Verify the bearer token and return its Supabase user UUID."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid bearer token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    verifier = request.app.state.token_verifier
    if verifier is None:
        try:
            verifier = SupabaseTokenVerifier(SupabaseAuthConfig.from_environment())
        except AuthConfigurationError as error:
            # The message contains only the missing setting name, never its value.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase authentication is not configured",
            ) from error
        request.app.state.token_verifier = verifier

    try:
        return verifier.verify(credentials.credentials)
    except InvalidAccessToken as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except AuthServiceUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase authentication is temporarily unavailable",
        ) from error


def require_candidate_owner(candidate_id: UUID, user_id: UUID) -> None:
    """Candidate IDs map directly to Supabase auth.users.id (the JWT sub)."""

    if candidate_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidate ID does not match the authenticated user",
        )


def create_app(
    evidence_store: EvidenceStore | None = None,
    token_verifier: TokenVerifier | None = None,
) -> FastAPI:
    """Build the API; tests can supply isolated storage and a token verifier."""

    application = FastAPI(
        title="CareerPilot API",
        description=(
            "Learning foundation API. Supabase bearer tokens protect evidence "
            "routes; candidate IDs must match the verified user ID. This API "
            "is not production-secure."
        ),
        version="0.2.0",
    )
    store = evidence_store or EvidenceStore()
    application.state.token_verifier = token_verifier

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
        candidate_id: UUID,
        payload: EvidenceCreate,
        user_id: UUID = Depends(authenticated_user_id),
    ) -> PersistedCandidateEvidence:
        require_candidate_owner(candidate_id, user_id)
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
    def list_evidence(
        candidate_id: UUID,
        user_id: UUID = Depends(authenticated_user_id),
    ) -> list[PersistedCandidateEvidence]:
        require_candidate_owner(candidate_id, user_id)
        return store.list_for_candidate(candidate_id)

    @application.get(
        "/candidates/{candidate_id}/evidence/{evidence_id}",
        response_model=PersistedCandidateEvidence,
    )
    def get_evidence(
        candidate_id: UUID,
        evidence_id: UUID,
        user_id: UUID = Depends(authenticated_user_id),
    ) -> PersistedCandidateEvidence:
        require_candidate_owner(candidate_id, user_id)
        evidence = store.get(candidate_id, evidence_id)
        if evidence is None:
            raise HTTPException(status_code=404, detail="Evidence not found")
        return evidence

    @application.patch(
        "/candidates/{candidate_id}/evidence/{evidence_id}/verification",
        response_model=PersistedCandidateEvidence,
    )
    def update_verification(
        candidate_id: UUID,
        evidence_id: UUID,
        payload: VerificationUpdate,
        user_id: UUID = Depends(authenticated_user_id),
    ) -> PersistedCandidateEvidence:
        require_candidate_owner(candidate_id, user_id)
        evidence = store.update_verification(
            candidate_id, evidence_id, payload.verification_status
        )
        if evidence is None:
            raise HTTPException(status_code=404, detail="Evidence not found")
        return evidence

    return application


app = create_app()
