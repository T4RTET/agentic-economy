import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app import repositories
from app.database import get_db
from app.schemas import AgentPassport, WalletConnect


router = APIRouter(prefix="/wallet", tags=["wallet passport"])


@router.post("/connect", response_model=AgentPassport)
def connect_wallet(payload: WalletConnect, db: sqlite3.Connection = Depends(get_db)) -> AgentPassport:
    agent = repositories.connect_wallet(db, payload)
    passport = repositories.build_passport(db, agent["id"])
    if not passport:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found")
    return passport


@router.get("/{wallet_address}/passport", response_model=AgentPassport)
def get_wallet_passport(
    wallet_address: str,
    chain_id: int = 5000,
    db: sqlite3.Connection = Depends(get_db),
) -> AgentPassport:
    agent = repositories.get_agent_by_wallet(db, wallet_address, chain_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet-linked agent not found")
    return repositories.build_passport(db, agent["id"])
