from __future__ import annotations

import sqlite3
from typing import Any

from app import repositories
from app.schemas import AgentEventCreate, TransactionPrepareRequest, TransactionRecordRequest
from app.services.agent_intelligence import analyze_agent_passport
from app.services.policy_engine import evaluate_transaction_policy
from app.services.wallet_utils import int_to_hex_quantity, normalize_wallet_address


class TransactionSafetyError(Exception):
    def __init__(self, detail: str, status_code: int = 403) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def prepare_transaction(
    db: sqlite3.Connection,
    agent_id: int,
    payload: TransactionPrepareRequest,
    mode: str = "metamask",
) -> dict[str, Any]:
    passport = repositories.build_passport(db, agent_id)
    if not passport:
        raise TransactionSafetyError("Agent not found", 404)

    agent = passport["agent"]
    from_address = normalize_wallet_address(agent["owner_wallet"])
    to_address = normalize_wallet_address(payload.to_address)
    value_wei_int = int(payload.value_wei)

    if payload.chain_id != int(agent["chain_id"]):
        raise TransactionSafetyError("Transaction chain_id must match the agent wallet chain_id", 400)

    intelligence = analyze_agent_passport(passport)
    wallet_permission = intelligence["wallet_permission"]
    transaction_request = {
        "from": from_address,
        "to": to_address,
        "value": int_to_hex_quantity(value_wei_int),
        "chainId": int_to_hex_quantity(payload.chain_id),
    }
    policy_input = {
        "from_address": from_address,
        "to_address": to_address,
        "chain_id": payload.chain_id,
        "value_wei": payload.value_wei,
        "value_usd": payload.value_usd,
        "transaction_request": transaction_request,
    }
    policy = evaluate_transaction_policy(agent_id, passport, intelligence, policy_input, mode)
    if not policy["allowed"]:
        raise TransactionSafetyError(policy["reason"], 403)

    return {
        "agent_id": agent_id,
        "from_address": from_address,
        "to_address": to_address,
        "from": from_address,
        "to": to_address,
        "chain_id": payload.chain_id,
        "value_wei": payload.value_wei,
        "value": payload.value_wei,
        "value_usd": payload.value_usd,
        "requires_user_signature": True,
        "wallet_decision": wallet_permission["decision"],
        "recommended_limit_usd": wallet_permission["recommended_limit_usd"],
        "transaction_request": transaction_request,
        "reason": payload.reason,
        "policy_reason": policy["reason"],
        "passport": passport,
        "intelligence": intelligence,
        "policy": policy,
    }


def record_transaction(
    db: sqlite3.Connection,
    agent_id: int,
    payload: TransactionRecordRequest,
    recorded_by: str = "wallet_ui_or_agent",
) -> dict[str, Any]:
    agent = repositories.get_agent_or_none(db, agent_id)
    if not agent:
        raise TransactionSafetyError("Agent not found", 404)

    metadata = {
        **payload.metadata,
        "source": "transaction_record",
        "recorded_by": recorded_by,
    }
    event = repositories.create_event(
        db,
        agent_id,
        AgentEventCreate(
            title=payload.title,
            category=payload.category,
            outcome=payload.outcome,
            value_usd=payload.value_usd,
            tx_hash=payload.tx_hash,
            metadata=metadata,
        ),
    )
    passport = repositories.build_passport(db, agent_id)
    intelligence = analyze_agent_passport(passport)
    return {"event": event, "passport": passport, "intelligence": intelligence}
