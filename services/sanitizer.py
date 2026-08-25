import re
import langsmith as ls
from core.logging_config import get_logger

logger = get_logger("sanitizer")

PII_PATTERNS = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "phone": r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "card_number": r"\b(?:\d[ -]*?){13,16}\b",
}

# Not exhaustive — a cheap first line of defense, not the only one.
# The real defense is the "treat ticket content as data" instruction
# inside the classifier prompt itself.
INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (all )?(previous|prior|above) instructions",
    r"you are now",
    r"new instructions?:",
    r"system prompt",
    r"act as (a|an)\s",
]


def redact_pii(text: str) -> tuple[str, bool]:
    """Returns (redacted_text, pii_found)."""
    redacted = text
    found = False
    for label, pattern in PII_PATTERNS.items():
        redacted, count = re.subn(pattern, f"[REDACTED_{label.upper()}]", redacted, flags=re.IGNORECASE)
        if count > 0:
            found = True
    return redacted, found


def detect_injection(text: str) -> bool:
    """Flags likely prompt-injection attempts. Does not block — just flags for logging + confidence downgrade."""
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in INJECTION_PATTERNS)


@ls.traceable(run_type="tool", name="sanitize_ticket")
def sanitize(raw_body: str) -> tuple[str, bool, bool]:
    """
    Full sanitization pass: PII redaction + injection scan.
    Returns (sanitized_body, pii_flagged, injection_flagged).
    """
    sanitized, pii_flagged = redact_pii(raw_body)
    injection_flagged = detect_injection(raw_body)

    if pii_flagged:
        logger.info("PII redacted from incoming ticket")
    if injection_flagged:
        logger.warning("Possible prompt injection pattern detected in incoming ticket")

    return sanitized, pii_flagged, injection_flagged