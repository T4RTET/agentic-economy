import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app import repositories
from app.database import get_db
from app.schemas import MantleReadinessReport


router = APIRouter(prefix="/mantle", tags=["mantle readiness"])


@router.get("/agents/{agent_id}/readiness", response_model=MantleReadinessReport)
def get_agent_mantle_readiness(
    agent_id: int,
    db: sqlite3.Connection = Depends(get_db),
) -> MantleReadinessReport:
    passport = repositories.build_passport(db, agent_id)
    if not passport:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return passport["mantle_readiness"]
