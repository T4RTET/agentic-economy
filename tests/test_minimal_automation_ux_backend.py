from collections.abc import Iterator
import sqlite3

from fastapi.testclient import TestClient

from app.database import connect, get_db, init_db
from app.main import app
from app.seed import seed_demo_data


RECIPIENT = "0x000000000000000000000000000000000000dEaD"
SMART_ACCOUNT = "0x4444444444444444444444444444444444444444"


def _client_with_seeded_db() -> tuple[TestClient, sqlite3.Connection]:
    db = connect(":memory:")
    init_db(db)
    seed_demo_data(connection=db)

    def override_db() -> Iterator[sqlite3.Connection]:
        yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), db


def _agent_id_by_name(client: TestClient, name: str) -> int:
    agents = client.get("/agents").json()
    return next(item["agent"]["id"] for item in agents if item["agent"]["name"] == name)


def _policy_payload(mode: str = "semi_auto", **overrides) -> dict:
    payload = {
        "automation_enabled": True,
        "mode": mode,
        "max_tx_value_usd": 10,
        "daily_limit_usd": 100,
        "max_transactions_per_hour": 10,
        "min_native_balance_wei": "0",
        "require_confirmation_above_usd": 5,
        "allowed_chain_ids": [5000],
        "allowed_tokens": ["NATIVE"],
        "allowed_recipients": [RECIPIENT],
        "allowed_actions": ["native_transfer"],
        "emergency_stop": False,
    }
    payload.update(overrides)
    return payload


def _action_payload(**overrides) -> dict:
    payload = {
        "action_type": "native_transfer",
        "to_address": RECIPIENT,
        "value_wei": "1",
        "value_usd": 1,
        "chain_id": 5000,
        "reason": "minimal automation ux test",
    }
    payload.update(overrides)
    return payload


def _confirm_delegation(client: TestClient, agent_id: int) -> None:
    response = client.post(
        f"/agents/{agent_id}/automation/delegation/confirm",
        json={
            "smart_account_address": SMART_ACCOUNT,
            "delegation_id": f"local-test-delegation-{agent_id}",
            "delegation_scope": {"allowed_chain_ids": [5000]},
        },
    )
    assert response.status_code == 200


def test_evaluate_action_with_automation_disabled() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")
        response = client.post(f"/agents/{agent_id}/automation-policy/evaluate", json=_action_payload())
        assert response.status_code == 200
        body = response.json()
        assert body["allowed"] is False
        assert body["can_auto_execute"] is False
        assert "disabled" in body["reason"].lower()
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_evaluate_action_with_active_delegation() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")
        client.put(f"/agents/{agent_id}/automation-policy", json=_policy_payload("full_auto"))
        _confirm_delegation(client, agent_id)

        response = client.post(f"/agents/{agent_id}/automation-policy/evaluate", json=_action_payload())
        assert response.status_code == 200
        body = response.json()
        assert body["allowed"] is True
        assert body["requires_user_confirmation"] is False
        assert body["can_auto_execute"] is True
        assert body["delegation_required"] is False
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_execute_automated_returns_smart_account_execution_payload_when_policy_allows() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")
        client.put(f"/agents/{agent_id}/automation-policy", json=_policy_payload("full_auto"))
        _confirm_delegation(client, agent_id)

        response = client.post(f"/agents/{agent_id}/transactions/execute-automated", json=_action_payload())
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "prepared"
        assert body["requires_user_confirmation"] is False
        assert body["delegation_required"] is False
        assert body["smart_account_execution_payload"]["type"] == "metamask_smart_account_execution"
    finally:
        app.dependency_overrides.clear()
        db.close()
