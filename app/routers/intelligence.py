import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app import repositories
from app.database import get_db
from app.schemas import AgentIntelligenceReport
from app.services.agent_intelligence import analyze_agent_passport


router = APIRouter(prefix="/agents", tags=["agent intelligence"])


@router.get("/{agent_id}/intelligence", response_model=AgentIntelligenceReport)
def get_agent_intelligence(agent_id: int, db: sqlite3.Connection = Depends(get_db)) -> AgentIntelligenceReport:
    passport = repositories.build_passport(db, agent_id)
    if not passport:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return analyze_agent_passport(passport)
