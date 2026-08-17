from datetime import datetime
from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    """What the web form / email webhook submits."""
    channel: str = Field(description="'web_form' or 'email'")
    subject: str | None = None
    body: str
    customer_email: str | None = None


class TicketResponse(BaseModel):
    id: str
    channel: str
    category: str
    priority: str
    sentiment: str
    assigned_team: str
    confidence: float
    escalated: bool
    reply_hint: str | None = None

    class Config:
        from_attributes = True