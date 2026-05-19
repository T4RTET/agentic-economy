from app.reputation import ReputationComplaint, ReputationEvent, calculate_reputation


def test_successful_events_raise_score() -> None:
    result = calculate_reputation(
        [ReputationEvent(outcome="success", value_usd=1000)],
        [],
    )

    assert result.trust_score > 50
    assert result.risk_level == "Medium"


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
    assert dismissed_high.trust_score == 50


def test_score_is_clamped_to_zero_and_one_hundred() -> None:
    very_good = calculate_reputation(
        [ReputationEvent(outcome="success", value_usd=1000000) for _ in range(20)],
        [],
    )
    very_bad = calculate_reputation(
        [ReputationEvent(outcome="error") for _ in range(20)],
        [ReputationComplaint(severity="high", status="confirmed") for _ in range(10)],
    )

    assert very_good.trust_score == 100
    assert very_bad.trust_score == 0
