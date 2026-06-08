from __future__ import annotations

import json
import math
import sqlite3
from typing import Any

from app.reputation import ReputationComplaint, ReputationEvent, calculate_reputation
from app.schemas import (
    AgentCreate,
    AgentEventCreate,
    AutomationActionRequest,
    AutomationPolicyUpdate,
    ComplaintCreate,
    ComplaintUpdate,
    MarketplaceListingCreate,
    RentalCreate,
    WalletConnect,
)
from app.services.wallet_utils import normalize_wallet_address


def create_agent(db: sqlite3.Connection, payload: AgentCreate) -> dict[str, Any]:
    owner_wallet = normalize_wallet_address(payload.owner_wallet)
    existing = get_agent_by_wallet(db, owner_wallet, payload.chain_id)
    if existing:
        return existing

    cursor = db.execute(
        """
        INSERT INTO agents (name, description, agent_type, owner_wallet, chain_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            payload.name,
            payload.description,
            payload.agent_type,
            owner_wallet,
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


def get_agent_by_wallet(db: sqlite3.Connection, wallet_address: str, chain_id: int | None = None) -> dict[str, Any] | None:
    normalized_wallet = normalize_wallet_address(wallet_address)
    query = "SELECT * FROM agents WHERE lower(owner_wallet) = lower(?)"
    params: tuple[Any, ...] = (normalized_wallet,)
    if chain_id is not None:
        query += " AND chain_id = ?"
        params = (normalized_wallet, chain_id)
    query += " ORDER BY created_at DESC, id DESC LIMIT 1"
    row = db.execute(query, params).fetchone()
    return dict(row) if row else None


def connect_wallet(db: sqlite3.Connection, payload: WalletConnect) -> dict[str, Any]:
    wallet_address = normalize_wallet_address(payload.wallet_address)
    existing = get_agent_by_wallet(db, wallet_address, payload.chain_id)
    if existing:
        add_audit_log(db, existing["id"], "wallet.connected", {"wallet_address": wallet_address})
        db.commit()
        return existing

    short_wallet = f"{wallet_address[:6]}...{wallet_address[-4:]}"
    return create_agent(
        db,
        AgentCreate(
            name=payload.agent_name or f"Agent {short_wallet}",
            description="AI agent passport created from a connected wallet.",
            agent_type=payload.agent_type,
            owner_wallet=wallet_address,
            chain_id=payload.chain_id,
        ),
    )


def count_agents(db: sqlite3.Connection) -> int:
    row = db.execute("SELECT COUNT(*) AS count FROM agents").fetchone()
    return int(row["count"])


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
    return dict(row) if row else None


def update_complaint(db: sqlite3.Connection, complaint_id: int, payload: ComplaintUpdate) -> dict[str, Any] | None:
    existing = get_complaint(db, complaint_id)
    if not existing:
        return None

    db.execute("UPDATE complaints SET status = ? WHERE id = ?", (payload.status, complaint_id))
    add_audit_log(
        db,
        existing["agent_id"],
        "complaint.reviewed",
        {"complaint_id": complaint_id, "old_status": existing["status"], "new_status": payload.status},
    )
    db.commit()
    return get_complaint(db, complaint_id)


def reset_demo_data(db: sqlite3.Connection) -> None:
    db.execute("DELETE FROM audit_log")
    db.execute("DELETE FROM agent_automation_attempts")
    db.execute("DELETE FROM agent_automation_policies")
    db.execute("DELETE FROM agent_tasks")
    db.execute("DELETE FROM wallet_auth_nonces")
    db.execute("DELETE FROM rentals")
    db.execute("DELETE FROM marketplace_listings")
    db.execute("DELETE FROM complaints")
    db.execute("DELETE FROM agent_events")
    db.execute("DELETE FROM agents")
    db.execute(
        """
        DELETE FROM sqlite_sequence
        WHERE name IN ('audit_log', 'agent_automation_attempts', 'agent_automation_policies', 'agent_tasks', 'wallet_auth_nonces', 'rentals', 'marketplace_listings', 'complaints', 'agent_events', 'agents')
        """
    )
    db.commit()


def create_or_update_listing(
    db: sqlite3.Connection,
    agent_id: int,
    payload: MarketplaceListingCreate,
) -> dict[str, Any]:
    capabilities_json = json.dumps(payload.capabilities)
    existing = get_listing_by_agent(db, agent_id)
    if existing:
        db.execute(
            """
            UPDATE marketplace_listings
            SET pricing_model = ?, price_usd = ?, price_token = ?, availability = ?,
                capabilities_json = ?, terms = ?, updated_at = CURRENT_TIMESTAMP
            WHERE agent_id = ?
            """,
            (
                payload.pricing_model,
                payload.price_usd,
                payload.price_token,
                payload.availability,
                capabilities_json,
                payload.terms,
                agent_id,
            ),
        )
        action = "listing.updated"
    else:
        db.execute(
            """
            INSERT INTO marketplace_listings
            (agent_id, pricing_model, price_usd, price_token, availability, capabilities_json, terms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agent_id,
                payload.pricing_model,
                payload.price_usd,
                payload.price_token,
                payload.availability,
                capabilities_json,
                payload.terms,
            ),
        )
        action = "listing.created"
    add_audit_log(db, agent_id, action, {"pricing_model": payload.pricing_model, "price_usd": payload.price_usd})
    db.commit()
    return get_listing_by_agent(db, agent_id)


