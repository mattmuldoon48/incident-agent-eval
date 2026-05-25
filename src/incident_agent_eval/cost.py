from dataclasses import dataclass


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0


MODEL_PRICING_PER_1M = {
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
}


def estimate_cost_usd(model: str, usage: TokenUsage) -> float:
    pricing = MODEL_PRICING_PER_1M.get(model, MODEL_PRICING_PER_1M["gpt-4.1-mini"])
    cost = (usage.input_tokens / 1_000_000) * pricing["input"]
    cost += (usage.output_tokens / 1_000_000) * pricing["output"]
    return round(cost, 6)
