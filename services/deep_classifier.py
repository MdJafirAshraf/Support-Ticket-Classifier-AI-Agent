import time, json
from langchain_core.messages import AIMessage, ToolMessage

from agents import deep_agent
from schemas.classification import TicketClassification, EscalationDecision
from core.logging_config import get_logger

logger = get_logger("deep_classifier")


def classify_and_escalate(
    sanitized_body: str,
    request_id: str,
    ticket_id: str,
    customer_id: str,
) -> tuple[TicketClassification, EscalationDecision, dict]:
    start = time.perf_counter()

    result = deep_agent.invoke(
        {
            "messages": [{
                "role": "user",
                "content": f"[customer_id: {customer_id}]\n\n{sanitized_body}",
            }]
        },
        config={
            "run_name": "ticket_classification",
            "tags": ["ticket-pipeline", "production"],
            "metadata": {"request_id": request_id, "ticket_id": ticket_id, "customer_id": customer_id},
        },
    )
    duration = time.perf_counter() - start

    subagent_results = _extract_subagent_results(result.get("messages", []))
    classification_raw = subagent_results.get("classifier")
    escalation_raw = subagent_results.get("escalation")

    if classification_raw is None or escalation_raw is None:
        logger.error(f"[{request_id}] Deep agent run did not produce both subagent results")
        raise ValueError("Incomplete deep agent run")

    classification = TicketClassification.model_validate(classification_raw)
    escalation = EscalationDecision.model_validate(escalation_raw)
    usage = _sum_usage(result)

    logger.info(f"[{request_id}] deep agent run complete duration={duration:.3f}s escalate={escalation.escalate}")
    return classification, escalation, usage


def _extract_subagent_results(messages: list) -> dict:
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
            if subagent_type:
                try:
                    results[subagent_type] = json.loads(_get_text(msg.content))
                except (json.JSONDecodeError, TypeError) as exc:
                    logger.warning(f"Could not parse structured output for '{subagent_type}': {exc}")
    return results


def _get_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(block.get("text", "") for block in content if isinstance(block, dict))
    return str(content)


def _sum_usage(result: dict) -> dict:
    input_tokens = output_tokens = 0
    for msg in result.get("messages", []):
        meta = getattr(msg, "usage_metadata", None)
        if meta:
            input_tokens += meta.get("input_tokens", 0)
            output_tokens += meta.get("output_tokens", 0)
    return {"input_tokens": input_tokens, "output_tokens": output_tokens}