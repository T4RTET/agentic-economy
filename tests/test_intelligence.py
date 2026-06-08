from collections.abc import Iterator
import sqlite3

from fastapi.testclient import TestClient

from app.database import connect, get_db, init_db
from app.main import app
from app.seed import seed_demo_data


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


def test_low_risk_seeded_agent_allows_wallet_permissions() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.get(f"/agents/{agent_id}/intelligence")

        assert response.status_code == 200
        report = response.json()
        assert report["wallet_permission"]["decision"] == "allow"
        assert report["risk_assessment"]["risk_level"] == "Low"
        assert report["marketplace_verdict"]["can_be_rented"] is True
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_medium_risk_seeded_agent_limits_wallet_permissions() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "SwapScout Beta")

        response = client.get(f"/agents/{agent_id}/intelligence")

        assert response.status_code == 200
        report = response.json()
        assert report["wallet_permission"]["decision"] == "limit"
        assert report["wallet_permission"]["recommended_limit_usd"] <= 1000
        assert "open complaint" in report["wallet_permission"]["reason"]
        assert report["risk_assessment"]["risk_level"] == "Medium"
        assert report["marketplace_verdict"]["can_be_rented"] is True
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_high_risk_seeded_agent_denies_wallet_permissions() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "LeverageHawk Gamma")

        response = client.get(f"/agents/{agent_id}/intelligence")

        assert response.status_code == 200
        report = response.json()
        assert report["wallet_permission"]["decision"] == "deny"
        assert report["wallet_permission"]["recommended_limit_usd"] <= 100
        assert report["risk_assessment"]["risk_level"] == "High"
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_high_risk_or_confirmed_high_complaint_agent_cannot_be_rented() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "LeverageHawk Gamma")

        response = client.get(f"/agents/{agent_id}/intelligence")

        assert response.status_code == 200
        verdict = response.json()["marketplace_verdict"]
        assert verdict["can_be_listed"] is False
        assert verdict["can_be_rented"] is False
        assert "confirmed high-severity complaint" in verdict["reason"]
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_intelligence_endpoint_returns_404_for_missing_agent() -> None:
    client, db = _client_with_seeded_db()
    try:
        response = client.get("/agents/9999/intelligence")

        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_intelligence_response_contains_required_sections() -> None:
    client, db = _client_with_seeded_db()
    try:
        agent_id = _agent_id_by_name(client, "YieldPilot Alpha")

        response = client.get(f"/agents/{agent_id}/intelligence")

        assert response.status_code == 200
        report = response.json()
        assert set(report) == {
            "summary",
            "wallet_permission",
            "risk_assessment",
            "marketplace_verdict",
            "suggested_next_actions",
        }
        assert set(report["wallet_permission"]) == {"decision", "recommended_limit_usd", "reason"}
        assert set(report["risk_assessment"]) == {"risk_level", "main_risks", "confidence"}
        assert set(report["marketplace_verdict"]) == {"can_be_listed", "can_be_rented", "reason"}
        assert isinstance(report["suggested_next_actions"], list)
    finally:
        app.dependency_overrides.clear()
        db.close()
