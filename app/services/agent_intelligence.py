from __future__ import annotations

from typing import Any, Literal


RiskLevel = Literal["Low", "Medium", "High"]
WalletDecision = Literal["allow", "limit", "deny"]


def analyze_agent_passport(passport: dict[str, Any]) -> dict[str, Any]:
    reputation = passport.get("reputation", {})
    agent = passport.get("agent", {})
    marketplace = passport.get("marketplace", {})
    events = passport.get("actions_history", [])
    complaints = passport.get("complaints", [])

    trust_score = int(reputation.get("trust_score", 0))
    risk_level = _risk_level(reputation.get("risk_level"))
    open_complaints = _complaints_with_status(complaints, "open")
    confirmed_high_complaints = _confirmed_high_complaints(complaints)
    failed_events = _failed_events(events)

    wallet_decision = _wallet_decision(
        risk_level=risk_level,
        trust_score=trust_score,
        has_confirmed_high_complaint=bool(confirmed_high_complaints),
    )
    wallet_limit = _wallet_limit(reputation, risk_level)
    marketplace_verdict = _marketplace_verdict(
        risk_level=risk_level,
        marketplace=marketplace,
        has_confirmed_high_complaint=bool(confirmed_high_complaints),
    )

    return {
        "summary": _summary(agent, trust_score, risk_level, wallet_decision),
        "wallet_permission": {
            "decision": wallet_decision,
            "recommended_limit_usd": wallet_limit,
            "reason": _wallet_reason(wallet_decision, risk_level, trust_score, open_complaints, confirmed_high_complaints),
        },
        "risk_assessment": {
            "risk_level": risk_level,
            "main_risks": _main_risks(reputation, failed_events, open_complaints, confirmed_high_complaints),
            "confidence": _confidence(reputation),
        },
        "marketplace_verdict": marketplace_verdict,
        "suggested_next_actions": _suggested_next_actions(
            reputation=reputation,
            risk_level=risk_level,
            marketplace=marketplace,
            open_complaints=open_complaints,
        ),
    }


def _risk_level(value: Any) -> RiskLevel:
    if value in {"Low", "Medium", "High"}:
        return value
    return "High"


def _wallet_decision(
    risk_level: RiskLevel,
    trust_score: int,
    has_confirmed_high_complaint: bool,
) -> WalletDecision:
    if has_confirmed_high_complaint or risk_level == "High" or trust_score < 50:
        return "deny"
    if risk_level == "Medium" or 50 <= trust_score <= 74:
        return "limit"
    if risk_level == "Low" and trust_score >= 75:
        return "allow"
    return "limit"


def _wallet_limit(reputation: dict[str, Any], risk_level: RiskLevel) -> int:
    raw_limit = int(reputation.get("recommended_wallet_limit_usd", 0))
    if risk_level == "Medium":
        return min(raw_limit, 1000)
    if risk_level == "High":
        return min(raw_limit, 100)
    return raw_limit


def _marketplace_verdict(
    risk_level: RiskLevel,
    marketplace: dict[str, Any],
    has_confirmed_high_complaint: bool,
) -> dict[str, Any]:
    listing = marketplace.get("listing")
    if has_confirmed_high_complaint:
        return {
            "can_be_listed": False,
            "can_be_rented": False,
            "reason": "Agent has a confirmed high-severity complaint and should not be rented.",
        }
    if risk_level == "High":
        return {
            "can_be_listed": False,
            "can_be_rented": False,
            "reason": "High-risk agents are not marketplace-ready until risk issues are resolved.",
        }
    if not listing:
        return {
            "can_be_listed": True,
            "can_be_rented": False,
            "reason": "Agent can be listed, but it cannot be rented until a marketplace listing exists.",
        }
    if listing.get("availability") == "paused":
        return {
            "can_be_listed": True,
            "can_be_rented": False,
            "reason": "Marketplace listing is paused and should stay unavailable until risk issues are resolved.",
        }
    if risk_level == "Medium":
        return {
            "can_be_listed": True,
            "can_be_rented": True,
            "reason": "Medium-risk agents can be rented only with capped wallet permissions.",
        }
    return {
        "can_be_listed": True,
        "can_be_rented": True,
        "reason": "Low-risk agent is marketplace-ready within the recommended wallet limit.",
    }


def _summary(agent: dict[str, Any], trust_score: int, risk_level: RiskLevel, decision: WalletDecision) -> str:
    agent_name = agent.get("name") or "This agent"
    return f"{agent_name} has Trust Score {trust_score}/100 with {risk_level} risk. Wallet access decision: {decision}."


def _wallet_reason(
    decision: WalletDecision,
    risk_level: RiskLevel,
    trust_score: int,
    open_complaints: list[dict[str, Any]],
    confirmed_high_complaints: list[dict[str, Any]],
) -> str:
    reasons = [f"Trust Score {trust_score}/100 and Risk Level {risk_level} produce a {decision} decision."]
    if confirmed_high_complaints:
        reasons.append("Confirmed high-severity complaints force wallet permission denial.")
    if open_complaints:
        reasons.append(f"{len(open_complaints)} open complaint(s) require review before expanding permissions.")
    return " ".join(reasons)


def _main_risks(
    reputation: dict[str, Any],
    failed_events: list[dict[str, Any]],
    open_complaints: list[dict[str, Any]],
    confirmed_high_complaints: list[dict[str, Any]],
) -> list[str]:
    risks: list[str] = []
    total_events = int(reputation.get("total_events", 0))

    if failed_events:
        risks.append(f"{len(failed_events)} failed/error action(s) recorded.")
    if open_complaints:
        risks.append(f"{len(open_complaints)} open complaint(s) need review.")
    if confirmed_high_complaints:
        risks.append(f"{len(confirmed_high_complaints)} confirmed high-severity complaint(s).")
    if total_events == 0:
        risks.append("No successful actions yet.")
    if not risks:
        risks.append("No active risk flags.")
    return risks


def _confidence(reputation: dict[str, Any]) -> Literal["low", "medium", "high"]:
    total_events = int(reputation.get("total_events", 0))
    if total_events >= 3:
        return "high"
    if total_events >= 1:
        return "medium"
    return "low"


def _suggested_next_actions(
    reputation: dict[str, Any],
    risk_level: RiskLevel,
    marketplace: dict[str, Any],
    open_complaints: list[dict[str, Any]],
) -> list[str]:
    actions: list[str] = []
    listing = marketplace.get("listing")

    if int(reputation.get("total_events", 0)) == 0:
        actions.append("Record successful actions to build confidence.")
    if open_complaints:
        actions.append("Review open complaints before expanding wallet permissions.")
    if risk_level == "High":
        actions.append("Limit wallet access and resolve complaints before marketplace use.")
    if not listing and risk_level != "High":
        actions.append("Create a marketplace listing after confirming task terms.")
    if listing and listing.get("availability") == "paused":
        actions.append("Resolve risk issues before unpausing the marketplace listing.")
    if risk_level == "Low":
        actions.append("Allow broader permissions within the recommended wallet limit.")

    return _dedupe(actions)


def _complaints_with_status(complaints: list[dict[str, Any]], status: str) -> list[dict[str, Any]]:
    return [complaint for complaint in complaints if complaint.get("status") == status]


def _confirmed_high_complaints(complaints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        complaint
        for complaint in complaints
        if complaint.get("status") == "confirmed" and complaint.get("severity") == "high"
    ]


def _failed_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event.get("outcome") in {"failed", "error"}]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
