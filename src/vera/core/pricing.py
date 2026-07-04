"""Model pricing and cost calculation.

Prices are per million tokens (input / output).
Cache-write = 1.25x input price, cache-read = 0.1x input price.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float
    cache_write_multiplier: float = 1.25
    cache_read_multiplier: float = 0.10


MODEL_PRICING: dict[str, ModelPricing] = {
    "claude-sonnet-4-6": ModelPricing(
        input_per_million=3.00,
        output_per_million=15.00,
    ),
    "claude-haiku-4-5": ModelPricing(
        input_per_million=1.00,
        output_per_million=5.00,
    ),
    "claude-opus-4-8": ModelPricing(
        input_per_million=5.00,
        output_per_million=25.00,
    ),
}

CACHE_THRESHOLD_TOKENS: dict[str, int] = {
    "claude-sonnet-4-6": 1024,
    "claude-haiku-4-5": 4096,
    "claude-opus-4-8": 1024,
}


def get_pricing(model: str) -> ModelPricing:
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        msg = f"Unknown model {model!r}; add its pricing to MODEL_PRICING."
        raise KeyError(msg)
    return pricing


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_input_tokens: int = 0,
    cache_read_input_tokens: int = 0,
) -> float:
    """Calculate the cost of an LLM call from token usage.

    Accepts the same key names that LangChain's ``UsageMetadata`` exposes
    (``cache_creation_input_tokens``, ``cache_read_input_tokens``) so
    the caller can splat the dict returned by ``extract_usage_from_result``.
    """
    p = get_pricing(model)
    base_input = input_tokens - cache_creation_input_tokens - cache_read_input_tokens
    if base_input < 0:
        base_input = 0

    cost = (
        base_input * p.input_per_million
        + cache_creation_input_tokens * p.input_per_million * p.cache_write_multiplier
        + cache_read_input_tokens * p.input_per_million * p.cache_read_multiplier
        + output_tokens * p.output_per_million
    ) / 1_000_000
    return round(cost, 6)
