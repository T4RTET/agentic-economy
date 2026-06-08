from collections.abc import Iterator
import sqlite3

from fastapi.testclient import TestClient

from app.database import connect, get_db, init_db
from app.main import app
from app.schemas import AutonomousTransactionRequest, TransactionPrepareRequest, WalletVerifyRequest
from app.seed import seed_demo_data
from app.services.agent_executor import execute_transaction_if_allowed


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


def _low_risk_passport() -> dict:
    return {
        "agent": {"id": 1, "owner_wallet": "0x1234567890AbcdEF1234567890aBcdef12345678", "chain_id": 5000},
        "complaints": [],
        "actions_history": [],
    }


def _intelligence(decision: str = "allow", risk_level: str = "Low") -> dict:
    return {
        "wallet_permission": {"decision": decision, "recommended_limit_usd": 100, "reason": "test"},
        "risk_assessment": {"risk_level": risk_level},
    }


def _request(chain_id: int = 5000) -> dict:
    return {"to_address": RECIPIENT, "chain_id": chain_id, "value_wei": "1", "value_usd": 1}


def test_no_private_key_in_request_schemas() -> None:
    for model in (TransactionPrepareRequest, AutonomousTransactionRequest, WalletVerifyRequest):
        field_names = " ".join(model.model_fields)
        assert "private" not in field_names.lower()
        assert "seed" not in field_names.lower()


def test_executor_disabled_returns_403(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_EXECUTOR_ENABLED", "false")
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(
            f"/agents/{agent_id}/transactions/execute-autonomous",
            json={
                "to_address": RECIPIENT,
                "value_wei": "1",
                "value_usd": 1,
                "chain_id": 5000,
                "confirm_policy_ack": True,
            },
        )

        assert response.status_code == 403
        assert "Autonomous executor is disabled" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_executor_requires_env_private_key(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_EXECUTOR_ENABLED", "true")
    monkeypatch.delenv("AGENT_EXECUTOR_PRIVATE_KEY", raising=False)

    result = execute_transaction_if_allowed(1, _request(), _low_risk_passport(), _intelligence())

    assert result["executed"] is False
    assert "AGENT_EXECUTOR_PRIVATE_KEY" in result["reason"]


def test_executor_cannot_run_on_mainnet_by_default(monkeypatch) -> None:
    passport = _low_risk_passport()
    passport["agent"]["chain_id"] = 1
    monkeypatch.setenv("AGENT_EXECUTOR_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTOR_PRIVATE_KEY", "0x" + "1" * 64)
    monkeypatch.setenv("AGENT_ALLOWED_CHAIN_IDS", "1")
    monkeypatch.setenv("AGENT_EXECUTOR_ALLOW_MAINNET", "false")

    result = execute_transaction_if_allowed(1, _request(chain_id=1), passport, _intelligence())

    assert result["executed"] is False
    assert "mainnet" in result["reason"]


def test_policy_violations_prevent_signing(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_EXECUTOR_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTOR_PRIVATE_KEY", "0x" + "1" * 64)

    def fail_if_called():
        raise AssertionError("Signing path should not be reached")

    monkeypatch.setattr("app.services.agent_executor._web3", fail_if_called)

    result = execute_transaction_if_allowed(1, _request(), _low_risk_passport(), _intelligence("deny", "High"))

    assert result["executed"] is False
    assert "deny" in result["reason"]
