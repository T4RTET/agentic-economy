from __future__ import annotations

from typing import Any


MANTLE_CHAIN_IDS = {5000, 5001}
CRITERION_WEIGHTS = {
    "technical": 30,
    "ecosystem_fit": 20,
    "business_potential": 20,
    "innovation": 20,
    "user_experience": 10,
}


def build_mantle_readiness_report(passport: dict[str, Any]) -> dict[str, Any]:
    criteria = [
        _technical_score(passport),
        _ecosystem_score(passport),
        _business_score(passport),
        _innovation_score(passport),
        _ux_score(passport),
    ]
    overall_score = _risk_adjusted_score(sum(item["weighted_score"] for item in criteria), passport)
    grade = _grade(overall_score)
    return {
        "overall_score": overall_score,
        "grade": grade,
        "summary": _summary(overall_score, grade),
        "criteria": criteria,
        "next_steps": _next_steps(criteria),
    }


def build_project_mantle_readiness_report(passports: list[dict[str, Any]]) -> dict[str, Any]:
    if not passports:
        return {
            "overall_score": 0.0,
            "grade": "weak",
            "summary": "Mantle readiness score 0/100 (weak): no agent passports are available.",
            "agent_count": 0,
            "average_agent_score": 0.0,
            "grade_distribution": {},
            "risk_distribution": {},
            "top_agent": None,
            "judging_alignment": _empty_project_criteria(),
            "recommended_demo_flow": _recommended_demo_flow(),
            "next_steps": ["Seed demo data or create at least one wallet-linked agent passport."],
        }

    reports = [passport["mantle_readiness"] for passport in passports]
    agent_scores = [float(report["overall_score"]) for report in reports]
    average_agent_score = round(sum(agent_scores) / len(agent_scores), 2)
    best_index = max(range(len(passports)), key=lambda index: agent_scores[index])
    judging_alignment = _aggregate_criteria(reports)
    project_score = round((average_agent_score * 0.7) + (_criteria_average(judging_alignment) * 0.3), 2)
    grade = _grade(project_score)

    return {
        "overall_score": project_score,
        "grade": grade,
        "summary": f"Project Mantle readiness score {project_score}/100 ({grade}) across {len(passports)} agent passport(s).",
        "agent_count": len(passports),
        "average_agent_score": average_agent_score,
        "grade_distribution": _count_by(reports, "grade"),
        "risk_distribution": _risk_distribution(passports),
        "top_agent": passports[best_index]["agent"],
        "judging_alignment": judging_alignment,
        "recommended_demo_flow": _recommended_demo_flow(),
        "next_steps": _project_next_steps(passports, reports, judging_alignment),
    }


def _technical_score(passport: dict[str, Any]) -> dict[str, Any]:
    reputation = passport.get("reputation", {})
    events = passport.get("actions_history", [])
    complaints = passport.get("complaints", [])
    audit_log = passport.get("audit_log", [])

    raw = 4.0
    evidence = ["FastAPI backend exposes typed OpenAPI contracts."]
    recommendations: list[str] = []

    if reputation.get("score_breakdown"):
        raw += 1.5
        evidence.append("Trust Score has a transparent machine-readable score_breakdown.")
    else:
        recommendations.append("Expose score breakdown for judging transparency.")

    if events:
        raw += 1.0
        evidence.append(f"{len(events)} recorded agent action(s) available for passport review.")
    else:
        recommendations.append("Record at least one successful agent action in the demo.")

    if audit_log:
        raw += 1.0
        evidence.append("Audit log tracks important backend events.")

    if _tx_hash_count(events) > 0:
        raw += 1.0
        evidence.append("Some actions include transaction hashes for on-chain style evidence.")
    else:
        recommendations.append("Add tx_hash evidence to the demo actions.")

    if not _active_high_complaints(complaints):
        raw += 1.0
        evidence.append("No active confirmed high-severity complaint blocks technical confidence.")

    return _criterion(
        criterion="technical",
        label="Technical quality",
        weight_percent=30,
        raw_score=min(raw, 10),
        evidence=evidence,
        recommendations=recommendations,
    )


def _ecosystem_score(passport: dict[str, Any]) -> dict[str, Any]:
    agent = passport.get("agent", {})
    events = passport.get("actions_history", [])
    categories = _categories(events)
    chain_id = int(agent.get("chain_id") or 0)

    raw = 3.0
    evidence: list[str] = []
    recommendations: list[str] = []

    if chain_id in MANTLE_CHAIN_IDS:
        raw += 2.0
        evidence.append(f"Agent is configured for Mantle chain id {chain_id}.")
    else:
        recommendations.append("Use Mantle chain id 5000 or 5001 in the primary demo.")

    defi_categories = categories & {"defi", "swap", "rewards", "risk-check", "leverage", "marketplace-rental"}
    if defi_categories:
        raw += 2.0
        evidence.append(f"Agent activity maps to Mantle-relevant DeFi/CeFi categories: {', '.join(sorted(defi_categories))}.")
    else:
        recommendations.append("Add Mantle DeFi or wallet-permission activity examples.")

    if _tx_hash_count(events) > 0:
        raw += 1.5
        evidence.append("Passport can display transaction hash evidence for Mantle explorer links.")

    if passport.get("analysis", {}).get("recommendation"):
        raw += 1.0
        evidence.append("Passport translates reputation into wallet-access guidance.")

    return _criterion(
        criterion="ecosystem_fit",
        label="Mantle ecosystem fit",
        weight_percent=20,
        raw_score=min(raw, 10),
        evidence=evidence or ["Backend has Mantle-ready fields even when demo data is sparse."],
        recommendations=recommendations,
    )


