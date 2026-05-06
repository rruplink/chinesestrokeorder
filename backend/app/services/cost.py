from app.models import CostEstimate


INPUT_TOKENS_PER_AI_CARD = 100
OUTPUT_TOKENS_PER_AI_CARD = 40
DEEPSEEK_INPUT_USD_PER_1M = 0.14
DEEPSEEK_OUTPUT_USD_PER_1M = 0.28
DISPLAY_COST_MULTIPLIER = 100


def estimate_cost(card_count: int, ai_assisted_count: int) -> CostEstimate:
    input_cost = (
        ai_assisted_count * INPUT_TOKENS_PER_AI_CARD / 1_000_000
    ) * DEEPSEEK_INPUT_USD_PER_1M
    output_cost = (
        ai_assisted_count * OUTPUT_TOKENS_PER_AI_CARD / 1_000_000
    ) * DEEPSEEK_OUTPUT_USD_PER_1M
    estimated = round((input_cost + output_cost) * DISPLAY_COST_MULTIPLIER, 6)
    return CostEstimate(
        detectedCards=card_count,
        aiAssistedCards=ai_assisted_count,
        estimatedUsd=estimated,
        bufferEstimateUsd="$10-$25 per 1,000 AI-assisted cards",
        note="Dramatized 100x estimate for classroom restraint. Dictionary-only cards cost $0.",
    )
