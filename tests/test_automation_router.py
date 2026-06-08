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

    def override_db() -> Iterator:
        yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), db


def _agent_id_by_name(client: TestClient, name: str) -> int:
    agents = client.get("/agents").json()
    return next(item["agent"]["id"] for item in agents if item["agent"]["name"] == name)


def _policy_payload(mode: str = "manual", **overrides) -> dict:
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
        "value_wei": "1000000000000000",
        "value_usd": 1,
        "chain_id": 5000,
        "reason": "automation router test",
    }
    payload.update(overrides)
    return payload


def test_get_default_policy() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.get(f"/agents/{agent_id}/automation-policy")

        assert response.status_code == 200
        body = response.json()
        assert body["automation_enabled"] is False
        assert body["mode"] == "manual"
        assert body["delegation_status"] == "none"
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_update_policy() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.put(f"/agents/{agent_id}/automation-policy", json=_policy_payload("semi_auto"))

        assert response.status_code == 200
        body = response.json()
        assert body["automation_enabled"] is True
        assert body["mode"] == "semi_auto"
        assert body["allowed_recipients"] == [RECIPIENT]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_update_policy_stores_smart_account_address() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")
        payload = _policy_payload("semi_auto", smart_account_address=SMART_ACCOUNT)

        response = client.put(f"/agents/{agent_id}/automation-policy", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["smart_account_address"] == SMART_ACCOUNT
        assert body["delegation_status"] == "none"
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_evaluate_action() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")
        client.put(f"/agents/{agent_id}/automation-policy", json=_policy_payload("manual"))

        response = client.post(f"/agents/{agent_id}/automation-policy/evaluate", json=_action_payload())

        assert response.status_code == 200
        body = response.json()
        assert body["allowed"] is True
        assert body["requires_user_confirmation"] is True
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_evaluate_action_with_automation_disabled() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(f"/agents/{agent_id}/automation-policy/evaluate", json=_action_payload())

        assert response.status_code == 200
        body = response.json()
        assert body["allowed"] is False
        assert "Automation is disabled" in body["reason"]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_request_delegation() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")
        client.put(f"/agents/{agent_id}/automation-policy", json=_policy_payload("full_auto"))

        response = client.post(f"/agents/{agent_id}/automation/delegation/request")

        assert response.status_code == 200
        body = response.json()
        assert body["delegation_status"] == "requested"
        assert body["request"]["type"] == "metamask_smart_account_delegation"
        assert body["policy_scope"]["allowed_chain_ids"] == [5000]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_confirm_delegation() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(
            f"/agents/{agent_id}/automation/delegation/confirm",
            json={
                "smart_account_address": SMART_ACCOUNT,
                "delegation_id": "local-test-delegation",
                "delegation_scope": {"allowed_chain_ids": [5000]},
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["delegation_status"] == "active"
        assert body["smart_account_address"] == SMART_ACCOUNT
        assert body["delegation_id"] == "local-test-delegation"
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_confirm_delegation_rejects_invalid_smart_account_address() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(
            f"/agents/{agent_id}/automation/delegation/confirm",
            json={
                "smart_account_address": "not-an-address",
                "delegation_id": "local-test-delegation",
                "delegation_scope": {"allowed_chain_ids": [5000]},
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_confirm_delegation_rejects_blank_delegation_id() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(
            f"/agents/{agent_id}/automation/delegation/confirm",
            json={
                "smart_account_address": SMART_ACCOUNT,
                "delegation_id": "   ",
                "delegation_scope": {"allowed_chain_ids": [5000]},
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_confirm_delegation_rejects_empty_delegation_scope() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(
            f"/agents/{agent_id}/automation/delegation/confirm",
            json={
                "smart_account_address": SMART_ACCOUNT,
                "delegation_id": "local-test-delegation",
                "delegation_scope": {},
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_evaluate_action_with_active_delegation() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")
        client.put(f"/agents/{agent_id}/automation-policy", json=_policy_payload("full_auto"))
        client.post(
            f"/agents/{agent_id}/automation/delegation/confirm",
            json={
                "smart_account_address": SMART_ACCOUNT,
                "delegation_id": "local-test-delegation",
                "delegation_scope": {"allowed_chain_ids": [5000]},
            },
        )

        response = client.post(f"/agents/{agent_id}/automation-policy/evaluate", json=_action_payload())

        assert response.status_code == 200
        body = response.json()
        assert body["allowed"] is True
        assert body["can_auto_execute"] is True
        assert body["delegation_required"] is False
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_execute_automated_returns_delegation_required_when_missing() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")
        client.put(f"/agents/{agent_id}/automation-policy", json=_policy_payload("full_auto"))

        response = client.post(f"/agents/{agent_id}/transactions/execute-automated", json=_action_payload())

        assert response.status_code == 200
        body = response.json()
        assert body["delegation_required"] is True
        assert body["status"] == "delegation_required"
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_execute_automated_returns_smart_account_execution_payload_when_policy_allows_and_delegation_active() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")
        client.put(f"/agents/{agent_id}/automation-policy", json=_policy_payload("full_auto"))
        client.post(
            f"/agents/{agent_id}/automation/delegation/confirm",
            json={
                "smart_account_address": SMART_ACCOUNT,
                "delegation_id": "local-test-delegation",
                "delegation_scope": {"allowed_chain_ids": [5000]},
            },
        )

        response = client.post(f"/agents/{agent_id}/transactions/execute-automated", json=_action_payload())

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "prepared"
        assert body["evaluation"]["can_auto_execute"] is True
        assert body["smart_account_execution_payload"]["type"] == "metamask_smart_account_execution"
        assert body["smart_account_execution_payload"]["smart_account_address"] == SMART_ACCOUNT
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_execute_automated_returns_requires_user_confirmation_in_manual_mode() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")
        client.put(f"/agents/{agent_id}/automation-policy", json=_policy_payload("manual"))

        response = client.post(f"/agents/{agent_id}/transactions/execute-automated", json=_action_payload())

        assert response.status_code == 200
        body = response.json()
        assert body["requires_user_confirmation"] is True
        assert body["transaction_request"]["to"] == RECIPIENT
        assert body["status"] == "requires_confirmation"
    finally:
        app.dependency_overrides.clear()
        db.close()