def _business_score(passport: dict[str, Any]) -> dict[str, Any]:
    reputation = passport.get("reputation", {})
    marketplace = passport.get("marketplace", {})
    listing = marketplace.get("listing")
    stats = marketplace.get("stats", {})

    raw = 4.0
    evidence = ["Passport supports a clear trust decision before giving an agent wallet permissions."]
    recommendations: list[str] = []

    if int(reputation.get("recommended_wallet_limit_usd", 0)) > 0:
        raw += 1.5
        evidence.append("Backend calculates a recommended wallet limit, which maps reputation to economic risk.")

    if listing:
        raw += 1.5
        evidence.append("Marketplace listing data exists for phase 2 monetization.")
    else:
        recommendations.append("Create a listing for the agent when demonstrating marketplace potential.")

    if int(stats.get("completed_rentals") or 0) > 0:
        raw += 1.0
        evidence.append("Completed rentals can become proof of real demand.")

    if reputation.get("successful_volume_usd", 0) > 0:
        raw += 1.0
        evidence.append(f"${reputation['successful_volume_usd']} successful handled value is tracked.")

    return _criterion(
        criterion="business_potential",
        label="Business potential",
        weight_percent=20,
        raw_score=min(raw, 10),
        evidence=evidence,
        recommendations=recommendations,
    )


def _innovation_score(passport: dict[str, Any]) -> dict[str, Any]:
    reputation = passport.get("reputation", {})
    breakdown = reputation.get("score_breakdown", {})
    analysis = passport.get("analysis", {})

    raw = 4.0
    evidence = ["Agent Reputation Passport turns agent behavior into a reusable trust primitive."]
    recommendations: list[str] = []

    if breakdown:
        raw += 2.0
        evidence.append("Reputation is explainable instead of a black-box rating.")

    if {"wallet_verification", "onchain_evidence", "task_diversity"}.issubset(set(breakdown.keys())):
        raw += 1.5
        evidence.append("Scoring combines wallet verification, on-chain evidence, task diversity, and risk signals.")

    if analysis.get("risk_flags") and analysis.get("recommendation"):
        raw += 1.0
        evidence.append("Passport produces actionable risk flags and recommendations.")

    if int(reputation.get("complaint_count", 0)) >= 0:
        raw += 0.5
        evidence.append("Complaints are first-class reputation inputs.")

    if raw < 8:
        recommendations.append("Show before/after score changes when adding actions or complaints.")

    return _criterion(
        criterion="innovation",
        label="Innovation",
        weight_percent=20,
        raw_score=min(raw, 10),
        evidence=evidence,
        recommendations=recommendations,
    )


def _ux_score(passport: dict[str, Any]) -> dict[str, Any]:
    agent = passport.get("agent", {})
    reputation = passport.get("reputation", {})
    analysis = passport.get("analysis", {})

    raw = 3.5
    evidence: list[str] = []
    recommendations: list[str] = []

    if agent.get("owner_wallet"):
        raw += 1.0
        evidence.append("Primary onboarding starts from a wallet-linked passport.")

    if analysis.get("summary") and analysis.get("recommendation"):
        raw += 2.0
        evidence.append("Backend returns human-readable summary and recommendation for frontend display.")

    if reputation.get("risk_level") and reputation.get("recommended_wallet_limit_usd") is not None:
        raw += 1.5
        evidence.append("Frontend can show risk level and wallet limit without recalculating anything.")

    if reputation.get("score_breakdown"):
        raw += 1.0
        evidence.append("Frontend can render why the score changed.")

    if raw < 8:
        recommendations.append("Keep the frontend flow to connect wallet -> passport -> intelligence.")

    return _criterion(
        criterion="user_experience",
        label="User experience",
        weight_percent=10,
        raw_score=min(raw, 10),
        evidence=evidence,
        recommendations=recommendations,
    )


def _criterion(
    criterion: str,
    label: str,
    weight_percent: int,
    raw_score: float,
    evidence: list[str],
    recommendations: list[str],
) -> dict[str, Any]:
    weighted_score = round(raw_score * weight_percent / 10, 2)
    return {
        "criterion": criterion,
        "label": label,
        "weight_percent": weight_percent,
        "raw_score": round(raw_score, 2),
        "weighted_score": weighted_score,
        "max_weighted_score": float(weight_percent),
        "evidence": evidence,
        "recommendations": recommendations,
    }


