from pydantic import ValidationError

from schemas.classification import TicketClassification
from core.config import get_settings
from core.logging_config import get_logger
from services import classifier

settings = get_settings()
logger = get_logger("validator")


def fallback_classification() -> TicketClassification:
    """Safe default when the model can't produce a usable result, even after retry."""
    return TicketClassification(
        category="other",
        assigned_team="support_team",
        priority="medium",
        sentiment="neutral",
        confidence=0.0,
    )


def validate(llm_result: dict | None, sanitized_body: str) -> tuple[TicketClassification, bool]:
    """
    Validates the LLM's raw output against the schema.
    Retries once on failure, then falls back to a safe default.
    Returns (validated_result, is_fallback).
    """
    result = _try_validate(llm_result)
    if result is not None:
        return result, False

    logger.warning("Initial classification invalid or missing — retrying once")
    retry_result, _, _, _ = classifier.classify(sanitized_body)
    result = _try_validate(retry_result)
    if result is not None:
        return result, False

    logger.error("Retry also failed validation — using fallback classification")
    return fallback_classification(), True


def _try_validate(raw: dict | None) -> TicketClassification | None:
    if raw is None:
        return None
    try:
        return TicketClassification.model_validate(raw)
    except ValidationError as exc:
        logger.warning(f"Schema validation failed: {exc}")
        return None