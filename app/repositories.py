from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.reputation import ReputationComplaint, ReputationEvent, calculate_reputation
from app.schemas import AgentCreate, AgentEventCreate, ComplaintCreate


def create_agent(db: sqlite3.Connection, payload: AgentCreate) -> dict[str, Any]:
    cursor = db.execute(
        """
        INSERT INTO agents (name, description, agent_type, owner_wallet, chain_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            payload.name,
            payload.description,
            payload.agent_type,
            payload.owner_wallet,
            payload.chain_id,
            payload.status,
        ),
    )
    agent_id = cursor.lastrowid
    add_audit_log(db, agent_id, "agent.created", {"name": payload.name})
    db.commit()
    return get_agent_or_none(db, agent_id)


def list_agents(db: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute("SELECT * FROM agents ORDER BY created_at DESC, id DESC")]


def get_agent_or_none(db: sqlite3.Connection, agent_id: int) -> dict[str, Any] | None:
    row = db.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    return dict(row) if row else None


def create_event(db: sqlite3.Connection, agent_id: int, payload: AgentEventCreate) -> dict[str, Any]:
    cursor = db.execute(
        """
        INSERT INTO agent_events (agent_id, title, category, outcome, value_usd, tx_hash, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            agent_id,
            payload.title,
            payload.category,
            payload.outcome,
            payload.value_usd,
            payload.tx_hash,
            json.dumps(payload.metadata),
        ),
    )
    add_audit_log(
        db,
        agent_id,
        "event.created",
        {"title": payload.title, "outcome": payload.outcome, "value_usd": payload.value_usd},
    )
    db.commit()
    return get_event(db, cursor.lastrowid)


def list_events(db: sqlite3.Connection, agent_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        "SELECT * FROM agent_events WHERE agent_id = ? ORDER BY created_at DESC, id DESC",
        (agent_id,),
    ).fetchall()
    return [_event_from_row(row) for row in rows]


def get_event(db: sqlite3.Connection, event_id: int) -> dict[str, Any]:
    row = db.execute("SELECT * FROM agent_events WHERE id = ?", (event_id,)).fetchone()
    return _event_from_row(row)


def create_complaint(db: sqlite3.Connection, agent_id: int, payload: ComplaintCreate) -> dict[str, Any]:
    cursor = db.execute(
        """
        INSERT INTO complaints (agent_id, reason, severity, status)
        VALUES (?, ?, ?, ?)
        """,
        (agent_id, payload.reason, payload.severity, payload.status),
    )
    add_audit_log(
        db,
        agent_id,
        "complaint.created",
        {"severity": payload.severity, "status": payload.status},
    )
    db.commit()
    return get_complaint(db, cursor.lastrowid)


def list_complaints(db: sqlite3.Connection, agent_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        "SELECT * FROM complaints WHERE agent_id = ? ORDER BY created_at DESC, id DESC",
        (agent_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_complaint(db: sqlite3.Connection, complaint_id: int) -> dict[str, Any]:
    row = db.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    return dict(row)


def list_audit_log(db: sqlite3.Connection, agent_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        "SELECT * FROM audit_log WHERE agent_id = ? ORDER BY created_at DESC, id DESC",
        (agent_id,),
    ).fetchall()
    return [_audit_from_row(row) for row in rows]


def add_audit_log(db: sqlite3.Connection, agent_id: int | None, action: str, details: dict[str, Any]) -> None:
    db.execute(
        "INSERT INTO audit_log (agent_id, action, details) VALUES (?, ?, ?)",
        (agent_id, action, json.dumps(details)),
    )


def build_reputation(db: sqlite3.Connection, agent_id: int) -> dict[str, Any]:
    events = [
        ReputationEvent(outcome=row["outcome"], value_usd=row["value_usd"])
        for row in db.execute("SELECT outcome, value_usd FROM agent_events WHERE agent_id = ?", (agent_id,))
    ]
    complaints = [
        ReputationComplaint(severity=row["severity"], status=row["status"])
        for row in db.execute("SELECT severity, status FROM complaints WHERE agent_id = ?", (agent_id,))
    ]
    return calculate_reputation(events, complaints).__dict__


def _event_from_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
    return item


def _audit_from_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["details"] = json.loads(item["details"] or "{}")
    return item