def _aggregate_criteria(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for report in reports:
        for criterion in report["criteria"]:
            grouped.setdefault(criterion["criterion"], []).append(criterion)

    result: list[dict[str, Any]] = []
    for criterion_id, weight in CRITERION_WEIGHTS.items():
        items = grouped.get(criterion_id, [])
        if not items:
            result.append(
                _criterion(
                    criterion=criterion_id,
                    label=_criterion_label(criterion_id),
                    weight_percent=weight,
                    raw_score=0,
                    evidence=[],
                    recommendations=["No evidence for this judging criterion yet."],
                )
            )
            continue

        raw_score = sum(float(item["raw_score"]) for item in items) / len(items)
        evidence = _dedupe([entry for item in items for entry in item["evidence"]])[:5]
        recommendations = _dedupe([entry for item in items for entry in item["recommendations"]])[:5]
        result.append(
            _criterion(
                criterion=criterion_id,
                label=_criterion_label(criterion_id),
                weight_percent=weight,
                raw_score=raw_score,
                evidence=evidence,
                recommendations=recommendations,
            )
        )
    return result


def _empty_project_criteria() -> list[dict[str, Any]]:
    return [
        _criterion(
            criterion=criterion_id,
            label=_criterion_label(criterion_id),
            weight_percent=weight,
            raw_score=0,
            evidence=[],
            recommendations=["Create demo passports to generate judging evidence."],
        )
        for criterion_id, weight in CRITERION_WEIGHTS.items()
    ]


def _grade(score: float) -> str:
    if score >= 90:
        return "excellent"
    if score >= 70:
        return "good"
    if score >= 50:
        return "average"
    if score >= 30:
        return "below_average"
    return "weak"


def _summary(score: float, grade: str) -> str:
    return f"Mantle readiness score {score}/100 ({grade})."


def _risk_adjusted_score(score: float, passport: dict[str, Any]) -> float:
    reputation = passport.get("reputation", {})
    risk_level = reputation.get("risk_level")
    complaint_count = int(reputation.get("complaint_count", 0))
    if risk_level == "High":
        score = min(score, 64)
    elif risk_level == "Medium":
        score = min(score, 84)
    if complaint_count >= 2:
        score -= min(complaint_count * 2, 8)
    return round(max(score, 0), 2)


def _next_steps(criteria: list[dict[str, Any]]) -> list[str]:
    steps: list[str] = []
    for item in criteria:
        steps.extend(item["recommendations"])
    if not steps:
        steps.append("Use the wallet -> passport -> intelligence flow as the primary judging demo.")
    return _dedupe(steps)


def _project_next_steps(
    passports: list[dict[str, Any]],
    reports: list[dict[str, Any]],
    criteria: list[dict[str, Any]],
) -> list[str]:
    steps = _dedupe([entry for criterion in criteria for entry in criterion["recommendations"]])
    risk_distribution = _risk_distribution(passports)
    if risk_distribution.get("High", 0):
        steps.append("Use the Low-risk passport as the main demo and keep High-risk agents as contrast cases.")
    if not any(report["grade"] == "excellent" for report in reports):
        steps.append("Improve one flagship agent until it reaches an excellent Mantle readiness grade.")
    if not steps:
        steps.append("Lead the demo with wallet verification, passport scoring, intelligence, and Mantle readiness.")
    return _dedupe(steps)


def _recommended_demo_flow() -> list[str]:
    return [
        "POST /auth/nonce",
        "POST /auth/verify",
        "GET /agents/{agent_id}/passport",
        "GET /agents/{agent_id}/intelligence",
        "GET /mantle/agents/{agent_id}/readiness",
        "GET /mantle/readiness",
    ]


def _criteria_average(criteria: list[dict[str, Any]]) -> float:
    return round(sum(float(item["weighted_score"]) for item in criteria), 2)


def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _risk_distribution(passports: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for passport in passports:
        risk = str(passport.get("reputation", {}).get("risk_level", "unknown"))
        counts[risk] = counts.get(risk, 0) + 1
    return counts


def _criterion_label(criterion_id: str) -> str:
    return {
        "technical": "Technical quality",
        "ecosystem_fit": "Mantle ecosystem fit",
        "business_potential": "Business potential",
        "innovation": "Innovation",
        "user_experience": "User experience",
    }.get(criterion_id, criterion_id)


def _categories(events: list[dict[str, Any]]) -> set[str]:
    return {str(event.get("category")) for event in events if event.get("category")}


def _tx_hash_count(events: list[dict[str, Any]]) -> int:
    return len([event for event in events if event.get("tx_hash")])


def _active_high_complaints(complaints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        complaint
        for complaint in complaints
        if complaint.get("severity") == "high" and complaint.get("status") in {"open", "confirmed"}
    ]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
