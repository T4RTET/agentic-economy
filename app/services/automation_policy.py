from __future__ import annotations

import sqlite3
from typing import Any

from app import repositories
from app.services.wallet_utils import is_valid_evm_address, normalize_wallet_address


def evaluate_automation_action(
    db: sqlite3.Connection,
    agent_id: int,
    passport: dict[str, Any],
    intelligence: dict[str, Any],
    policy: dict[str, Any],
    action: dict[str, Any],
    current_native_balance_wei: int | None = None,
) -> dict[str, Any]:
    violations: list[str] = []
    requires_user_confirmation = False
    can_auto_execute = False
    delegation_required = False

    to_address = str(action.get("to_address") or action.get("recipient") or action.get("recipient_address") or "")
    token_address = action.get("token_address")
    action_type = str(action.get("action_type") or "")
    value_usd = float(action.get("value_usd") or 0)
    value_wei = int(action.get("value_wei") or 0)
    chain_id = int(action.get("chain_id") or 0)

    if policy.get("emergency_stop"):
        violations.append("Emergency stop is enabled.")

    if not policy.get("automation_enabled"):
        violations.append("Automation is disabled.")

    if intelligence.get("wallet_permission", {}).get("decision") == "deny":
        violations.append("Wallet permission decision is deny.")

    if _has_confirmed_high_complaint(passport):
        violations.append("Agent has a confirmed high-severity complaint.")

    max_tx_value = float(policy.get("max_tx_value_usd") or 0)
    if value_usd > max_tx_value:
        violations.append(f"Action value exceeds max_tx_value_usd of ${max_tx_value}.")

    daily_limit = float(policy.get("daily_limit_usd") or 0)
    daily_used = repositories.automation_daily_value_usd(db, agent_id)
    if daily_used + value_usd > daily_limit:
        violations.append("Action would exceed daily_limit_usd.")

    max_per_hour = int(policy.get("max_transactions_per_hour") or 0)
    if repositories.automation_hourly_count(db, agent_id) >= max_per_hour:
        violations.append("Action would exceed max_transactions_per_hour.")

    allowed_chain_ids = set(policy.get("allowed_chain_ids") or [])
    if chain_id not in allowed_chain_ids:
        violations.append("Chain ID is not allowed.")

    if not is_valid_evm_address(to_address):
        violations.append("Recipient address is invalid.")
    else:
        allowed_recipients = {normalize_wallet_address(item).lower() for item in policy.get("allowed_recipients") or []}
        if normalize_wallet_address(to_address).lower() not in allowed_recipients:
            violations.append("Recipient is not allowlisted.")

    allowed_actions = set(policy.get("allowed_actions") or [])
    if action_type not in allowed_actions:
        violations.append("Action type is not allowlisted.")

    allowed_tokens = _normalized_allowed_tokens(policy.get("allowed_tokens") or [])
    if allowed_tokens:
        if token_address:
            token_key = normalize_wallet_address(str(token_address)).lower() if is_valid_evm_address(str(token_address)) else ""
            if token_key not in allowed_tokens:
                violations.append("Token address is not allowlisted.")
        elif "NATIVE" not in allowed_tokens:
            violations.append("Native transfer is not allowlisted.")

    if current_native_balance_wei is not None:
        min_balance = int(policy.get("min_native_balance_wei") or 0)
        if current_native_balance_wei - value_wei < min_balance:
            violations.append("Action would reduce native balance below min_native_balance_wei.")

    mode = str(policy.get("mode") or "manual")
    delegation_status = str(policy.get("delegation_status") or "none")

    if violations:
        return _result(False, False, False, False, " ".join(violations), violations)

    if mode == "manual":
        requires_user_confirmation = True
        reason = "Manual mode requires MetaMask user confirmation."
    elif mode == "semi_auto" and value_usd > float(policy.get("require_confirmation_above_usd") or 0):
        requires_user_confirmation = True
        reason = "Semi-auto mode requires confirmation above the configured threshold."
    else:
        if delegation_status != "active":
            delegation_required = True
            reason = "Active MetaMask Smart Account delegation is required for automatic execution."
        else:
            can_auto_execute = True
            reason = "Automation policy allows smart-account execution."

    return _result(True, requires_user_confirmation, can_auto_execute, delegation_required, reason, [])


def _result(
    allowed: bool,
    requires_user_confirmation: bool,
    can_auto_execute: bool,
    delegation_required: bool,
    reason: str,
    violations: list[str],
) -> dict[str, Any]:
    return {
        "allowed": allowed,
        "requires_user_confirmation": requires_user_confirmation,
        "can_auto_execute": can_auto_execute,
        "delegation_required": delegation_required,
        "reason": reason,
        "violations": violations,
    }


def _has_confirmed_high_complaint(passport: dict[str, Any]) -> bool:
    return any(
        complaint.get("status") == "confirmed" and complaint.get("severity") == "high"
        for complaint in passport.get("complaints", [])
    )


def _normalized_allowed_tokens(values: list[str]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        if value.upper() == "NATIVE":
            tokens.add("NATIVE")
        elif is_valid_evm_address(value):
            tokens.add(normalize_wallet_address(value).lower())
    return tokens
