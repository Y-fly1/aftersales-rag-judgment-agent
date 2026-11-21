from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TicketType = Literal["refund", "return", "exchange", "repair", "complaint"]
ClaimReason = Literal["quality", "no_reason", "damaged", "missing", "not_as_described"]
LiableParty = Literal["merchant", "logistics", "buyer", "unknown"]
TicketAction = Literal[
    "full_refund", "partial_refund", "exchange", "repair", "reject", "reship", "manual"
]
Confidence = Literal["high", "medium", "low"]
TicketStatus = Literal[
    "judging", "pending_approval", "approved", "rejected", "executed", "closed"
]


class TicketCreate(BaseModel):
    order_no: str = Field(min_length=4, max_length=40)
    type: TicketType = "refund"
    reason: ClaimReason = "no_reason"
    description: str | None = Field(default=None, max_length=1000)


class PolicyRef(BaseModel):
    policy_no: str
    title: str | None = None
    id: int | None = None


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_no: str
    type: TicketType
    reason: ClaimReason | None = None
    description: str | None = None
    status: TicketStatus
    liable_party: LiableParty | None = None
    action: TicketAction | None = None
    action_amount: Decimal | None = None
    confidence: Confidence | None = None
    policy_refs: list[PolicyRef] = []
    reasoning: str | None = None
    need_human: bool = False
    human_decision: str | None = None
    created_at: datetime


class ApprovalRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    remark: str | None = Field(default=None, max_length=500)
