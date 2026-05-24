import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app import repositories
from app.database import get_db
from app.schemas import WalletConnect, WalletNonceRequest, WalletNonceResponse, WalletVerifyRequest, WalletVerifyResponse
from app.services.wallet_auth import WalletAuthError, create_wallet_nonce, verify_wallet_signature


router = APIRouter(prefix="/auth", tags=["wallet auth"])


@router.post("/nonce", response_model=WalletNonceResponse)
def post_wallet_nonce(payload: WalletNonceRequest, db: sqlite3.Connection = Depends(get_db)) -> WalletNonceResponse:
    return create_wallet_nonce(db, payload)


@router.post("/verify", response_model=WalletVerifyResponse)
def post_wallet_verify(payload: WalletVerifyRequest, db: sqlite3.Connection = Depends(get_db)) -> WalletVerifyResponse:
    try:
        verify_wallet_signature(db, payload)
    except WalletAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    agent = repositories.connect_wallet(
        db,
        WalletConnect(
            wallet_address=payload.wallet_address,
            chain_id=payload.chain_id,
            agent_name=payload.agent_name,
            agent_type=payload.agent_type,
        ),
    )
    passport = repositories.build_passport(db, agent["id"])
    if not passport:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found")
    return {
        "verified": True,
        "wallet_address": payload.wallet_address,
        "chain_id": payload.chain_id,
        "passport": passport,
    }
