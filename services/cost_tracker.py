from core.config import get_settings

settings = get_settings()


def compute_cost(input_tokens: int, output_tokens: int) -> float:
    """Computes USD cost for one classification call based on configured per-token rates."""
    return round(
        input_tokens * settings.cost_per_input_token
        + output_tokens * settings.cost_per_output_token,
        6,
    )