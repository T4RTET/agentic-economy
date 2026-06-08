import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app import repositories
from app.database import get_db
from app.schemas import (
    AutomatedTransactionRequest,
    AutomatedTransactionResponse,
    AutomationActionRequest,
    AutomationEvaluationResponse,
    AutomationPolicy,
    AutomationPolicyUpdate,
    DelegationConfirmRequest,
    DelegationRequestResponse,
)
from app.services.agent_intelligence import analyze_agent_passport
from app.services.automation_policy import evaluate_automation_action
from app.services.wallet_utils import int_to_hex_quantity


router = APIRouter(tags=["automation"])


@router.get("/agents/{agent_id}/automation-policy", response_model=AutomationPolicy)
def get_agent_automation_policy(
    agent_id: int,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    policy = repositories.get_or_create_automation_policy(db, agent_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return policy


@router.put("/agents/{agent_id}/automation-policy", response_model=AutomationPolicy)
def put_agent_automation_policy(
    agent_id: int,
    payload: AutomationPolicyUpdate,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    policy = repositories.update_automation_policy(db, agent_id, payload)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return policy


@router.post("/agents/{agent_id}/automation-policy/evaluate", response_model=AutomationEvaluationResponse)
def evaluate_agent_automation_action(
    agent_id: int,
    payload: AutomationActionRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    passport, intelligence, policy = _load_context(db, agent_id)
    return _evaluate(db, agent_id, passport, intelligence, policy, payload)


@router.post("/agents/{agent_id}/automation/delegation/request", response_model=DelegationRequestResponse)
def request_agent_delegation(
    agent_id: int,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    policy = repositories.get_or_create_automation_policy(db, agent_id)
    agent = repositories.get_agent_or_none(db, agent_id)
    if not policy or not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    scope = _policy_scope(policy)
    updated = repositories.request_automation_delegation(db, agent_id, scope)
    return {
        "agent_id": agent_id,
        "delegation_status": updated["delegation_status"],
        "message": "Grant limited MetaMask Smart Account delegation for this agent policy.",
        "policy_scope": scope,
        "request": {
            "type": "metamask_smart_account_delegation",
            "agent_id": agent_id,
            "owner_wallet": agent["owner_wallet"],
            "scope": scope,
            "note": "Backend does not sign this request. User approval must happen in MetaMask Smart Accounts / Delegation.",
        },
    }


@router.post("/agents/{agent_id}/automation/delegation/confirm", response_model=AutomationPolicy)
def confirm_agent_delegation(
    agent_id: int,
    payload: DelegationConfirmRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    policy = repositories.confirm_automation_delegation(
        db,
        agent_id,
        payload.smart_account_address,
        payload.delegation_id,
        payload.delegation_scope,
    )
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return policy


@router.post("/agents/{agent_id}/transactions/execute-automated", response_model=AutomatedTransactionResponse)
def execute_agent_transaction_with_automation(
    agent_id: int,
    payload: AutomatedTransactionRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    passport, intelligence, policy = _load_context(db, agent_id)
    evaluation = _evaluate(db, agent_id, passport, intelligence, policy, payload)
    transaction_request = _metamask_transaction_request(passport, payload)
    smart_account_payload = _smart_account_execution_payload(policy, payload, evaluation)

    if not evaluation["allowed"]:
        attempt = repositories.create_automation_attempt(
            db,
            agent_id,
            payload,
            status="rejected",
            reason=evaluation["reason"],
            rejection_reason=evaluation["reason"],
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=evaluation["reason"])

    if evaluation["delegation_required"]:
        attempt = repositories.create_automation_attempt(
            db,
            agent_id,
            payload,
            status="delegation_required",
            reason=evaluation["reason"],
        )
        return _execution_response(False, False, True, "delegation_required", attempt, evaluation, transaction_request, None)

    if evaluation["requires_user_confirmation"]:
        attempt = repositories.create_automation_attempt(
            db,
            agent_id,
            payload,
            status="requires_confirmation",
            reason=evaluation["reason"],
        )
        return _execution_response(False, True, False, "requires_confirmation", attempt, evaluation, transaction_request, None)

    attempt = repositories.create_automation_attempt(
        db,
        agent_id,
        payload,
        status="prepared",
        reason=evaluation["reason"],
    )
    return _execution_response(False, False, False, "prepared", attempt, evaluation, None, smart_account_payload)


def _load_context(db: sqlite3.Connection, agent_id: int) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    passport = repositories.build_passport(db, agent_id)
    if not passport:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    policy = repositories.get_or_create_automation_policy(db, agent_id)
    return passport, analyze_agent_passport(passport), policy


def _evaluate(
    db: sqlite3.Connection,
    agent_id: int,
    passport: dict[str, Any],
    intelligence: dict[str, Any],
    policy: dict[str, Any],
    payload: AutomationActionRequest,
) -> dict:
    current_balance = int(payload.current_native_balance_wei) if payload.current_native_balance_wei is not None else None
    return evaluate_automation_action(
        db,
        agent_id,
        passport,
        intelligence,
        policy,
        payload.model_dump(),
        current_native_balance_wei=current_balance,
    )


def _policy_scope(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "max_tx_value_usd": policy["max_tx_value_usd"],
        "daily_limit_usd": policy["daily_limit_usd"],
        "max_transactions_per_hour": policy["max_transactions_per_hour"],
        "min_native_balance_wei": policy["min_native_balance_wei"],
        "require_confirmation_above_usd": policy["require_confirmation_above_usd"],
        "allowed_chain_ids": policy["allowed_chain_ids"],
        "allowed_tokens": policy["allowed_tokens"],
        "allowed_recipients": policy["allowed_recipients"],
        "allowed_actions": policy["allowed_actions"],
        "expiry": "24h",
    }


def _metamask_transaction_request(passport: dict[str, Any], payload: AutomatedTransactionRequest) -> dict[str, Any]:
    return {
        "from": passport["agent"]["owner_wallet"],
        "to": payload.to_address,
        "value": int_to_hex_quantity(int(payload.value_wei)),
        "chainId": int_to_hex_quantity(payload.chain_id),
    }


def _smart_account_execution_payload(
    policy: dict[str, Any],
    payload: AutomatedTransactionRequest,
    evaluation: dict[str, Any],
) -> dict[str, Any] | None:
    if not evaluation["can_auto_execute"]:
        return None
    return {
        "type": "metamask_smart_account_execution",
        "smart_account_address": policy["smart_account_address"],
        "delegation_id": policy["delegation_id"],
        "call": {
            "action_type": payload.action_type,
            "to": payload.to_address,
            "token": payload.token_address or "NATIVE",
            "value": int_to_hex_quantity(int(payload.value_wei)),
            "chainId": int_to_hex_quantity(payload.chain_id),
            "reason": payload.reason,
        },
        "policy_scope": policy.get("delegation_scope") or _policy_scope(policy),
        "note": "Submit this payload with MetaMask Smart Accounts Kit. The backend has not signed anything.",
    }


def _execution_response(
    executed: bool,
    requires_user_confirmation: bool,
    delegation_required: bool,
    status_value: str,
    attempt: dict[str, Any],
    evaluation: dict[str, Any],
    transaction_request: dict[str, Any] | None,
    smart_account_execution_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "executed": executed,
        "requires_user_confirmation": requires_user_confirmation,
        "delegation_required": delegation_required,
        "status": status_value,
        "reason": evaluation["reason"],
        "attempt_id": attempt["id"],
        "transaction_request": transaction_request,
        "smart_account_execution_payload": smart_account_execution_payload,
        "tx_hash": attempt.get("tx_hash"),
        "evaluation": evaluation,
    }
