from app.reputation import ReputationComplaint, ReputationEvent, calculate_reputation


def test_successful_events_raise_score() -> None:
    result = calculate_reputation(
        [ReputationEvent(outcome="success", value_usd=1000)],
        [],
    )

    assert result.trust_score > 50
    assert result.risk_level == "Medium"
    assert "transaction_quality" in result.score_breakdown


def test_failed_events_lower_score() -> None:
    result = calculate_reputation(
        [ReputationEvent(outcome="failed", value_usd=1000), ReputationEvent(outcome="error")],
        [],
    )

    assert result.trust_score < 50
    assert result.risk_level == "High"


def test_weighted_complaints_reduce_score_by_severity_and_status() -> None:
    open_low = calculate_reputation([], [ReputationComplaint(severity="low", status="open")])
    confirmed_high = calculate_reputation([], [ReputationComplaint(severity="high", status="confirmed")])
    dismissed_high = calculate_reputation([], [ReputationComplaint(severity="high", status="dismissed")])

    assert confirmed_high.trust_score < open_low.trust_score
    assert dismissed_high.trust_score == calculate_reputation([], []).trust_score


def test_formula_uses_creation_count_quality_and_frequency() -> None:
    result = calculate_reputation(
        [
            ReputationEvent(outcome="success", value_usd=200),
            ReputationEvent(outcome="success", value_usd=300),
            ReputationEvent(outcome="failed", value_usd=50),
        ],
        [],
    )

    breakdown = result.score_breakdown
    assert breakdown["creation_history"]["max"] == 15
    assert breakdown["transaction_count"]["max"] == 20
    assert breakdown["transaction_quality"]["max"] == 40
    assert breakdown["transaction_frequency"]["max"] == 15


def test_score_is_clamped_to_zero_and_one_hundred() -> None:
    very_good = calculate_reputation(
        [ReputationEvent(outcome="success", value_usd=1000000) for _ in range(20)],
        [],
        agent_created_at="2025-01-01 00:00:00",
    )
    very_bad = calculate_reputation(
        [ReputationEvent(outcome="error") for _ in range(20)],
        [ReputationComplaint(severity="high", status="confirmed") for _ in range(10)],
    )

    assert very_good.trust_score == 100
    assert very_bad.trust_score == 0
