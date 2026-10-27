"""Models for candidate evidence and evidence-backed resume claims."""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VerificationStatus(str, Enum):
    """Whether the candidate has checked an evidence item against its source."""

    UNVERIFIED = "unverified"
    VERIFIED = "verified"


class CandidateEvidence(BaseModel):
    """A candidate claim with a traceable source and review status."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    # None remains valid for older in-memory callers; persisted evidence always
    # receives an owner from the candidate-scoped storage operation.
    candidate_id: UUID | None = None
    claim: str = Field(min_length=1)
    source: str = Field(min_length=1)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("claim", "source")
    @classmethod
    def require_non_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must contain non-whitespace characters.")
        return value


class PersistedCandidateEvidence(CandidateEvidence):
    """Evidence loaded from storage, which always has a candidate owner."""

    candidate_id: UUID


class EvidenceCreate(BaseModel):
    """Fields a candidate may provide when adding evidence."""

    model_config = ConfigDict(extra="forbid")

    claim: str = Field(min_length=1)
    source: str = Field(min_length=1)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("claim", "source")
    @classmethod
    def require_non_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must contain non-whitespace characters.")
        return value


class VerificationUpdate(BaseModel):
    """Candidate-reviewed verification state update."""

    model_config = ConfigDict(extra="forbid")

    verification_status: VerificationStatus


class ResumeClaim(BaseModel):
    """A proposed resume statement and IDs of the evidence supporting it."""

    claim: str = Field(min_length=1)
    evidence_ids: list[UUID] = Field(min_length=1)
