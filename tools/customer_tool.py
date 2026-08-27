from langchain_core.tools import tool
from sqlalchemy import desc
from database import SessionLocal
from models import Ticket, Classification
from core.logging_config import get_logger

logger = get_logger("tools.customer")


@tool
def get_last_ticket_details(customer_id: str) -> dict:
    """
    Look up this customer's most recent prior support ticket.

    The current ticket has already been inserted into the database, so
    this function intentionally excludes the latest ticket and returns
    the ticket immediately before it.

    Args:
        customer_id: The customer's unique ID.

    Returns:
        A dict containing the previous ticket details, or {"found": False}
        if the customer has no previous ticket.
    """
    db = SessionLocal()

    try:
        tickets = (
            db.query(Ticket)
            .filter(Ticket.customer_id == customer_id)
            .order_by(desc(Ticket.created_at))
            .limit(2)
            .all()
        )

        # No previous ticket
        if len(tickets) < 2:
            return {
                "found": False,
                "message": "No prior tickets for this customer."
            }

        # tickets[0] = current ticket
        # tickets[1] = most recent previous ticket
        last_ticket = tickets[1]

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
            "category": (
                last_classification.category
                if last_classification
                else None
            ),
            "priority": (
                last_classification.priority
                if last_classification
                else None
            ),
        }

        logger.info(f"customer_id={customer_id} " f"previous_ticket={last_ticket.id}")

        return result

    finally:
        db.close()