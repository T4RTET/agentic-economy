from collections.abc import Iterator
import sqlite3

from fastapi.testclient import TestClient

from app.database import connect, get_db, init_db
from app.main import app
from app.seed import seed_demo_data


RECIPIENT = "0x000000000000000000000000000000000000dEaD"


def _client_with_seeded_db() -> tuple[TestClient, sqlite3.Connection]:
    db = connect(":memory:")
    init_db(db)
    seed_demo_data(connection=db)

    def override_db() -> Iterator:
        yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), db


def _agent_id_by_name(client: TestClient, name: str) -> int:
    agents = client.get("/agents").json()
    return next(item["agent"]["id"] for item in agents if item["agent"]["name"] == name)


def _prepare_payload(value_usd: float) -> dict:
    return {
        "recipient_address": RECIPIENT,
        "value_usd": value_usd,
        "value_wei": "1000000000000000",
        "chain_id": 5000,
        "reason": "Test transaction prepared for user signature.",
    }


def test_low_risk_agent_can_prepare_small_transaction() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(f"/agents/{agent_id}/transactions/prepare", json=_prepare_payload(25))

        assert response.status_code == 200
        body = response.json()
        assert body["from"] == "0x7a4A00000000000000000000000000000000A11a"
        assert body["to"] == RECIPIENT
        assert body["value"] == "1000000000000000"
        assert body["chain_id"] == 5000
        assert body["requires_user_signature"] is True
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_high_risk_agent_cannot_prepare_transaction() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "LeverageHawk Gamma")

        response = client.post(f"/agents/{agent_id}/transactions/prepare", json=_prepare_payload(5))

        assert response.status_code == 403
        assert "Wallet permission denied" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_medium_risk_agent_cannot_exceed_recommended_limit() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "SwapScout Beta")

        response = client.post(f"/agents/{agent_id}/transactions/prepare", json=_prepare_payload(1001))

        assert response.status_code == 400
        assert "recommended wallet limit" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_record_endpoint_saves_tx_hash_in_actions_history() -> None:
    client, db = _client_with_seeded_db()
    tx_hash = "0xtesttransaction123"
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(
            f"/agents/{agent_id}/transactions/record",
            json={
                "tx_hash": tx_hash,
                "outcome": "success",
                "value_usd": 42,
                "metadata": {"recipient": RECIPIENT, "note": "recorded after user signature"},
            },
        )

        assert response.status_code == 201
        assert response.json()["event"]["tx_hash"] == tx_hash

        passport_response = client.get(f"/agents/{agent_id}/passport")
        assert passport_response.status_code == 200
        history = passport_response.json()["actions_history"]
        assert any(event["tx_hash"] == tx_hash for event in history)
    finally:
        app.dependency_overrides.clear()
        db.close()
