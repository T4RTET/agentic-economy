from collections.abc import Iterator
import sqlite3

from fastapi.testclient import TestClient

from app.database import connect, get_db, init_db
from app.main import app
from app.seed import seed_demo_data


RECIPIENT = "0x000000000000000000000000000000000000dEaD"
VALID_TX_HASH = "0x" + "1" * 64
FAKE_TEST_TX_HASH = "0xtesttransaction123"


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


def _prepare_payload(value_usd: float, **overrides) -> dict:
    payload = {
        "to_address": RECIPIENT,
        "value_wei": "1000000000000000",
        "value_usd": value_usd,
        "chain_id": 5000,
        "title": "Test wallet transaction",
        "category": "wallet-transaction",
        "metadata": {"note": "prepared for user signature"},
    }
    payload.update(overrides)
    return payload


def test_low_risk_agent_can_prepare_transaction() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(f"/agents/{agent_id}/transactions/prepare", json=_prepare_payload(25))

        assert response.status_code == 200
        body = response.json()
        assert body["agent_id"] == agent_id
        assert body["from_address"] == "0x7A4A00000000000000000000000000000000a11a"
        assert body["to_address"] == RECIPIENT
        assert body["value_wei"] == "1000000000000000"
        assert body["wallet_decision"] == "allow"
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
        assert "deny" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_medium_risk_agent_cannot_exceed_recommended_limit() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "SwapScout Beta")

        response = client.post(f"/agents/{agent_id}/transactions/prepare", json=_prepare_payload(1001))

        assert response.status_code == 403
        assert "recommended wallet limit" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_invalid_recipient_fails() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(
            f"/agents/{agent_id}/transactions/prepare",
            json=_prepare_payload(25, to_address="0xnot-a-wallet"),
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_wrong_chain_id_fails() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(f"/agents/{agent_id}/transactions/prepare", json=_prepare_payload(25, chain_id=1))

        assert response.status_code == 400
        assert "chain_id" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_prepare_response_contains_metamask_transaction_request() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(f"/agents/{agent_id}/transactions/prepare", json=_prepare_payload(25))

        assert response.status_code == 200
        tx_request = response.json()["transaction_request"]
        assert tx_request == {
            "from": "0x7A4A00000000000000000000000000000000a11a",
            "to": RECIPIENT,
            "value": "0x38d7ea4c68000",
            "chainId": "0x1388",
        }
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_prepare_accepts_frontend_recipient_payload_and_legacy_fields() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        payload = _prepare_payload(25)
        payload["recipient_address"] = payload.pop("to_address")
        payload["reason"] = "Test transaction prepared by agent"

        response = client.post(f"/agents/{agent_id}/transactions/prepare", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["from"] == "0x7A4A00000000000000000000000000000000a11a"
        assert body["to"] == RECIPIENT
        assert body["value"] == "1000000000000000"
        assert body["reason"] == "Test transaction prepared by agent"
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_record_endpoint_saves_tx_hash_in_actions_history() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(
            f"/agents/{agent_id}/transactions/record",
            json={
                "tx_hash": VALID_TX_HASH,
                "outcome": "success",
                "value_usd": 42,
                "metadata": {"recipient": RECIPIENT},
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["event"]["tx_hash"] == VALID_TX_HASH
        assert body["event"]["metadata"]["source"] == "transaction_record"
        assert body["event"]["metadata"]["recorded_by"] == "wallet_ui_or_agent"

        history = body["passport"]["actions_history"]
        assert any(event["tx_hash"] == VALID_TX_HASH for event in history)
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_fake_frontend_tx_hash_records_for_backend_testing() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(
            f"/agents/{agent_id}/transactions/record",
            json={
                "tx_hash": FAKE_TEST_TX_HASH,
                "outcome": "success",
                "value_usd": 1,
                "metadata": {"source": "test_frontend_fake_record"},
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["event"]["tx_hash"] == FAKE_TEST_TX_HASH
        assert any(event["tx_hash"] == FAKE_TEST_TX_HASH for event in body["passport"]["actions_history"])
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_invalid_tx_hash_fails_recording() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(
            f"/agents/{agent_id}/transactions/record",
            json={"tx_hash": "0xabc", "outcome": "success", "value_usd": 1},
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
        db.close()
