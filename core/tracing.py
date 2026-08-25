import os
from core.config import get_settings
from core.logging_config import get_logger

logger = get_logger("tracing")


def configure_tracing() -> None:
    """
    Pushes LangSmith settings into os.environ, since pydantic-settings
    only populates our own Settings object — it does NOT set real
    environment variables, which is what LangGraph's tracing hooks
    actually read from.

    Must run BEFORE agent/deep_agent.py is imported anywhere, since
    the model/graph objects are constructed at import time.
    """
    settings = get_settings()

    if not settings.langsmith_tracing:
        logger.info("LangSmith tracing disabled (langsmith_tracing=False)")
        return

    if not settings.langsmith_api_key:
        logger.warning(
            "LANGSMITH_TRACING is enabled but no langsmith_api_key is set — "
            "tracing will silently stay off. Add LANGSMITH_API_KEY to .env."
        )
        return

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project

    # Some langsmith/langchain versions still check the older var names —
    # setting both costs nothing and avoids a version-specific silent miss.
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

    logger.info(f"LangSmith tracing enabled — project='{settings.langsmith_project}'")