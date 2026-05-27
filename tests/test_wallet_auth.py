from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
import sqlite3

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient

from app.database import connect, get_db, init_db
from app.main import app
from app.services.wallet_utils import normalize_wallet_address


DEMO_WALLET = "0x1234567890abcdef1234567890abcdef12345678"


def _client_with_db() -> tuple[TestClient, sqlite3.Connection]:
    db = connect(":memory:")
    init_db(db)

    def override_db() -> Iterator:
        yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), db


def _signed_verification_payload(account, message: str, **overrides) -> dict:
    signature = Account.sign_message(encode_defunct(text=message), account.key).signature.hex()
    payload = {
        "wallet_address": account.address,
        "chain_id": 5000,
        "message": message,
        "signature": signature,
        "agent_name": "Verified Wallet Agent",
    }
    payload.update(overrides)
    return payload


def _nonce_response(client: TestClient, wallet_address: str, chain_id: int = 5000) -> dict:
    response = client.post("/auth/nonce", json={"wallet_address": wallet_address, "chain_id": chain_id})
    assert response.status_code == 200
    return response.json()


def test_auth_nonce_returns_message_and_nonce() -> None:
    client, db = _client_with_db()
    account = Account.create()
    try:
        nonce = _nonce_response(client, account.address)

        assert nonce["wallet_address"] == normalize_wallet_address(account.address)
        assert nonce["chain_id"] == 5000
        assert nonce["nonce"]
        assert account.address in nonce["message"]
        assert "This signature does not authorize a transaction or transfer funds." in nonce["message"]
        assert nonce["expires_at"]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_valid_signature_verifies_and_returns_passport() -> None:
    client, db = _client_with_db()
    account = Account.create()
    try:
        nonce = _nonce_response(client, account.address)

        response = client.post("/auth/verify", json=_signed_verification_payload(account, nonce["message"]))

        assert response.status_code == 200
        body = response.json()
        assert body["verified"] is True
        assert body["agent_id"] == body["passport"]["agent"]["id"]
        assert body["wallet_address"] == account.address
        assert body["passport"]["agent"]["owner_wallet"] == account.address
        assert body["passport"]["agent"]["name"] == "Verified Wallet Agent"
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_wrong_wallet_address_fails_verification() -> None:
    client, db = _client_with_db()
    signer = Account.create()
    requested_wallet = Account.create()
    try:
        nonce = _nonce_response(client, requested_wallet.address)
        signature = Account.sign_message(encode_defunct(text=nonce["message"]), signer.key).signature.hex()

        response = client.post(
            "/auth/verify",
            json={
                "wallet_address": requested_wallet.address,
                "chain_id": 5000,
                "message": nonce["message"],
                "signature": signature,
            },
        )

        assert response.status_code == 401
        assert "does not match" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_reusing_same_nonce_fails() -> None:
    client, db = _client_with_db()
    account = Account.create()
    try:
        nonce = _nonce_response(client, account.address)
        payload = _signed_verification_payload(account, nonce["message"])

        assert client.post("/auth/verify", json=payload).status_code == 200
        response = client.post("/auth/verify", json=payload)

        assert response.status_code == 400
        assert "already been used" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_expired_nonce_fails() -> None:
    client, db = _client_with_db()
    account = Account.create()
    try:
        nonce = _nonce_response(client, account.address)
        expired_at = (datetime.now(UTC) - timedelta(minutes=1)).replace(microsecond=0).isoformat()
        db.execute("UPDATE wallet_auth_nonces SET expires_at = ? WHERE nonce = ?", (expired_at, nonce["nonce"]))
        db.commit()

        response = client.post("/auth/verify", json=_signed_verification_payload(account, nonce["message"]))

        assert response.status_code == 400
        assert "expired" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_existing_wallet_connect_still_works() -> None:
    client, db = _client_with_db()
    try:
        response = client.post(
            "/wallet/connect",
            json={
                "wallet_address": DEMO_WALLET,
                "chain_id": 5000,
                "agent_name": "Demo Wallet Agent",
            },
        )

        assert response.status_code == 200
        assert response.json()["agent"]["owner_wallet"] == normalize_wallet_address(DEMO_WALLET)
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_intelligence_endpoint_works_after_verified_wallet_connection() -> None:
    client, db = _client_with_db()
    account = Account.create()
    try:
        nonce = _nonce_response(client, account.address)
        verify_response = client.post("/auth/verify", json=_signed_verification_payload(account, nonce["message"]))
        agent_id = verify_response.json()["passport"]["agent"]["id"]

        response = client.get(f"/agents/{agent_id}/intelligence")

        assert response.status_code == 200
        assert response.json()["wallet_permission"]["decision"] in {"allow", "limit", "deny"}
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_verify_response_normalizes_wallet_address() -> None:
    client, db = _client_with_db()
    account = Account.create()
    lowercase_wallet = account.address.lower()
    try:
        nonce = _nonce_response(client, lowercase_wallet)

        response = client.post(
            "/auth/verify",
            json=_signed_verification_payload(account, nonce["message"], wallet_address=lowercase_wallet),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["wallet_address"] == account.address
        assert body["passport"]["agent"]["owner_wallet"] == account.address
    finally:
        app.dependency_overrides.clear()
        db.close()
