from typing import Literal
from pydantic import BaseModel, Field


class TicketClassification(BaseModel):
    """The LLM's structured output — validated before anything trusts it."""
    category: Literal["billing", "shipping", "product_defect", "account", "refund", "other"] = Field(
        description="The single best-fit issue category."
    )
    assigned_team: Literal["billing_team", "logistics_team", "qa_team", "account_team", "support_team"] = Field(
        description="Which internal team should handle this."
    )
    priority: Literal["low", "medium", "high", "urgent"] = Field(
        description="How urgently this needs a response."
    )
    sentiment: Literal["negative", "neutral", "positive"] = Field(
        description="The customer's emotional tone."
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Model's confidence, 0 to 1.")


class EscalationDecision(BaseModel):
    escalate: bool = Field(description="Whether a human agent must take over.")
    reason: str = Field(description="Why this does or doesn't need escalation.")
    risk_flags: list[str] = Field(
        default_factory=list,
        description="Specific triggers found, e.g. 'refund_over_threshold', 'legal_threat', 'angry_tone'.",
    )