def list_marketplace_cards(db: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = db.execute(
        """
        SELECT agents.*
        FROM agents
        JOIN marketplace_listings ON marketplace_listings.agent_id = agents.id
        ORDER BY marketplace_listings.availability ASC, agents.created_at DESC, agents.id DESC
        """
    ).fetchall()
    return [
        {
            "agent": dict(row),
            "reputation": build_reputation(db, row["id"]),
            "marketplace": build_marketplace_info(db, row["id"]),
        }
        for row in rows
    ]


def get_listing_by_agent(db: sqlite3.Connection, agent_id: int) -> dict[str, Any] | None:
    row = db.execute("SELECT * FROM marketplace_listings WHERE agent_id = ?", (agent_id,)).fetchone()
    return _listing_from_row(row) if row else None


def get_listing(db: sqlite3.Connection, listing_id: int) -> dict[str, Any] | None:
    row = db.execute("SELECT * FROM marketplace_listings WHERE id = ?", (listing_id,)).fetchone()
    return _listing_from_row(row) if row else None


def create_rental(db: sqlite3.Connection, listing_id: int, payload: RentalCreate) -> dict[str, Any] | None:
    listing = get_listing(db, listing_id)
    if not listing or listing["availability"] != "available":
        return None

    agreed_price = _calculate_rental_price(listing, payload.duration_hours)
    renter_wallet = normalize_wallet_address(payload.renter_wallet)
    cursor = db.execute(
        """
        INSERT INTO rentals
        (listing_id, agent_id, renter_wallet, task_title, task_description, duration_hours, agreed_price_usd, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        """,
        (
            listing_id,
            listing["agent_id"],
            renter_wallet,
            payload.task_title,
            payload.task_description,
            payload.duration_hours,
            agreed_price,
        ),
    )
    db.execute(
        "UPDATE marketplace_listings SET availability = 'rented', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (listing_id,),
    )
    add_audit_log(
        db,
        listing["agent_id"],
        "rental.created",
        {"listing_id": listing_id, "task_title": payload.task_title, "agreed_price_usd": agreed_price},
    )
    db.commit()
    return get_rental(db, cursor.lastrowid)


def create_agent_task(
    db: sqlite3.Connection,
    agent_id: int,
    user_goal: str,
    status: str,
    mode: str,
    plan: dict[str, Any],
) -> dict[str, Any]:
    cursor = db.execute(
        """
        INSERT INTO agent_tasks (agent_id, user_goal, status, mode, plan_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (agent_id, user_goal, status, mode, json.dumps(plan)),
    )
    add_audit_log(db, agent_id, "task.planned", {"task_id": cursor.lastrowid, "status": status, "mode": mode})
    db.commit()
    return get_agent_task(db, cursor.lastrowid)


def get_agent_task(db: sqlite3.Connection, task_id: int) -> dict[str, Any] | None:
    row = db.execute("SELECT * FROM agent_tasks WHERE id = ?", (task_id,)).fetchone()
    return _task_from_row(row) if row else None


def update_agent_task(
    db: sqlite3.Connection,
    task_id: int,
    status: str,
    plan: dict[str, Any],
) -> dict[str, Any] | None:
    existing = get_agent_task(db, task_id)
    if not existing:
        return None
    db.execute(
        """
        UPDATE agent_tasks
        SET status = ?, plan_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, json.dumps(plan), task_id),
    )
    add_audit_log(db, existing["agent_id"], "task.updated", {"task_id": task_id, "status": status})
    db.commit()
    return get_agent_task(db, task_id)


