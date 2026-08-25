from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # LLM
    groq_api_key: str
    gemini_api_key: str
    classifier_model: str = "gemini-3.5-flash-lite"
    classifier_temperature: float = 0.2
    classifier_max_output_tokens: int = 512

    # LangSmith
    langsmith_tracing: bool = True
    langsmith_api_key: str | None = None
    langsmith_project: str = "support-ticket-classifier"

    # Pipeline behavior
    confidence_threshold: float = 0.6
    max_classification_retries: int = 1

    # Cost tracking — per-token USD rates for the configured model
    cost_per_input_token: float = 0.075 / 1_000_000
    cost_per_output_token: float = 0.30 / 1_000_000

    # Database
    database_url: str = "mysql+pymysql://root:tiger@localhost:3306/tickets"

    # App
    app_name: str = "Support Ticket Classifier"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()