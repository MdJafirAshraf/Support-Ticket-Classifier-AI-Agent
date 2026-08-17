import time
from agents import deep_agent
from schemas.classification import TicketClassification, EscalationDecision
from core.logging_config import get_logger

logger = get_logger("deep_classifier")


def classify_and_escalate(sanitized_body: str) -> tuple[TicketClassification, EscalationDecision, dict]:
    """
    Runs the coordinator, which delegates to classifier then escalation.
    Returns (classification, escalation_decision, usage_dict).
    usage_dict sums tokens across ALL model calls (coordinator + both
    subagents) — needed since cost_tracker now has to account for
    three LLM calls per ticket, not one.
    """
    start = time.perf_counter()
    result = deep_agent.invoke({"messages": [{"role": "user", "content": sanitized_body}]})
    duration = time.perf_counter() - start

    # Structured outputs land in each subagent's state; deepagents surfaces
    # them via the task tool results. Pull the last classifier/escalation
    # structured_response out of the run's intermediate state.
    classification = result.get("classifier_result")       # wire via middleware/state capture
    escalation = result.get("escalation_result")

    if classification is None or escalation is None:
        logger.error("Deep agent run did not produce both subagent results")
        raise ValueError("Incomplete deep agent run")

    usage = _sum_usage(result)  # sum input/output tokens across all calls in result["messages"]

    logger.info(f"deep agent run complete duration={duration:.3f}s escalate={escalation.escalate}")
    return classification, escalation, usage


def _sum_usage(result: dict) -> dict:
    input_tokens = output_tokens = 0
    for msg in result.get("messages", []):
        meta = getattr(msg, "usage_metadata", None)
        if meta:
            input_tokens += meta.get("input_tokens", 0)
            output_tokens += meta.get("output_tokens", 0)
    return {"input_tokens": input_tokens, "output_tokens": output_tokens}