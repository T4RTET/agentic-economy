import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app import repositories
from app.database import get_db
from app.schemas import AgentPassport, WalletBalanceResponse, WalletConnect
from app.services.chain_client import ChainClientUnavailable, configured_chain_id, get_native_balance
from app.services.wallet_utils import normalize_wallet_address


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
    try:
        normalized_wallet = normalize_wallet_address(wallet_address)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    agent = repositories.get_agent_by_wallet(db, normalized_wallet, chain_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet-linked agent not found")
    return repositories.build_passport(db, agent["id"])


@router.get("/{wallet_address}/balance", response_model=WalletBalanceResponse)
def get_wallet_balance(wallet_address: str, chain_id: int = 5000) -> dict:
    try:
        normalized_wallet = normalize_wallet_address(wallet_address)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if chain_id != configured_chain_id():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requested chain_id is not configured")
    try:
        balance = get_native_balance(normalized_wallet)
    except ChainClientUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.args[0]) from exc
    return {"wallet_address": normalized_wallet, "chain_id": chain_id, "balance_wei": str(balance)}
