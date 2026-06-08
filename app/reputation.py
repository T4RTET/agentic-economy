from __future__ import annotations

from dataclasses import dataclass
import math


SUCCESS_OUTCOME = "success"
FAILED_OUTCOMES = {"failed", "error"}


@dataclass(frozen=True)
class ReputationEvent:
    outcome: str
    value_usd: float = 0


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


def calculate_reputation(
    events: list[ReputationEvent],
    complaints: list[ReputationComplaint],
) -> ReputationResult:
    score = 50.0
    successful_volume = 0.0

    for event in events:
        value = max(float(event.value_usd or 0), 0)
        if event.outcome == SUCCESS_OUTCOME:
            successful_volume += value
            score += 4
            score += min(math.log10(value + 1) * 2, 8)
        elif event.outcome in FAILED_OUTCOMES:
            score -= 8 if event.outcome == "failed" else 12

    for complaint in complaints:
        score -= _complaint_penalty(complaint.severity, complaint.status)

    trust_score = int(round(max(0, min(100, score))))
    risk_level = _risk_level(trust_score)

    return ReputationResult(
        trust_score=trust_score,
        risk_level=risk_level,
        recommended_wallet_limit_usd=_wallet_limit(risk_level, successful_volume),
        successful_volume_usd=round(successful_volume, 2),
        total_events=len(events),
        complaint_count=len([item for item in complaints if item.status != "dismissed"]),
    )


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
    return base_penalty


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
