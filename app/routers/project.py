import sqlite3

from fastapi import APIRouter, Depends

from app.database import get_db
from app.schemas import HackathonAlignmentReport
from app.services.hackathon_alignment import build_hackathon_alignment_report


router = APIRouter(prefix="/project", tags=["project alignment"])

METRIC_TABLES = {
    "agents": "agents",
    "actions": "agent_events",
    "complaints": "complaints",
    "marketplace_listings": "marketplace_listings",
    "rentals": "rentals",
    "automation_policies": "agent_automation_policies",
}


@router.get("/hackathon-alignment", response_model=HackathonAlignmentReport)
def get_hackathon_alignment(db: sqlite3.Connection = Depends(get_db)) -> HackathonAlignmentReport:
    metrics = {
        metric: _count(db, table)
        for metric, table in METRIC_TABLES.items()
    }
    metrics["verified_wallets"] = _count_verified_wallets(db)
    return build_hackathon_alignment_report(metrics)


def _count(db: sqlite3.Connection, table: str) -> int:
    row = db.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
    return int(row["count"] or 0)


def _count_verified_wallets(db: sqlite3.Connection) -> int:
    row = db.execute(
        """
        SELECT COUNT(DISTINCT lower(wallet_address) || ':' || chain_id) AS count
        FROM wallet_auth_nonces
        WHERE used = 1
        """
    ).fetchone()
    return int(row["count"] or 0)
