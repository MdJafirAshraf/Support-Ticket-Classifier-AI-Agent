from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from schemas.ticket import TicketCreate, TicketResponse
from services import sanitizer, deep_classifier, router as team_router
from services.cost_tracker import compute_cost
from models import Ticket, Classification, Assignment
from core.logging_config import get_logger
from core.config import get_settings

router = APIRouter(prefix="/tickets", tags=["tickets"])
logger = get_logger("tickets")

settings = get_settings()

@router.post("", response_model=TicketResponse)
def create_ticket(payload: TicketCreate, request: Request, db: Session = Depends(get_db)):
    # Set by RequestLoggingMiddleware
    request_id = request.state.request_id

    # 1. sanitize — PII masking + injection scan, before anything else sees the text
    sanitized_body, pii_flagged, injection_flagged = sanitizer.sanitize(payload.body)

    ticket = Ticket(
        channel=payload.channel,
        raw_subject=payload.subject,
        raw_body=payload.body,
        sanitized_body=sanitized_body,
        pii_flagged=pii_flagged,
        injection_flagged=injection_flagged,
        customer_email=payload.customer_email,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    result, escalation, usage = deep_classifier.classify_and_escalate(
        sanitized_body,
        request_id=request_id,
        ticket_id=ticket.id,
    )

    is_fallback = False  # deep-agent path has no retry/fallback logic yet — see note below
    prompt_version = "deep_agent_v1"
    model_name = settings.classifier_model

    # usage sums tokens across all 3 model calls (coordinator + classifier + escalation),
    # not just one — cost_usd below reflects the full delegation, not a single call
    cost_usd = compute_cost(usage["input_tokens"], usage["output_tokens"])

    classification = Classification(
        ticket_id=ticket.id,
        category=result.category,
        priority=result.priority,
        sentiment=result.sentiment,
        confidence=result.confidence,
        prompt_version=prompt_version,
        model_name=model_name,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cost_usd=cost_usd,
        is_fallback=is_fallback,
    )
    db.add(classification)
    db.commit()
    db.refresh(classification)

    # 3. route — escalation subagent's decision takes priority over the
    #    deterministic category -> team lookup
    final_team = "support_team" if escalation.escalate else team_router.resolve_team(result)

    assignment = Assignment(
        ticket_id=ticket.id,
        classification_id=classification.id,
        assigned_team=final_team,
    )
    db.add(assignment)
    db.commit()

    logger.info(f"ticket={ticket.id} category={result.category} "
                f"team={final_team} confidence={result.confidence} escalate={escalation.escalate}")

    return TicketResponse(
        id=ticket.id,
        channel=ticket.channel,
        category=result.category,
        priority=result.priority,
        sentiment=result.sentiment,
        assigned_team=final_team,
        confidence=result.confidence,
        escalated=escalation.escalate,
    )
