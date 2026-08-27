from langchain_core.tools import tool
from sqlalchemy import desc
from database import SessionLocal
from models import Ticket, Classification
from core.logging_config import get_logger

logger = get_logger("tools.customer")


@tool
def get_last_ticket_details(customer_id: str) -> dict:
    """
    Look up this customer's most recent prior support ticket, if one
    exists. Use this before classifying to check whether the customer
    has raised this same issue before — repeat tickets about the same
    problem are a signal worth factoring into priority and escalation.

    Args:
        customer_id: The customer's unique ID (not their email).

    Returns:
        A dict describing the last ticket (category, priority, status,
        how long ago it was created), or {"found": False} if this is
        a first-time customer.
    """
    db = SessionLocal()
    try:
        last_ticket = (
            db.query(Ticket)
            .filter(Ticket.customer_id == customer_id)
            .order_by(desc(Ticket.created_at))
            .first()
        )
        if last_ticket is None:
            return {"found": False, "message": "No prior tickets for this customer."}

        # Pull the most recent classification for that ticket, if any —
        # the ticket alone doesn't say what it was about or how it was handled
        last_classification = (
            db.query(Classification)
            .filter(Classification.ticket_id == last_ticket.id)
            .order_by(desc(Classification.created_at))
            .first()
        )

        result = {
            "found": True,
            "ticket_id": last_ticket.id,
            "subject": last_ticket.raw_subject,
            "created_at": last_ticket.created_at.isoformat(),
            "category": last_classification.category if last_classification else None,
            "priority": last_classification.priority if last_classification else None,
        }
        logger.info(f"customer_id={customer_id} last_ticket={last_ticket.id}")
        return result

    finally:
        db.close()