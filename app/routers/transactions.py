import os
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app import repositories
from app.database import get_db
from app.schemas import (
    AutonomousTransactionRequest,
    AutonomousTransactionResponse,
    ExecutorStatusResponse,
    TransactionPrepareRequest,
    TransactionPrepareResponse,
    TransactionRecordRequest,
    TransactionRecordResponse,
    TransactionStatusResponse,
)
from app.services.agent_executor import (
    AgentExecutorError,
    execute_transaction_if_allowed,
    get_executor_address,
    is_executor_enabled,
)
from app.services.agent_intelligence import analyze_agent_passport
from app.services.chain_client import ChainClientUnavailable, configured_chain_id, get_transaction_status
from app.services.transaction_service import TransactionSafetyError, prepare_transaction, record_transaction


router = APIRouter(tags=["transactions"])


@router.post("/agents/{agent_id}/transactions/prepare", response_model=TransactionPrepareResponse)
def prepare_agent_transaction(
    agent_id: int,
    payload: TransactionPrepareRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        prepared = prepare_transaction(db, agent_id, payload, mode="metamask")
    except TransactionSafetyError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return prepared


@router.post(
    "/agents/{agent_id}/transactions/record",
    response_model=TransactionRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_agent_transaction(
    agent_id: int,
    payload: TransactionRecordRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        return record_transaction(db, agent_id, payload)
    except TransactionSafetyError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/agents/{agent_id}/transactions/execute-autonomous", response_model=AutonomousTransactionResponse)
def execute_agent_transaction_autonomously(
    agent_id: int,
    payload: AutonomousTransactionRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    if not payload.confirm_policy_ack:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="confirm_policy_ack must be true")

    passport = repositories.build_passport(db, agent_id)
    if not passport:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if payload.chain_id != passport["agent"]["chain_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction chain_id must match the agent wallet chain_id",
        )

    intelligence = analyze_agent_passport(passport)
    request = {
        "to_address": payload.to_address,
        "chain_id": payload.chain_id,
        "value_wei": payload.value_wei,
        "value_usd": payload.value_usd,
    }

    if not is_executor_enabled():
        repositories.add_audit_log(
            db,
            agent_id,
            "autonomous_transaction.rejected",
            {"reason": "executor_disabled", "to_address": payload.to_address, "value_usd": payload.value_usd},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Autonomous executor is disabled. Use /transactions/prepare and sign with MetaMask.",
        )

    try:
        result = execute_transaction_if_allowed(agent_id, request, passport, intelligence)
    except AgentExecutorError as exc:
        repositories.add_audit_log(db, agent_id, "autonomous_transaction.failed", {"error": exc.detail})
        db.commit()
        status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if "RPC" in exc.detail or "web3" in exc.detail
            else status.HTTP_403_FORBIDDEN
        )
        raise HTTPException(status_code=status_code, detail=exc.detail) from exc
    if not result.get("executed"):
        repositories.add_audit_log(
            db,
            agent_id,
            "autonomous_transaction.rejected",
            {"reason": result.get("reason"), "violations": result.get("violations", [])},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.get("reason", "Policy rejected transaction"))

    try:
        recorded = record_transaction(
            db,
            agent_id,
            TransactionRecordRequest(
                tx_hash=result["tx_hash"],
                outcome="success",
                value_usd=payload.value_usd,
                title=payload.title,
                category=payload.category,
                metadata={**payload.metadata, "executor_address": result["executor_address"]},
            ),
            recorded_by="autonomous_executor",
        )
    except (AgentExecutorError, TransactionSafetyError) as exc:
        repositories.add_audit_log(db, agent_id, "autonomous_transaction.record_failed", {"error": str(exc)})
        db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    repositories.add_audit_log(
        db,
        agent_id,
        "autonomous_transaction.submitted",
        {"tx_hash": result["tx_hash"], "executor_address": result["executor_address"]},
    )
    db.commit()
    return {
        "executed": True,
        "tx_hash": result["tx_hash"],
        "executor_address": result["executor_address"],
        "passport": recorded["passport"],
        "intelligence": recorded["intelligence"],
    }


@router.get("/transactions/{tx_hash}/status", response_model=TransactionStatusResponse)
def get_transaction_chain_status(tx_hash: str) -> dict:
    try:
        tx_status = get_transaction_status(tx_hash)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ChainClientUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.args[0]) from exc
    return {"tx_hash": tx_hash, "status": tx_status}


@router.get("/agent-executor/status", response_model=ExecutorStatusResponse)
def get_agent_executor_status() -> dict:
    return {
        "enabled": is_executor_enabled(),
        "executor_address": get_executor_address(),
        "chain_id": configured_chain_id(),
        "mainnet_allowed": os.getenv("AGENT_EXECUTOR_ALLOW_MAINNET", "false").lower() in {"1", "true", "yes", "on"},
    }
