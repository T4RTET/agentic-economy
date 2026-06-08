from __future__ import annotations

from datetime import UTC, datetime
import os
from typing import Any

from app.services.wallet_utils import is_valid_evm_address, normalize_wallet_address


MAINNET_CHAIN_IDS = {1}


def evaluate_transaction_policy(
    agent_id: int,
    passport: dict[str, Any],
    intelligence: dict[str, Any],
    transaction_request: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    violations: list[str] = []
    agent = passport.get("agent", {})
    wallet_permission = intelligence.get("wallet_permission", {})
    risk_assessment = intelligence.get("risk_assessment", {})

    owner_wallet = agent.get("owner_wallet", "")
    if not is_valid_evm_address(owner_wallet):
        violations.append("Agent wallet address is invalid.")

    chain_id = _transaction_chain_id(transaction_request)
    if chain_id != int(agent.get("chain_id", 0)):
        violations.append("Transaction chain_id must match the agent wallet chain_id.")

    to_address = _transaction_to_address(transaction_request)
    if not to_address or not is_valid_evm_address(to_address):
        violations.append("Recipient address is invalid.")

    value_usd = float(transaction_request.get("value_usd", 0) or 0)
    value_wei = _transaction_value_wei(transaction_request)
    if value_wei < 0:
        violations.append("Transaction value must be non-negative.")

    decision = wallet_permission.get("decision")
    recommended_limit = int(wallet_permission.get("recommended_limit_usd", 0) or 0)
    if decision == "deny":
        violations.append("Wallet permission decision is deny.")
    if value_usd > recommended_limit:
        violations.append(f"Transaction value exceeds the recommended wallet limit of ${recommended_limit}.")

    if _has_confirmed_high_complaint(passport):
        violations.append("Agent has a confirmed high-severity complaint.")
    if risk_assessment.get("risk_level") == "High":
        violations.append("High-risk agents cannot prepare or execute transactions.")

    allowed_recipients = _allowed_recipients()
    if allowed_recipients and to_address:
        normalized_to = normalize_wallet_address(to_address)
        if normalized_to.lower() not in allowed_recipients:
            violations.append("Recipient is not in the configured allowlist.")

    if mode == "autonomous":
        if not _env_bool("AGENT_EXECUTOR_ENABLED", False):
            violations.append("Autonomous executor is disabled.")
        if not os.getenv("AGENT_EXECUTOR_PRIVATE_KEY"):
            violations.append("AGENT_EXECUTOR_PRIVATE_KEY is not configured.")
        if chain_id in MAINNET_CHAIN_IDS and not _env_bool("AGENT_EXECUTOR_ALLOW_MAINNET", False):
            violations.append("Autonomous mainnet execution is disabled by default.")
        allowed_chain_ids = _allowed_chain_ids()
        if chain_id not in allowed_chain_ids:
            violations.append("Chain ID is not allowed for autonomous execution.")

        max_value_wei = _env_int("AGENT_MAX_TX_VALUE_WEI", 0)
        if max_value_wei > 0 and value_wei > max_value_wei:
            violations.append("Transaction value exceeds AGENT_MAX_TX_VALUE_WEI.")

        daily_limit_usd = _env_float("AGENT_DAILY_LIMIT_USD", 10)
        if daily_limit_usd >= 0 and _todays_transaction_volume(passport) + value_usd > daily_limit_usd:
            violations.append("Transaction would exceed AGENT_DAILY_LIMIT_USD.")

    allowed = not violations
    return {
        "allowed": allowed,
        "reason": "Policy checks passed." if allowed else " ".join(violations),
        "violations": violations,
        "mode": mode,
        "agent_id": agent_id,
    }


def _transaction_to_address(transaction_request: dict[str, Any]) -> str:
    nested = transaction_request.get("transaction_request", {})
    return str(transaction_request.get("to_address") or nested.get("to") or "")


def _transaction_chain_id(transaction_request: dict[str, Any]) -> int:
    nested = transaction_request.get("transaction_request", {})
    raw = transaction_request.get("chain_id", nested.get("chainId", 0))
    if isinstance(raw, str) and raw.startswith("0x"):
        return int(raw, 16)
    return int(raw or 0)


def _transaction_value_wei(transaction_request: dict[str, Any]) -> int:
    nested = transaction_request.get("transaction_request", {})
    raw = transaction_request.get("value_wei", nested.get("value", "0"))
    if isinstance(raw, str) and raw.startswith("0x"):
        return int(raw, 16)
    return int(raw or 0)


def _has_confirmed_high_complaint(passport: dict[str, Any]) -> bool:
    return any(
        complaint.get("status") == "confirmed" and complaint.get("severity") == "high"
        for complaint in passport.get("complaints", [])
    )


def _todays_transaction_volume(passport: dict[str, Any]) -> float:
    today = datetime.now(UTC).date()
    total = 0.0
    for event in passport.get("actions_history", []):
        if event.get("category") not in {"wallet-transaction", "blockchain-transaction"}:
            continue
        created_at = str(event.get("created_at", ""))
        if not created_at:
            continue
        try:
            event_date = datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()
        except ValueError:
            event_date = datetime.strptime(created_at.split(" ")[0], "%Y-%m-%d").date()
        if event_date == today:
            total += float(event.get("value_usd") or 0)
    return total


def _allowed_recipients() -> set[str]:
    raw = os.getenv("AGENT_ALLOWED_RECIPIENTS", "")
    recipients: set[str] = set()
    for item in raw.split(","):
        value = item.strip()
        if value and is_valid_evm_address(value):
            recipients.add(normalize_wallet_address(value).lower())
    return recipients


def _allowed_chain_ids() -> set[int]:
    raw = os.getenv("AGENT_ALLOWED_CHAIN_IDS", "5000")
    return {int(item.strip()) for item in raw.split(",") if item.strip()}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default