def get_or_create_automation_policy(db: sqlite3.Connection, agent_id: int) -> dict[str, Any] | None:
    if not get_agent_or_none(db, agent_id):
        return None

    existing = get_automation_policy(db, agent_id)
    if existing:
        return existing

    cursor = db.execute(
        """
        INSERT INTO agent_automation_policies (agent_id)
        VALUES (?)
        """,
        (agent_id,),
    )
    add_audit_log(db, agent_id, "automation_policy.created", {"policy_id": cursor.lastrowid})
    db.commit()
    return get_automation_policy(db, agent_id)


def get_automation_policy(db: sqlite3.Connection, agent_id: int) -> dict[str, Any] | None:
    row = db.execute("SELECT * FROM agent_automation_policies WHERE agent_id = ?", (agent_id,)).fetchone()
    return _automation_policy_from_row(row) if row else None


def update_automation_policy(
    db: sqlite3.Connection,
    agent_id: int,
    payload: AutomationPolicyUpdate,
) -> dict[str, Any] | None:
    if not get_agent_or_none(db, agent_id):
        return None
    get_or_create_automation_policy(db, agent_id)

    db.execute(
        """
        UPDATE agent_automation_policies
        SET automation_enabled = ?, mode = ?, max_tx_value_usd = ?, daily_limit_usd = ?,
            max_transactions_per_hour = ?, min_native_balance_wei = ?,
            require_confirmation_above_usd = ?, allowed_chain_ids_json = ?,
            allowed_tokens_json = ?, allowed_recipients_json = ?, allowed_actions_json = ?,
            emergency_stop = ?, smart_account_address = COALESCE(?, smart_account_address),
            updated_at = CURRENT_TIMESTAMP
        WHERE agent_id = ?
        """,
        (
            int(payload.automation_enabled),
            payload.mode,
            payload.max_tx_value_usd,
            payload.daily_limit_usd,
            payload.max_transactions_per_hour,
            payload.min_native_balance_wei,
            payload.require_confirmation_above_usd,
            json.dumps(payload.allowed_chain_ids),
            json.dumps(payload.allowed_tokens),
            json.dumps(payload.allowed_recipients),
            json.dumps(payload.allowed_actions),
            int(payload.emergency_stop),
            payload.smart_account_address,
            agent_id,
        ),
    )
    add_audit_log(
        db,
        agent_id,
        "automation_policy.updated",
        {
            "automation_enabled": payload.automation_enabled,
            "mode": payload.mode,
            "max_tx_value_usd": payload.max_tx_value_usd,
            "daily_limit_usd": payload.daily_limit_usd,
            "smart_account_address": payload.smart_account_address,
        },
    )
    db.commit()
    return get_automation_policy(db, agent_id)


def request_automation_delegation(db: sqlite3.Connection, agent_id: int, scope: dict[str, Any]) -> dict[str, Any] | None:
    if not get_agent_or_none(db, agent_id):
        return None
    get_or_create_automation_policy(db, agent_id)
    db.execute(
        """
        UPDATE agent_automation_policies
        SET delegation_status = 'requested', delegation_scope_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE agent_id = ?
        """,
        (json.dumps(scope), agent_id),
    )
    add_audit_log(db, agent_id, "automation_delegation.requested", scope)
    db.commit()
    return get_automation_policy(db, agent_id)


def confirm_automation_delegation(
    db: sqlite3.Connection,
    agent_id: int,
    smart_account_address: str,
    delegation_id: str,
    delegation_scope: dict[str, Any],
) -> dict[str, Any] | None:
    if not get_agent_or_none(db, agent_id):
        return None
    smart_account = normalize_wallet_address(smart_account_address)
    get_or_create_automation_policy(db, agent_id)
    db.execute(
        """
        UPDATE agent_automation_policies
        SET smart_account_address = ?, delegation_id = ?, delegation_status = 'active',
            delegation_scope_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE agent_id = ?
        """,
        (smart_account, delegation_id, json.dumps(delegation_scope), agent_id),
    )
    add_audit_log(
        db,
        agent_id,
        "automation_delegation.confirmed",
        {"smart_account_address": smart_account, "delegation_id": delegation_id},
    )
    db.commit()
    return get_automation_policy(db, agent_id)


