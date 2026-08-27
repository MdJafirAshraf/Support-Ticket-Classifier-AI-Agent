from langchain.agents.middleware import PIIMiddleware
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.rate_limiters import InMemoryRateLimiter
from deepagents import create_deep_agent, HarnessProfile, register_harness_profile

from core.config import get_settings
from tools.customer_tool import get_last_ticket_details
from schemas.classification import TicketClassification, EscalationDecision
from middleware.agent_middleware import LoggingMiddleware, IterationGuardMiddleware
from prompts.agent_prompts import COORDINATOR_PROMPT, CLASSIFIER_AGENT_PROMPT, ESCALATION_AGENT_PROMPT

settings = get_settings()

register_harness_profile(
    settings.classifier_model,
    HarnessProfile(
        excluded_tools=frozenset(
            {"ls", "read_file", "write_file", "edit_file", "delete", "glob", "grep"}
        ),
    ),
)

rate_limiter = InMemoryRateLimiter(requests_per_second=0.15, check_every_n_seconds=0.5, max_bucket_size=1)

model = ChatGoogleGenerativeAI(
    api_key=settings.gemini_api_key,
    model=settings.classifier_model,
    temperature=settings.classifier_temperature,
    rate_limiter=rate_limiter
)

classifier_agent = {
    "name": "classifier",
    "description": "Classifies a support ticket into category, team, priority, sentiment, confidence.",
    "system_prompt": CLASSIFIER_AGENT_PROMPT,
    "tools": [],
    "response_format": TicketClassification,
    "middleware": [LoggingMiddleware(agent_name="classifier")],
}

escalation_agent = {
    "name": "escalation",
    "description": "Decides whether a classified ticket needs human escalation.",
    "system_prompt": ESCALATION_AGENT_PROMPT,
    "tools": [],
    "response_format": EscalationDecision,
    "middleware": [LoggingMiddleware(agent_name="escalation")],
}

deep_agent = create_deep_agent(
    model=model,
    system_prompt=COORDINATOR_PROMPT,
    tools=[get_last_ticket_details],
    middleware=[
        LoggingMiddleware(agent_name="coordinator"), 
        IterationGuardMiddleware(max_iterations=3),
        PIIMiddleware("email", strategy="mask", apply_to_input=True),
        PIIMiddleware("phone", detector=r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", strategy="mask", apply_to_input=True),
        PIIMiddleware("credit_card", strategy="mask", apply_to_input=True),],
    subagents=[classifier_agent, escalation_agent],
)