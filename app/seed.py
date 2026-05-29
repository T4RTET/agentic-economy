import sqlite3

from app.database import connect, init_db
from app.repositories import create_agent, create_complaint, create_event, create_or_update_listing, list_agents, reset_demo_data
from app.schemas import AgentCreate, AgentEventCreate, ComplaintCreate, MarketplaceListingCreate


def seed_demo_data(reset: bool = False, connection: sqlite3.Connection | None = None) -> int:
    db = connection or connect()
    owns_connection = connection is None
    try:
        init_db(db)
        if reset:
            reset_demo_data(db)
        if list_agents(db):
            return len(list_agents(db))

        low_risk = create_agent(
            db,
            AgentCreate(
                name="YieldPilot Alpha",
                description="Autonomous DeFi assistant for conservative mETH and USDY yield routing.",
                agent_type="defi-yield-agent",
                owner_wallet="0x7a4A00000000000000000000000000000000A11a",
            ),
        )
        create_event(db, low_risk["id"], AgentEventCreate(title="Rebalanced mETH position", category="defi", outcome="success", value_usd=5000, tx_hash="0xmantle-low-001"))
        create_event(db, low_risk["id"], AgentEventCreate(title="Audited pool risk before deposit", category="risk-check", outcome="success", value_usd=0))
        create_event(db, low_risk["id"], AgentEventCreate(title="Claimed incentives", category="rewards", outcome="success", value_usd=380, tx_hash="0xmantle-low-002"))
        create_or_update_listing(
            db,
            low_risk["id"],
            MarketplaceListingCreate(
                pricing_model="rent_daily",
                price_usd=240,
                capabilities=["defi-routing", "risk-checks", "yield-optimization"],
                terms="Best for conservative wallet automation with capped permissions.",
            ),
        )

        medium_risk = create_agent(
            db,
            AgentCreate(
                name="SwapScout Beta",
                description="Trading helper that scans swaps and routes small wallet actions.",
                agent_type="trading-agent",
                owner_wallet="0x8b5B00000000000000000000000000000000B22b",
            ),
        )
        create_event(db, medium_risk["id"], AgentEventCreate(title="Executed stablecoin route", category="swap", outcome="success", value_usd=10000, tx_hash="0xmantle-med-001"))
        create_event(db, medium_risk["id"], AgentEventCreate(title="Missed slippage threshold", category="swap", outcome="failed", value_usd=250))
        create_complaint(db, medium_risk["id"], ComplaintCreate(reason="Returned a delayed execution report after a failed route.", severity="low", status="open"))
        create_or_update_listing(
            db,
            medium_risk["id"],
            MarketplaceListingCreate(
                pricing_model="per_task",
                price_usd=45,
                capabilities=["token-swaps", "route-search", "execution-reports"],
                terms="Good for small swap tasks; recommended wallet limit should be respected.",
            ),
        )

        high_risk = create_agent(
            db,
            AgentCreate(
                name="LeverageHawk Gamma",
                description="Experimental leverage strategy agent with limited wallet permissions.",
                agent_type="high-risk-trading-agent",
                owner_wallet="0x9c6C00000000000000000000000000000000C33c",
            ),
        )
        create_event(db, high_risk["id"], AgentEventCreate(title="Opened aggressive strategy", category="leverage", outcome="success", value_usd=700, tx_hash="0xmantle-high-001"))
        create_event(db, high_risk["id"], AgentEventCreate(title="Failed liquidation protection check", category="risk-check", outcome="error", value_usd=1200, tx_hash="0xmantle-high-002"))
        create_event(db, high_risk["id"], AgentEventCreate(title="Reported stale pool data", category="data", outcome="failed", value_usd=0))
        create_complaint(db, high_risk["id"], ComplaintCreate(reason="Agent recommended an unsafe wallet limit for a volatile strategy.", severity="high", status="confirmed"))
        create_complaint(db, high_risk["id"], ComplaintCreate(reason="User disputed the agent's explanation of risk.", severity="medium", status="open"))
        create_or_update_listing(
            db,
            high_risk["id"],
            MarketplaceListingCreate(
                pricing_model="rent_hourly",
                price_usd=15,
                availability="paused",
                capabilities=["leverage-analysis", "experimental-strategies"],
                terms="Paused for high-risk tasks until disputes are resolved.",
            ),
        )
        return len(list_agents(db))
    finally:
        if owns_connection:
            db.close()


if __name__ == "__main__":
    seed_demo_data()
    print("Demo data is ready.")
