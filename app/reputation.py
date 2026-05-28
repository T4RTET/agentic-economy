from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Any


SUCCESS_OUTCOME = "success"
FAILED_OUTCOMES = {"failed", "error"}


@dataclass(frozen=True)
class ReputationEvent:
    outcome: str
    value_usd: float = 0
    created_at: str | None = None
    category: str | None = None
    tx_hash: str | None = None


@dataclass(frozen=True)
class ReputationComplaint:
    severity: str
    status: str = "open"


@dataclass(frozen=True)
class ReputationResult:
    trust_score: int
    risk_level: str
    recommended_wallet_limit_usd: int
    successful_volume_usd: float
    total_events: int
    complaint_count: int
    score_breakdown: dict[str, Any]


def calculate_reputation(
    events: list[ReputationEvent],
    complaints: list[ReputationComplaint],
    agent_created_at: str | None = None,
    wallet_verified: bool = False,
) -> ReputationResult:
    successful_events = [event for event in events if event.outcome == SUCCESS_OUTCOME]
    failed_events = [event for event in events if event.outcome in FAILED_OUTCOMES]
    successful_volume = sum(max(float(event.value_usd or 0), 0) for event in successful_events)
    active_complaints = [item for item in complaints if item.status != "dismissed"]

    creation_score = _creation_history_score(agent_created_at)
    identity_score = _identity_verification_score(wallet_verified)
    count_score = _transaction_count_score(len(events))
    quality_score = _transaction_quality_score(events)
    frequency_score = _transaction_frequency_score(events)
    onchain_score = _onchain_evidence_score(events)
    diversity_score = _category_diversity_score(events)
    volume_score = _volume_experience_score(successful_volume)
    complaint_penalty = sum(_complaint_penalty(complaint.severity, complaint.status) for complaint in complaints)
    complaint_health_score = 10 - complaint_penalty

    score = (
        creation_score
        + identity_score
        + count_score
        + quality_score
        + frequency_score
        + onchain_score
        + diversity_score
        + volume_score
        + complaint_health_score
    )
    trust_score = int(round(max(0, min(100, score))))
    risk_level = _risk_level(trust_score)

    return ReputationResult(
        trust_score=trust_score,
        risk_level=risk_level,
        recommended_wallet_limit_usd=_wallet_limit(risk_level, successful_volume),
        successful_volume_usd=round(successful_volume, 2),
        total_events=len(events),
        complaint_count=len(active_complaints),
        score_breakdown={
            "creation_history": {
                "score": round(creation_score, 2),
                "max": 10,
                "description": "Older wallet-linked agents get more trust than freshly created ones.",
            },
            "wallet_verification": {
                "score": round(identity_score, 2),
                "max": 10,
                "description": "Wallet ownership verified by signed message increases confidence.",
            },
            "transaction_count": {
                "score": round(count_score, 2),
                "max": 15,
                "description": "More recorded transactions/actions give more evidence.",
            },
            "transaction_quality": {
                "score": round(quality_score, 2),
                "max": 30,
                "description": "Success rate and handled value increase trust; failed/error outcomes reduce it.",
            },
            "transaction_frequency": {
                "score": round(frequency_score, 2),
                "max": 10,
                "description": "Recent consistent activity is better than an inactive passport.",
            },
            "onchain_evidence": {
                "score": round(onchain_score, 2),
                "max": 10,
                "description": "Actions with transaction hashes are easier to verify.",
            },
            "task_diversity": {
                "score": round(diversity_score, 2),
                "max": 5,
                "description": "Successful activity across multiple task categories reduces single-use uncertainty.",
            },
            "value_experience": {
                "score": round(volume_score, 2),
                "max": 10,
                "description": "Higher successfully handled value adds confidence with a capped impact.",
            },
            "complaint_health": {
                "score": round(complaint_health_score, 2),
                "max": 10,
                "penalty_applied": round(complaint_penalty, 2),
                "description": "Clean complaint history adds trust; open and confirmed complaints reduce it.",
            },
        },
    )


def _creation_history_score(agent_created_at: str | None) -> float:
    age_days = _age_days(agent_created_at)
    if age_days >= 90:
        return 10
    if age_days >= 30:
        return 8
    if age_days >= 7:
        return 6
    if age_days >= 1:
        return 4
    return 5


def _identity_verification_score(wallet_verified: bool) -> float:
    return 10 if wallet_verified else 0


def _transaction_count_score(total_events: int) -> float:
    return min(total_events * 3, 15)


def _transaction_quality_score(events: list[ReputationEvent]) -> float:
    if not events:
        return 15

    success_count = len([event for event in events if event.outcome == SUCCESS_OUTCOME])
    failed_count = len([event for event in events if event.outcome in FAILED_OUTCOMES])
    success_rate = success_count / len(events)
    successful_volume = sum(max(float(event.value_usd or 0), 0) for event in events if event.outcome == SUCCESS_OUTCOME)
    volume_signal = min(math.log10(successful_volume + 1) * 2, 6)
    failure_penalty = min(failed_count * 4, 12)
    return max(0, min(30, success_rate * 28 + volume_signal - failure_penalty))


def _transaction_frequency_score(events: list[ReputationEvent]) -> float:
    if not events:
        return 0

    now = datetime.now(timezone.utc)
    recent_count = 0
    for event in events:
        event_time = _parse_datetime(event.created_at)
        if event_time is None or (now - event_time).days <= 30:
            recent_count += 1
    return min(recent_count * 3, 10)


def _onchain_evidence_score(events: list[ReputationEvent]) -> float:
    if not events:
        return 0
    tx_backed_events = len([event for event in events if event.tx_hash])
    return min((tx_backed_events / len(events)) * 10, 10)


def _category_diversity_score(events: list[ReputationEvent]) -> float:
    successful_categories = {
        event.category
        for event in events
        if event.outcome == SUCCESS_OUTCOME and event.category
    }
    return min(len(successful_categories) * 2, 5)


def _volume_experience_score(successful_volume_usd: float) -> float:
    if successful_volume_usd <= 0:
        return 0
    return min(math.log10(successful_volume_usd + 1) * 2.5, 10)


def _complaint_penalty(severity: str, status: str) -> float:
    if status == "dismissed":
        return 0

    base_penalty = {
        "low": 4,
        "medium": 10,
        "high": 18,
    }.get(severity, 8)

    if status == "confirmed":
        return base_penalty * 1.5
    return min(base_penalty, 30)


def _risk_level(trust_score: int) -> str:
    if trust_score >= 75:
        return "Low"
    if trust_score >= 50:
        return "Medium"
    return "High"


def _wallet_limit(risk_level: str, successful_volume_usd: float) -> int:
    base_limit = {
        "Low": 5000,
        "Medium": 1000,
        "High": 100,
    }[risk_level]
    volume_boost = min(successful_volume_usd * 0.1, base_limit)
    return int(round(base_limit + volume_boost))


def _age_days(value: str | None) -> int:
    created_at = _parse_datetime(value)
    if created_at is None:
        return 0
    return max((datetime.now(timezone.utc) - created_at).days, 0)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
