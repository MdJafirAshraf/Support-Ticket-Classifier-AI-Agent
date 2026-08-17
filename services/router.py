from schemas.classification import TicketClassification
from core.config import get_settings
from core.logging_config import get_logger

settings = get_settings()
logger = get_logger("router")

CATEGORY_TEAM_MAP = {
    "billing": "billing_team",
    "shipping": "logistics_team",
    "product_defect": "qa_team",
    "account": "account_team",
    "refund": "billing_team",
    "other": "support_team",
}


def resolve_team(result: TicketClassification) -> str:
    """
    Deterministic category -> team lookup, with a confidence override:
    low-confidence classifications go to support_team for human review
    regardless of what category the model picked.
    """
    if result.confidence < settings.confidence_threshold:
        logger.info(f"confidence {result.confidence} below threshold "
                     f"{settings.confidence_threshold} — routing to support_team")
        return "support_team"

    return CATEGORY_TEAM_MAP.get(result.category, "support_team")