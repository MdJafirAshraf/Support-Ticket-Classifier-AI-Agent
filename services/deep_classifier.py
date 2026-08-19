import json
import time
from langchain_core.messages import AIMessage, ToolMessage

from agents import deep_agent
from schemas.classification import TicketClassification, EscalationDecision
from core.logging_config import get_logger

logger = get_logger("deep_classifier")


def _extract_subagent_results(messages: list) -> dict:
    """
    Maps each 'task' tool call's tool_call_id -> subagent_type (from the
    AIMessage that issued it), then matches that id to the corresponding
    ToolMessage to pull out its JSON-serialized structured_response.
    """
    call_id_to_subagent = {}
    for msg in messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                if tc.get("name") == "task":
                    call_id_to_subagent[tc["id"]] = tc["args"].get("subagent_type")

    results = {}
    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.name == "task":
            subagent_type = call_id_to_subagent.get(msg.tool_call_id)
            if not subagent_type:
                continue
            try:
                results[subagent_type] = json.loads(msg.content)
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning(f"Could not parse structured output for '{subagent_type}': {exc}")

    return results


def classify_and_escalate(sanitized_body: str) -> tuple[TicketClassification, EscalationDecision, dict]:
    start = time.perf_counter()
    result = deep_agent.invoke({"messages": [{"role": "user", "content": sanitized_body}]})
    duration = time.perf_counter() - start

    logger.info(f"deep agent raw result: {result}")

    subagent_results = _extract_subagent_results(result.get("messages", []))
    classification_raw = subagent_results.get("classifier")
    escalation_raw = subagent_results.get("escalation")

    if classification_raw is None or escalation_raw is None:
        logger.error(f"Deep agent run did not produce both subagent results: {subagent_results.keys()}")
        raise ValueError("Incomplete deep agent run")

    classification = TicketClassification.model_validate(classification_raw)
    escalation = EscalationDecision.model_validate(escalation_raw)

    usage = _sum_usage(result)

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