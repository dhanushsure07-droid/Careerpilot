"""Models for approvals of specific proposed external actions."""

from pydantic import BaseModel, ConfigDict, Field


class ActionApproval(BaseModel):
    """Candidate approval tied to one action and its exact scope."""

    model_config = ConfigDict(frozen=True)

    proposed_action: str = Field(min_length=1)
    scope: dict[str, str]
    approved: bool = False
