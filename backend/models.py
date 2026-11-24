"""The shapes of the backend's requests and responses."""

from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["waiting", "in_progress", "awaiting_sign_off", "decided"]
Outcome = Literal["approve", "decline", "refer"]
StepKind = Literal["tool_call", "tool_result", "reply"]


class Item(BaseModel):
    description: str
    category: str
    amount: float


class Document(BaseModel):
    name: str
    type: str
    content: str


class Decision(BaseModel):
    decision: Outcome
    payout: float
    reason: str
    policy_section: str
    decided_at: str


class SignOff(BaseModel):
    handler_id: str
    handler_name: str
    signed_at: str


class Payment(BaseModel):
    amount: float
    paid_at: str


class ClaimSummary(BaseModel):
    claim_id: str
    claim_type: str
    summary: str
    customer_name: str
    submitted_on: str
    amount_claimed: float
    status: Status
    decision: Outcome | None
    payout: float | None


class Claim(BaseModel):
    claim_id: str
    policy_id: str
    customer_id: str
    customer_name: str
    claim_type: str
    submitted_on: str
    incident_date: str
    incident_location: str
    summary: str
    story: str
    items: list[Item]
    amount_claimed: float
    documents: list[Document]
    status: Status
    decision: Decision | None
    sign_off: SignOff | None
    payment: Payment | None


class Trip(BaseModel):
    destination: str
    departs_on: str
    returns_on: str
    trip_cost: float


class Policy(BaseModel):
    policy_id: str
    customer_id: str
    plan: str
    add_ons: list[str]
    purchased_on: str
    sold_through: str
    trip: Trip
    travelers: list[str]
    status: str


class PreviousClaim(BaseModel):
    claim_id: str
    filed_on: str
    incident_date: str
    claim_type: str
    summary: str
    outcome: str
    amount_paid: float


class Plan(BaseModel):
    plan: str
    name: str
    trip_cancellation_max: float
    trip_delay_waiting_hours: int
    trip_delay_max: float
    baggage_delay_waiting_hours: int
    baggage_delay_max: float
    baggage_max: float
    per_item_limit: float
    passport_max: float
    emergency_medical_max: float
    deductible: float


class AddOn(BaseModel):
    add_on: str
    name: str
    effect: str
    electronics_per_item_limit: float | None = None


class Plans(BaseModel):
    plans: list[Plan]
    deductible_applies_to: list[str]
    add_ons: list[AddOn]


class Handler(BaseModel):
    handler_id: str
    name: str
    role: str
    can_approve_over_limit: bool


class Step(BaseModel):
    step_id: int
    kind: StepKind
    text: str
    at: str


class Text(BaseModel):
    text: str


class StepIn(BaseModel):
    kind: StepKind
    text: str


class DecisionIn(BaseModel):
    decision: Outcome
    payout: float = Field(ge=0, description="The amount to pay, or 0 unless approving")
    reason: str = Field(min_length=1, description="Two or three sentences")
    policy_section: str = Field(
        min_length=1, description="The section of the policy wording, such as 3"
    )


class PaymentIn(BaseModel):
    amount: float = Field(gt=0)


class SignOffIn(BaseModel):
    handler_id: str
