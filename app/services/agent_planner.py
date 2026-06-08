from __future__ import annotations

from typing import Any

from app.services.agent_executor import is_executor_enabled


SAFETY_STEPS = [
    "verify wallet binding",
    "check passport",
    "check intelligence",
    "evaluate policy",
    "prepare transaction",
    "require MetaMask signature OR execute with agent executor wallet",
    "record tx_hash",
    "update passport",
]


def plan_wallet_task(
    agent_id: int,
    goal: str,
    passport: dict[str, Any],
    intelligence: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    wallet_decision = intelligence.get("wallet_permission", {}).get("decision")
    goal_lower = goal.lower()
    wants_transaction = any(keyword in goal_lower for keyword in ("transfer", "send", "payment", "pay"))

    if wallet_decision == "deny":
        status = "rejected"
        reason = "Wallet permission decision is deny."
    elif not wants_transaction:
        status = "rejected"
        reason = "Only transfer/send/payment wallet tasks are supported by the deterministic planner."
    elif mode == "autonomous" and not is_executor_enabled():
        status = "rejected"
        reason = "Autonomous executor is disabled. Use MetaMask mode for user-approved transactions."
    elif mode == "autonomous":
        status = "planned"
        reason = "Autonomous task can proceed after policy checks."
    else:
        status = "requires_signature"
        reason = "MetaMask task requires user signature before sending."

    return {
        "agent_id": agent_id,
        "goal": goal,
        "status": status,
        "mode": mode,
        "reason": reason,
        "steps": SAFETY_STEPS,
        "wallet_decision": wallet_decision,
        "risk_level": intelligence.get("risk_assessment", {}).get("risk_level"),
        "agent_wallet": passport.get("agent", {}).get("owner_wallet"),
    }
