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


def _plan_payload(mode: str = "metamask") -> dict:
    return {
        "goal": f"Send 0.001 MNT to {RECIPIENT}",
        "mode": mode,
        "estimated_value_usd": 1,
        "to_address": RECIPIENT,
        "value_wei": "1000000000000000",
        "chain_id": 5000,
    }


def test_metamask_mode_produces_requires_signature() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(f"/agents/{agent_id}/tasks/plan", json=_plan_payload())

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "requires_signature"
        assert body["mode"] == "metamask"
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_autonomous_mode_rejects_when_executor_disabled(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_EXECUTOR_ENABLED", "false")
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(f"/agents/{agent_id}/tasks/plan", json=_plan_payload("autonomous"))

        assert response.status_code == 200
        assert response.json()["status"] == "rejected"
        assert "Autonomous executor is disabled" in response.json()["plan"]["reason"]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_plan_includes_required_safety_steps() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.post(f"/agents/{agent_id}/tasks/plan", json=_plan_payload())

        assert response.status_code == 200
        steps = response.json()["plan"]["steps"]
        assert "verify wallet binding" in steps
        assert "evaluate policy" in steps
        assert "record tx_hash" in steps
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_denied_high_risk_agent_task_is_rejected() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "LeverageHawk Gamma")

        response = client.post(f"/agents/{agent_id}/tasks/plan", json=_plan_payload())

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "rejected"
        assert "deny" in body["plan"]["reason"]
    finally:
        app.dependency_overrides.clear()
        db.close()
