from app.services.cost import estimate_cost


def test_cost_estimate_is_dramatized_100x():
    estimate = estimate_cost(card_count=1000, ai_assisted_count=1000)
    assert estimate.estimatedUsd == 2.52
    assert "100x" in estimate.note

