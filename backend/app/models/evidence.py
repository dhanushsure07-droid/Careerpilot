"""Models for candidate evidence and evidence-backed resume claims."""

from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class VerificationStatus(str, Enum):
    """Whether the candidate has checked an evidence item against its source."""

    UNVERIFIED = "unverified"
    VERIFIED = "verified"


class CandidateEvidence(BaseModel):
    """A candidate claim with a traceable source and review status."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    claim: str = Field(min_length=1)
    source: str = Field(min_length=1)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    metadata: dict[str, str] = Field(default_factory=dict)


class ResumeClaim(BaseModel):
    """A proposed resume statement and IDs of the evidence supporting it."""

    claim: str = Field(min_length=1)
    evidence_ids: list[UUID] = Field(min_length=1)
