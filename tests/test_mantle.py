from collections.abc import Iterator
import sqlite3

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient

from app.database import connect, get_db, init_db
from app.main import app
from app.services.mantle import MantleService


def _client() -> tuple[TestClient, sqlite3.Connection]:
    db = connect(":memory:")
    init_db(db)

    def override_db() -> Iterator[sqlite3.Connection]:
        yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), db


def _verified_agent(client: TestClient) -> tuple[int, str]:
    account = Account.create()
    nonce = client.post("/auth/nonce", json={"wallet_address": account.address, "chain_id": 5000}).json()
    signature = Account.sign_message(encode_defunct(text=nonce["message"]), account.key).signature.hex()
    response = client.post(
        "/auth/verify",
        json={
            "wallet_address": account.address,
            "chain_id": 5000,
            "message": nonce["message"],
            "signature": signature,
            "agent_name": "Synced Agent",
        },
    )
    return response.json()["passport"]["agent"]["id"], account.address


def test_sync_requires_verified_wallet() -> None:
    client, db = _client()
    try:
        agent = client.post("/agents", json={"name": "Agent", "agent_type": "wallet-agent", "owner_wallet": "0x1234567890abcdef"}).json()
        response = client.post(f"/mantle/agents/{agent['id']}/sync")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_sync_imports_and_deduplicates_indexed_history(monkeypatch) -> None:
    client, db = _client()
    agent_id, wallet = _verified_agent(client)
    tx_hash = "0x" + "1" * 64
    indexed = [{
        "hash": tx_hash,
        "from": wallet,
        "to": "0x000000000000000000000000000000000000dEaD",
        "value": "1000",
        "blockNumber": "123",
        "timeStamp": "1700000000",
        "isError": "0",
        "txreceipt_status": "1",
    }]
    monkeypatch.setattr(MantleService, "wallet_transactions", lambda self, address, limit=50: indexed)
    try:
        first = client.post(f"/mantle/agents/{agent_id}/sync").json()
        second = client.post(f"/mantle/agents/{agent_id}/sync").json()
        assert first["imported_events"] == 1
        assert second["imported_events"] == 0
        assert second["skipped_duplicates"] == 1
        assert second["passport"]["actions_history"][0]["tx_hash"] == tx_hash
        assert second["passport"]["sync_state"]["last_synced_at"]
    finally:
        app.dependency_overrides.clear()
        db.close()
