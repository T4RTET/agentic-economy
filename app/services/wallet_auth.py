from __future__ import annotations

from datetime import UTC, datetime, timedelta
import secrets
import sqlite3
from typing import Any

from eth_account import Account
from eth_account.messages import encode_defunct

from app.schemas import WalletNonceRequest, WalletVerifyRequest
from app.services.wallet_utils import normalize_wallet_address, wallet_addresses_equal


APP_NAME = "Agent Reputation Passport"
NONCE_TTL_MINUTES = 10


class WalletAuthError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def create_wallet_nonce(db: sqlite3.Connection, payload: WalletNonceRequest) -> dict[str, Any]:
    wallet_address = normalize_wallet_address(payload.wallet_address)
    issued_at = _now()
    expires_at = issued_at + timedelta(minutes=NONCE_TTL_MINUTES)
    nonce = secrets.token_urlsafe(24)
    message = build_sign_in_message(
        wallet_address=wallet_address,
        chain_id=payload.chain_id,
        nonce=nonce,
        issued_at=issued_at,
        expires_at=expires_at,
    )

    db.execute(
        """
        INSERT INTO wallet_auth_nonces (wallet_address, chain_id, nonce, message, expires_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (wallet_address, payload.chain_id, nonce, message, _format_datetime(expires_at)),
    )
    db.commit()
    return {
        "wallet_address": wallet_address,
        "chain_id": payload.chain_id,
        "nonce": nonce,
        "message": message,
        "expires_at": _format_datetime(expires_at),
    }


def build_sign_in_message(
    wallet_address: str,
    chain_id: int,
    nonce: str,
    issued_at: datetime,
    expires_at: datetime,
) -> str:
    return (
        f"{APP_NAME} wants you to verify wallet ownership.\n\n"
        f"Wallet: {wallet_address}\n"
        f"Chain ID: {chain_id}\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {_format_datetime(issued_at)}\n"
        f"Expires At: {_format_datetime(expires_at)}\n\n"
        "This signature does not authorize a transaction or transfer funds."
    )


def verify_wallet_signature(db: sqlite3.Connection, payload: WalletVerifyRequest) -> None:
    wallet_address = normalize_wallet_address(payload.wallet_address)
    nonce_record = _find_nonce_record(db, wallet_address, payload.chain_id, payload.message)
    if not nonce_record:
        raise WalletAuthError("Nonce not found for this wallet and message.", 400)
    if int(nonce_record["used"]):
        raise WalletAuthError("Nonce has already been used.", 400)
    if _parse_datetime(nonce_record["expires_at"]) <= _now():
        raise WalletAuthError("Nonce has expired.", 400)

    recovered_address = _recover_address(payload.message, payload.signature)
    if not wallet_addresses_equal(recovered_address, wallet_address):
        raise WalletAuthError("Signature does not match the requested wallet address.", 401)

    db.execute("UPDATE wallet_auth_nonces SET used = 1 WHERE id = ?", (nonce_record["id"],))
    db.commit()


def _find_nonce_record(
    db: sqlite3.Connection,
    wallet_address: str,
    chain_id: int,
    message: str,
) -> dict[str, Any] | None:
    row = db.execute(
        """
        SELECT *
        FROM wallet_auth_nonces
        WHERE lower(wallet_address) = lower(?) AND chain_id = ? AND message = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (wallet_address, chain_id, message),
    ).fetchone()
    return dict(row) if row else None


def _recover_address(message: str, signature: str) -> str:
    try:
        signable_message = encode_defunct(text=message)
        return Account.recover_message(signable_message, signature=signature)
    except Exception as exc:
        raise WalletAuthError("Invalid wallet signature.", 401) from exc


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _format_datetime(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat()


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
