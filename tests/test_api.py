from collections.abc import Iterator

from fastapi.testclient import TestClient

from app.database import connect, get_db, init_db
from app.main import app


def test_agent_passport_flow() -> None:
    db = connect(":memory:")
    init_db(db)

    def override_db() -> Iterator:
        yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        response = client.post(
            "/agents",
            json={
                "name": "Demo Agent",
                "description": "Test agent",
                "agent_type": "wallet-agent",
                "owner_wallet": "0x1234567890abcdef",
                "chain_id": 5000,
            },
        )
        assert response.status_code == 201
        agent_id = response.json()["id"]

        wallet_connect_response = client.post(
            "/wallet/connect",
            json={
                "wallet_address": "0x1234567890abcdef",
                "chain_id": 5000,
                "agent_name": "Wallet Passport Agent",
            },
        )
        assert wallet_connect_response.status_code == 200
        wallet_passport = wallet_connect_response.json()
        assert wallet_passport["agent"]["id"] == agent_id
        assert wallet_passport["analysis"]["summary"].startswith("Trust Score")

        wallet_get_response = client.get("/wallet/0x1234567890abcdef/passport")
        assert wallet_get_response.status_code == 200
        assert wallet_get_response.json()["agent"]["id"] == agent_id

        event_response = client.post(
            f"/agents/{agent_id}/events",
            json={
                "title": "Completed payment task",
                "category": "payment",
                "outcome": "success",
                "value_usd": 1500,
                "tx_hash": "0xabc",
                "metadata": {"counterparty": "demo"},
            },
        )
        assert event_response.status_code == 201

        complaint_response = client.post(
            f"/agents/{agent_id}/complaints",
            json={"reason": "Minor delay in reporting", "severity": "low", "status": "open"},
        )
        assert complaint_response.status_code == 201

        passport_response = client.get(f"/agents/{agent_id}/passport")
        assert passport_response.status_code == 200
        passport = passport_response.json()
        assert passport["agent"]["name"] == "Demo Agent"
        assert passport["marketplace"]["listing"] is None
        assert passport["analysis"]["recommendation"]
        assert passport["mantle_readiness"]["overall_score"] > 0
        assert {item["criterion"] for item in passport["mantle_readiness"]["criteria"]} == {
            "technical",
            "ecosystem_fit",
            "business_potential",
            "innovation",
            "user_experience",
        }
        assert passport["actions_history"][0]["metadata"]["counterparty"] == "demo"
        assert passport["reputation"]["trust_score"] >= 50
        assert passport["reputation"]["risk_level"] in ["Low", "Medium", "High"]

        mantle_response = client.get(f"/mantle/agents/{agent_id}/readiness")
        assert mantle_response.status_code == 200
        assert mantle_response.json()["summary"].startswith("Mantle readiness score")

        list_response = client.get("/agents")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        update_response = client.patch(
            f"/agents/{agent_id}/complaints/{complaint_response.json()['id']}",
            json={"status": "confirmed"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "confirmed"

        reset_response = client.post("/demo/reset")
        assert reset_response.status_code == 200
        assert reset_response.json() == {"status": "reset", "agents_seeded": 3}

        seeded_agents_response = client.get("/agents")
        assert seeded_agents_response.status_code == 200
        assert len(seeded_agents_response.json()) == 3


        marketplace_response = client.get("/marketplace/listings")
        assert marketplace_response.status_code == 200
        listings = marketplace_response.json()
        assert len(listings) == 3
        assert listings[0]["marketplace"]["listing"]["capabilities"]

        listing_id = next(
            item["marketplace"]["listing"]["id"]
            for item in listings
            if item["marketplace"]["listing"]["availability"] == "available"
        )
        rental_response = client.post(
            f"/marketplace/listings/{listing_id}/rent",
            json={
                "renter_wallet": "0xabcdef1234567890",
                "task_title": "Demo marketplace task",
                "task_description": "Find a low-risk route",
                "duration_hours": 3,
            },
        )
        assert rental_response.status_code == 201
        rental = rental_response.json()
        assert rental["status"] == "active"
        assert rental["agreed_price_usd"] > 0

        read_rental_response = client.get(f"/marketplace/rentals/{rental['id']}")
        assert read_rental_response.status_code == 200
        assert read_rental_response.json()["id"] == rental["id"]

        complete_response = client.post(f"/marketplace/rentals/{rental['id']}/complete")
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"

        completed_passport_response = client.get(f"/agents/{rental['agent_id']}/passport")
        assert completed_passport_response.status_code == 200
        assert completed_passport_response.json()["marketplace"]["stats"]["completed_rentals"] == 1

        second_listing_id = next(
            item["marketplace"]["listing"]["id"]
            for item in client.get("/marketplace/listings").json()
            if item["marketplace"]["listing"]["availability"] == "available"
        )
        disputed_rental_response = client.post(
            f"/marketplace/listings/{second_listing_id}/rent",
            json={
                "renter_wallet": "0xabcdef1234567890",
                "task_title": "Disputed marketplace task",
                "duration_hours": 1,
            },
        )
        disputed_rental = disputed_rental_response.json()
        dispute_response = client.post(
            f"/marketplace/rentals/{disputed_rental['id']}/dispute",
            json={"reason": "The agent exceeded the agreed risk profile."},
        )
        assert dispute_response.status_code == 200
        assert dispute_response.json()["status"] == "disputed"
    finally:
        app.dependency_overrides.clear()
        db.close()
