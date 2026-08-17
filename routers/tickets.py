from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas.ticket import TicketCreate, TicketResponse
from services import sanitizer, classifier, validator, router as team_router
from services.cost_tracker import compute_cost
from models import Ticket, Classification, Assignment
from core.logging_config import get_logger

router = APIRouter(prefix="/tickets", tags=["tickets"])
logger = get_logger("tickets")


@router.post("", response_model=TicketResponse)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    # 1. sanitize — PII masking + injection scan, before anything else sees the text
    sanitized_body, pii_flagged, injection_flagged = sanitizer.sanitize(payload.body)

    ticket = Ticket(
        channel=payload.channel,
        raw_subject=payload.subject,
        raw_body=payload.body,
        sanitized_body=sanitized_body,
        customer_email=payload.customer_email,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # 2. classify — the one LLM call in the pipeline
    llm_result, usage, prompt_version, model_name = classifier.classify_and_escalate(sanitized_body)

    # 3. validate — schema check, confidence gate, retry/fallback happens inside
    result, is_fallback = validator.validate(llm_result, sanitized_body)

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

    # 4. route — deterministic category -> team, escalation already folded into confidence gate
    final_team = team_router.resolve_team(result)
    assignment = Assignment(
        ticket_id=ticket.id,
        classification_id=classification.id,
        assigned_team=final_team,
    )
    db.add(assignment)
    db.commit()

    logger.info(f"ticket={ticket.id} category={result.category} "
                f"team={final_team} confidence={result.confidence} fallback={is_fallback}")

    return TicketResponse(
        id=ticket.id,
        channel=ticket.channel,
        category=result.category,
        priority=result.priority,
        sentiment=result.sentiment,
        assigned_team=final_team,
        confidence=result.confidence,
        escalated=(final_team == "support_team" and result.category != "other"),
    )