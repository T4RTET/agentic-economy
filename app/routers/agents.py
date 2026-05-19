import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app import repositories
from app.schemas import (
    Agent,
    AgentCreate,
    AgentEvent,
    AgentEventCreate,
    AgentPassport,
    AgentSummary,
    Complaint,
    ComplaintCreate,
    Reputation,
)


router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentSummary])
def get_agents(db: sqlite3.Connection = Depends(get_db)) -> list[AgentSummary]:
    return [
        {"agent": agent, "reputation": repositories.build_reputation(db, agent["id"])}
        for agent in repositories.list_agents(db)
    ]


@router.post("", response_model=Agent, status_code=status.HTTP_201_CREATED)
def post_agent(payload: AgentCreate, db: sqlite3.Connection = Depends(get_db)) -> Agent:
    return repositories.create_agent(db, payload)


@router.get("/{agent_id}/passport", response_model=AgentPassport)
def get_agent_passport(agent_id: int, db: sqlite3.Connection = Depends(get_db)) -> AgentPassport:
    agent = _require_agent(db, agent_id)
    return {
        "agent": agent,
        "reputation": repositories.build_reputation(db, agent_id),
        "actions_history": repositories.list_events(db, agent_id),
        "complaints": repositories.list_complaints(db, agent_id),
        "audit_log": repositories.list_audit_log(db, agent_id),
    }


@router.get("/{agent_id}/reputation", response_model=Reputation)
def get_agent_reputation(agent_id: int, db: sqlite3.Connection = Depends(get_db)) -> Reputation:
    _require_agent(db, agent_id)
    return repositories.build_reputation(db, agent_id)


@router.post("/{agent_id}/events", response_model=AgentEvent, status_code=status.HTTP_201_CREATED)
def post_agent_event(
    agent_id: int,
    payload: AgentEventCreate,
    db: sqlite3.Connection = Depends(get_db),
) -> AgentEvent:
    _require_agent(db, agent_id)
    return repositories.create_event(db, agent_id, payload)


@router.post("/{agent_id}/complaints", response_model=Complaint, status_code=status.HTTP_201_CREATED)
def post_agent_complaint(
    agent_id: int,
    payload: ComplaintCreate,
    db: sqlite3.Connection = Depends(get_db),
) -> Complaint:
    _require_agent(db, agent_id)
    return repositories.create_complaint(db, agent_id, payload)


def _require_agent(db: sqlite3.Connection, agent_id: int) -> dict:
    agent = repositories.get_agent_or_none(db, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent
