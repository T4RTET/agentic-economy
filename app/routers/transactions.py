import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app import repositories
from app.database import get_db
from app.schemas import (
    AgentEventCreate,
    TransactionPrepareRequest,
    TransactionPrepareResponse,
    TransactionRecordRequest,
    TransactionRecordResponse,
)
from app.services.agent_intelligence import analyze_agent_passport


router = APIRouter(prefix="/agents", tags=["transactions"])


@router.post("/{agent_id}/transactions/prepare", response_model=TransactionPrepareResponse)
def prepare_agent_transaction(
    agent_id: int,
    payload: TransactionPrepareRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    passport = repositories.build_passport(db, agent_id)
    if not passport:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    agent = passport["agent"]
    if payload.chain_id != agent["chain_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction chain_id must match the agent wallet chain_id",
        )

    intelligence = analyze_agent_passport(passport)
    wallet_permission = intelligence["wallet_permission"]
    decision = wallet_permission["decision"]
    recommended_limit = int(wallet_permission["recommended_limit_usd"])

    if decision == "deny":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Wallet permission denied: {wallet_permission['reason']}",
        )
    if decision == "limit" and payload.value_usd > recommended_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction value exceeds the recommended wallet limit of ${recommended_limit}",
        )

    return {
        "from": agent["owner_wallet"],
        "to": payload.recipient_address,
        "value": payload.value_wei,
        "chain_id": payload.chain_id,
        "reason": payload.reason,
        "requires_user_signature": True,
    }


@router.post(
    "/{agent_id}/transactions/record",
    response_model=TransactionRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_agent_transaction(
    agent_id: int,
    payload: TransactionRecordRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    agent = repositories.get_agent_or_none(db, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    event = repositories.create_event(
        db,
        agent_id,
        AgentEventCreate(
            title=f"Recorded blockchain transaction {payload.tx_hash}",
            category="blockchain-transaction",
            outcome=payload.outcome,
            value_usd=payload.value_usd,
            tx_hash=payload.tx_hash,
            metadata=payload.metadata,
        ),
    )
    return {"event": event}
