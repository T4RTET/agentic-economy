import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import repositories
from app.database import get_db
from app.schemas import MantleSyncResponse, MantleTransactionVerification, MantleVerifyRequest
from app.services.mantle import MantleService, MantleServiceError, indexed_transaction_to_event


router = APIRouter(prefix="/mantle", tags=["mantle"])


@router.get("/status")
def get_mantle_status() -> dict:
    try:
        return MantleService().network_status()
    except MantleServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/transactions/verify", response_model=MantleTransactionVerification)
def verify_mantle_transaction(payload: MantleVerifyRequest) -> dict:
    try:
        return MantleService().verify_transaction(payload.tx_hash, payload.wallet_address)
    except MantleServiceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/agents/{agent_id}/sync", response_model=MantleSyncResponse)
def sync_agent_mantle_history(
    agent_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    agent = repositories.get_agent_or_none(db, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not repositories.wallet_is_verified(db, agent["owner_wallet"], agent["chain_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verify wallet ownership before syncing history.")
    try:
        indexed = MantleService().wallet_transactions(agent["owner_wallet"], limit)
    except MantleServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    imported = 0
    skipped = 0
    for transaction in indexed:
        event = indexed_transaction_to_event(transaction, agent["owner_wallet"])
        if repositories.event_exists_by_tx_hash(db, event["tx_hash"]):
            skipped += 1
            continue
        repositories.create_synced_event(db, agent_id, event)
        imported += 1
    repositories.record_wallet_sync(db, agent_id, imported, skipped)
    return {
        "agent_id": agent_id,
        "wallet_address": agent["owner_wallet"],
        "imported_events": imported,
        "skipped_duplicates": skipped,
        "passport": repositories.build_passport(db, agent_id),
    }
