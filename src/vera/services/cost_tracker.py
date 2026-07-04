"""Per-thread cost tracking across agent invocations."""

from dataclasses import dataclass, field

from vera.core.pricing import calculate_cost


@dataclass
class TurnCost:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    cost: float = 0.0


@dataclass
class ThreadCostTracker:
    model: str
    turns: list[TurnCost] = field(default_factory=list)

    @property
    def accumulated_cost(self) -> float:
        return round(sum(t.cost for t in self.turns), 6)

    @property
    def total_input_tokens(self) -> int:
        return sum(t.input_tokens for t in self.turns)

    @property
    def total_output_tokens(self) -> int:
        return sum(t.output_tokens for t in self.turns)

    def add_turn(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_creation_input_tokens: int = 0,
        cache_read_input_tokens: int = 0,
    ) -> TurnCost:
        cost = calculate_cost(
            self.model,
            input_tokens,
            output_tokens,
            cache_creation_input_tokens,
            cache_read_input_tokens,
        )
        turn = TurnCost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=cache_creation_input_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
            cost=cost,
        )
        self.turns.append(turn)
        return turn


def extract_usage_from_result(result: dict) -> dict:
    """Extract aggregate token usage from all AI messages in the agent result."""
    total = {"input_tokens": 0, "output_tokens": 0,
             "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
    for msg in result.get("messages", []):
        metadata = getattr(msg, "usage_metadata", None)
        if not metadata:
            continue
        total["input_tokens"] += metadata.get("input_tokens", 0) or 0
        total["output_tokens"] += metadata.get("output_tokens", 0) or 0
        details = metadata.get("input_token_details") or {}
        total["cache_creation_input_tokens"] += details.get("cache_creation", 0) or 0
        total["cache_read_input_tokens"] += details.get("cache_read", 0) or 0
    return total
