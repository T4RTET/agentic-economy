from __future__ import annotations

from typing import Any


def build_hackathon_alignment_report(metrics: dict[str, int]) -> dict[str, Any]:
    return {
        "project_name": "Agent Reputation Passport",
        "track_fit": "Mantle AI-agent economy infrastructure for wallet-linked agent trust and controlled wallet permissions.",
        "positioning": (
            "The project is not only an agent directory. It is a reputation and safety layer that lets users "
            "inspect an AI agent before granting wallet access or using it in an agent labor marketplace."
        ),
        "demo_story": [
            "User connects MetaMask and signs a nonce to prove wallet ownership.",
            "Backend creates or loads the wallet-linked agent passport.",
            "Passport shows Trust Score, Risk Level, wallet limit, actions, complaints, and audit log.",
            "Agent intelligence explains whether wallet access should be allowed, limited, or denied.",
            "Smart Account automation policy demonstrates controlled semi/full-auto execution boundaries.",
            "Marketplace endpoints remain available as phase 2: rent/list agents after trust review.",
        ],
        "judging_criteria": [
            _technical_alignment(),
            _ecosystem_alignment(),
            _business_alignment(),
            _innovation_alignment(),
            _ux_alignment(),
        ],
        "backend_demo_metrics": metrics,
        "non_goals": [
            "Hackathon judging criteria are not used as an agent Trust Score formula.",
            "Backend never accepts private keys or seed phrases.",
            "Marketplace is phase 2 support, while the primary demo is wallet -> passport -> intelligence.",
        ],
    }


def _technical_alignment() -> dict[str, Any]:
    return {
        "criterion": "technical",
        "label": "Technical quality",
        "weight_percent": 30,
        "project_evidence": [
            "FastAPI backend with typed Pydantic schemas and automatic OpenAPI docs.",
            "SQLite persistence for agents, actions, complaints, marketplace listings, rentals, wallet auth, and automation policy.",
            "Automated test coverage for API flows, wallet auth, reputation scoring, intelligence, and automation policy.",
        ],
        "backend_features": [
            "MetaMask nonce/signature verification",
            "Explainable Trust Score breakdown",
            "Audit log",
            "Smart Account automation policy guardrails",
            "Wallet-limit recommendations",
        ],
        "demo_endpoints": [
            "POST /auth/nonce",
            "POST /auth/verify",
            "GET /agents/{agent_id}/passport",
            "GET /agents/{agent_id}/intelligence",
            "GET /agents/{agent_id}/automation/policy",
        ],
        "improvement_notes": [
            "For production, replace SQLite with managed Postgres and add migrations.",
            "Add real Mantle RPC reads for tx verification after MVP.",
        ],
    }


def _ecosystem_alignment() -> dict[str, Any]:
    return {
        "criterion": "ecosystem_fit",
        "label": "Mantle ecosystem fit",
        "weight_percent": 20,
        "project_evidence": [
            "Agents are tied to EVM wallets and Mantle chain ids 5000/5001.",
            "Agent events store tx_hash and DeFi/CeFi categories for Mantle explorer-ready history.",
            "Wallet permission limits directly support safer autonomous agent activity on Mantle.",
        ],
        "backend_features": [
            "chain_id on agents and actions",
            "tx_hash evidence in action history",
            "DeFi/risk-check/swap demo categories",
            "Smart Account automation constraints",
        ],
        "demo_endpoints": [
            "GET /wallet/{wallet_address}/passport?chain_id=5000",
            "POST /agents/{agent_id}/events",
            "POST /agents/{agent_id}/automation/evaluate",
        ],
        "improvement_notes": [
            "Add live Mantle explorer links in frontend using stored tx_hash and chain_id.",
            "Add read-only Mantle RPC validation for tx_hash evidence.",
        ],
    }


def _business_alignment() -> dict[str, Any]:
    return {
        "criterion": "business_potential",
        "label": "Business potential",
        "weight_percent": 20,
        "project_evidence": [
            "Users need trust signals before letting autonomous agents touch wallets.",
            "Recommended wallet limits translate reputation into a concrete economic control.",
            "Marketplace/listing/rental backend supports the future agent labor market business model.",
        ],
        "backend_features": [
            "recommended_wallet_limit_usd",
            "marketplace listings",
            "rentals and disputes",
            "complaints as reputation inputs",
        ],
        "demo_endpoints": [
            "GET /marketplace/listings",
            "POST /marketplace/listings/{listing_id}/rent",
            "POST /marketplace/rentals/{rental_id}/dispute",
        ],
        "improvement_notes": [
            "Add pricing/token settlement integration after the passport demo is stable.",
            "Add organization/team accounts for agent operators.",
        ],
    }


def _innovation_alignment() -> dict[str, Any]:
    return {
        "criterion": "innovation",
        "label": "Innovation",
        "weight_percent": 20,
        "project_evidence": [
            "Reputation is explainable and action-based, not a simple like/dislike rating.",
            "Passport combines wallet verification, on-chain evidence, task history, complaints, and automation safety.",
            "The system turns agent behavior into reusable trust infrastructure for agentic finance.",
        ],
        "backend_features": [
            "score_breakdown",
            "agent intelligence report",
            "risk-based wallet decision",
            "automation guardrails",
        ],
        "demo_endpoints": [
            "GET /agents/{agent_id}/reputation",
            "GET /agents/{agent_id}/intelligence",
            "POST /agents/{agent_id}/complaints",
        ],
        "improvement_notes": [
            "Add richer task attestations and third-party verifier signatures.",
            "Add category-specific sub-scores for DeFi, trading, audit, and research agents.",
        ],
    }


def _ux_alignment() -> dict[str, Any]:
    return {
        "criterion": "user_experience",
        "label": "User experience",
        "weight_percent": 10,
        "project_evidence": [
            "Primary flow is simple: connect wallet, sign message, view passport.",
            "Backend gives frontend-ready summaries, risk flags, recommendations, and wallet access decisions.",
            "The UI does not need to recalculate risk, reducing integration complexity.",
        ],
        "backend_features": [
            "human-readable passport analysis",
            "agent intelligence next actions",
            "stable JSON response shapes",
            "demo reset endpoint",
        ],
        "demo_endpoints": [
            "POST /demo/reset",
            "POST /wallet/connect",
            "GET /agents/{agent_id}/passport",
        ],
        "improvement_notes": [
            "Frontend should lead with one flagship Low-risk agent and one High-risk contrast case.",
            "Show score changes after adding a successful action or complaint.",
        ],
    }