def create_automation_attempt(
    db: sqlite3.Connection,
    agent_id: int,
    payload: AutomationActionRequest,
    status: str,
    reason: str = "",
    rejection_reason: str | None = None,
    tx_hash: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cursor = db.execute(
        """
        INSERT INTO agent_automation_attempts
        (agent_id, action_type, to_address, token_address, value_wei, value_usd, chain_id,
         status, tx_hash, reason, rejection_reason, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            agent_id,
            payload.action_type,
            normalize_wallet_address(payload.to_address),
            normalize_wallet_address(payload.token_address) if payload.token_address else None,
            payload.value_wei,
            payload.value_usd,
            payload.chain_id,
            status,
            tx_hash,
            reason,
            rejection_reason,
            json.dumps(metadata or payload.metadata),
        ),
    )
    add_audit_log(
        db,
        agent_id,
        "automation_attempt.created",
        {"attempt_id": cursor.lastrowid, "status": status, "action_type": payload.action_type},
    )
    db.commit()
    return get_automation_attempt(db, cursor.lastrowid)


def get_automation_attempt(db: sqlite3.Connection, attempt_id: int) -> dict[str, Any]:
    row = db.execute("SELECT * FROM agent_automation_attempts WHERE id = ?", (attempt_id,)).fetchone()
    return _automation_attempt_from_row(row)


def automation_daily_value_usd(db: sqlite3.Connection, agent_id: int) -> float:
    row = db.execute(
        """
        SELECT COALESCE(SUM(value_usd), 0) AS total
        FROM agent_automation_attempts
        WHERE agent_id = ? AND status = 'executed' AND date(created_at) = date('now')
        """,
        (agent_id,),
    ).fetchone()
    return float(row["total"] or 0)


def automation_hourly_count(db: sqlite3.Connection, agent_id: int) -> int:
    row = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM agent_automation_attempts
        WHERE agent_id = ?
          AND status IN ('prepared', 'requires_confirmation', 'delegation_required', 'executed')
          AND created_at >= datetime('now', '-1 hour')
        """,
        (agent_id,),
    ).fetchone()
    return int(row["total"] or 0)


def get_rental(db: sqlite3.Connection, rental_id: int) -> dict[str, Any] | None:
    row = db.execute("SELECT * FROM rentals WHERE id = ?", (rental_id,)).fetchone()
    return dict(row) if row else None


def complete_rental(db: sqlite3.Connection, rental_id: int) -> dict[str, Any] | None:
    rental = get_rental(db, rental_id)
    if not rental or rental["status"] not in {"pending", "active"}:
        return None

    db.execute(
        "UPDATE rentals SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (rental_id,),
    )
    db.execute(
        "UPDATE marketplace_listings SET availability = 'available', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (rental["listing_id"],),
    )
    create_event(
        db,
        rental["agent_id"],
        AgentEventCreate(
            title=f"Completed rental: {rental['task_title']}",
            category="marketplace-rental",
            outcome="success",
            value_usd=rental["agreed_price_usd"],
            metadata={"rental_id": rental_id, "renter_wallet": rental["renter_wallet"]},
        ),
    )
    add_audit_log(db, rental["agent_id"], "rental.completed", {"rental_id": rental_id})
    db.commit()
    return get_rental(db, rental_id)


def dispute_rental(db: sqlite3.Connection, rental_id: int, reason: str) -> dict[str, Any] | None:
    rental = get_rental(db, rental_id)
    if not rental or rental["status"] not in {"pending", "active", "completed"}:
        return None

    db.execute("UPDATE rentals SET status = 'disputed' WHERE id = ?", (rental_id,))
    db.execute(
        "UPDATE marketplace_listings SET availability = 'available', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (rental["listing_id"],),
    )
    create_complaint(
        db,
        rental["agent_id"],
        ComplaintCreate(reason=reason, severity="medium", status="open"),
    )
    add_audit_log(db, rental["agent_id"], "rental.disputed", {"rental_id": rental_id, "reason": reason})
    db.commit()
    return get_rental(db, rental_id)


def build_marketplace_info(db: sqlite3.Connection, agent_id: int) -> dict[str, Any]:
    listing = get_listing_by_agent(db, agent_id)
    stats = db.execute(
        """
        SELECT
            COUNT(*) AS rentals_count,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_rentals,
            SUM(CASE WHEN status = 'disputed' THEN 1 ELSE 0 END) AS disputed_rentals
        FROM rentals
        WHERE agent_id = ?
        """,
        (agent_id,),
    ).fetchone()
    rentals_count = int(stats["rentals_count"] or 0)
    completed = int(stats["completed_rentals"] or 0)
    disputed = int(stats["disputed_rentals"] or 0)
    completion_rate = round(completed / rentals_count, 2) if rentals_count else 0.0
    return {
        "listing": listing,
        "stats": {
            "rentals_count": rentals_count,
            "completed_rentals": completed,
            "disputed_rentals": disputed,
            "completion_rate": completion_rate,
        },
    }


def build_passport(db: sqlite3.Connection, agent_id: int) -> dict[str, Any] | None:
    agent = get_agent_or_none(db, agent_id)
    if not agent:
        return None

    reputation = build_reputation(db, agent_id)
    events = list_events(db, agent_id)
    complaints = list_complaints(db, agent_id)
    marketplace = build_marketplace_info(db, agent_id)
    return {
        "agent": agent,
        "reputation": reputation,
        "marketplace": marketplace,
        "analysis": build_passport_analysis(reputation, events, complaints, marketplace),
        "actions_history": events,
        "complaints": complaints,
        "audit_log": list_audit_log(db, agent_id),
    }


def build_passport_analysis(
    reputation: dict[str, Any],
    events: list[dict[str, Any]],
    complaints: list[dict[str, Any]],
    marketplace: dict[str, Any],
) -> dict[str, Any]:
    trust_score = reputation["trust_score"]
    risk_level = reputation["risk_level"]
    successful_events = [event for event in events if event["outcome"] == "success"]
    failed_events = [event for event in events if event["outcome"] in {"failed", "error"}]
    active_complaints = [item for item in complaints if item["status"] != "dismissed"]

    strengths: list[str] = []
    risk_flags: list[str] = []

    if successful_events:
        strengths.append(f"{len(successful_events)} successful action(s) recorded")
    if reputation["successful_volume_usd"] > 0:
        strengths.append(f"${reputation['successful_volume_usd']} successfully handled")
    if marketplace["stats"]["completed_rentals"] > 0:
        strengths.append(f"{marketplace['stats']['completed_rentals']} completed marketplace rental(s)")
    if not strengths:
        strengths.append("New passport with no negative history yet")

    if failed_events:
        risk_flags.append(f"{len(failed_events)} failed/error action(s)")
    if active_complaints:
        risk_flags.append(f"{len(active_complaints)} active complaint(s)")
    if risk_level == "High":
        risk_flags.append("High risk score: keep wallet permissions very limited")
    if not risk_flags:
        risk_flags.append("No active risk flags")

    if risk_level == "Low":
        recommendation = "Suitable for broader wallet permissions within the recommended limit."
    elif risk_level == "Medium":
        recommendation = "Use with capped wallet permissions and monitor new actions."
    else:
        recommendation = "Use only for low-value tasks or review manually before granting wallet access."

    return {
        "summary": f"Trust Score {trust_score}/100, Risk Level {risk_level}.",
        "strengths": strengths,
        "risk_flags": risk_flags,
        "recommendation": recommendation,
    }


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


def _listing_from_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["capabilities"] = json.loads(item.pop("capabilities_json") or "[]")
    return item


def _task_from_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["plan"] = json.loads(item.pop("plan_json") or "{}")
    return item


def _automation_policy_from_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["automation_enabled"] = bool(item["automation_enabled"])
    item["emergency_stop"] = bool(item["emergency_stop"])
    item["allowed_chain_ids"] = json.loads(item.pop("allowed_chain_ids_json") or "[]")
    item["allowed_tokens"] = json.loads(item.pop("allowed_tokens_json") or "[]")
    item["allowed_recipients"] = json.loads(item.pop("allowed_recipients_json") or "[]")
    item["allowed_actions"] = json.loads(item.pop("allowed_actions_json") or "[]")
    item["delegation_scope"] = json.loads(item.pop("delegation_scope_json") or "{}")
    return item


def _automation_attempt_from_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
    return item


def _calculate_rental_price(listing: dict[str, Any], duration_hours: int) -> float:
    if listing["pricing_model"] == "rent_hourly":
        return round(listing["price_usd"] * duration_hours, 2)
    if listing["pricing_model"] == "rent_daily":
        days = max(1, math.ceil(duration_hours / 24))
        return round(listing["price_usd"] * days, 2)
    return round(listing["price_usd"], 2)
