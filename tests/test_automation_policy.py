import sqlite3

from app.database import connect, init_db
from app.repositories import create_agent, create_automation_attempt
from app.schemas import AgentCreate, AutomationActionRequest
from app.services.automation_policy import evaluate_automation_action


OWNER = "0x1234567890AbcdEF1234567890aBcdef12345678"
RECIPIENT = "0x000000000000000000000000000000000000dEaD"
OTHER_RECIPIENT = "0x1111111111111111111111111111111111111111"
TOKEN = "0x2222222222222222222222222222222222222222"
OTHER_TOKEN = "0x3333333333333333333333333333333333333333"


def _db_and_agent() -> tuple[sqlite3.Connection, int]:
    db = connect(":memory:")
    init_db(db)
    agent = create_agent(
        db,
        AgentCreate(name="Policy Agent", agent_type="test-agent", owner_wallet=OWNER, chain_id=5000),
    )
    return db, agent["id"]


def _passport(agent_id: int, complaints: list[dict] | None = None) -> dict:
    return {
        "agent": {"id": agent_id, "owner_wallet": OWNER, "chain_id": 5000},
        "complaints": complaints or [],
        "actions_history": [],
    }


def _intelligence(decision: str = "allow") -> dict:
    return {
        "wallet_permission": {"decision": decision, "recommended_limit_usd": 100, "reason": "test"},
        "risk_assessment": {"risk_level": "Low"},
    }


def _policy(**overrides) -> dict:
    policy = {
        "automation_enabled": True,
        "mode": "full_auto",
        "max_tx_value_usd": 10,
        "daily_limit_usd": 100,
        "max_transactions_per_hour": 10,
        "min_native_balance_wei": "0",
        "require_confirmation_above_usd": 5,
        "allowed_chain_ids": [5000],
        "allowed_tokens": ["NATIVE"],
        "allowed_recipients": [RECIPIENT],
        "allowed_actions": ["native_transfer"],
        "emergency_stop": False,
        "delegation_status": "active",
    }
    policy.update(overrides)
    return policy


def _action(**overrides) -> dict:
    action = {
        "action_type": "native_transfer",
        "to_address": RECIPIENT,
        "token_address": None,
        "value_wei": "10",
        "value_usd": 1,
        "chain_id": 5000,
    }
    action.update(overrides)
    return action


def _evaluate(db: sqlite3.Connection, agent_id: int, policy: dict, action: dict | None = None, **kwargs) -> dict:
    return evaluate_automation_action(
        db,
        agent_id,
        _passport(agent_id),
        _intelligence(),
        policy,
        action or _action(),
        **kwargs,
    )


def test_automation_disabled_blocks_auto_execution() -> None:
    db, agent_id = _db_and_agent()
    try:
        result = _evaluate(db, agent_id, _policy(automation_enabled=False))

        assert result["allowed"] is False
        assert "Automation is disabled" in result["reason"]
    finally:
        db.close()


def test_emergency_stop_blocks() -> None:
    db, agent_id = _db_and_agent()
    try:
        result = _evaluate(db, agent_id, _policy(emergency_stop=True))

        assert result["allowed"] is False
        assert "Emergency stop" in result["reason"]
    finally:
        db.close()


def test_max_tx_value_blocks() -> None:
    db, agent_id = _db_and_agent()
    try:
        result = _evaluate(db, agent_id, _policy(max_tx_value_usd=1), _action(value_usd=2))

        assert result["allowed"] is False
        assert "max_tx_value_usd" in result["reason"]
    finally:
        db.close()


def test_daily_limit_blocks() -> None:
    db, agent_id = _db_and_agent()
    try:
        create_automation_attempt(db, agent_id, AutomationActionRequest(**_action(value_usd=9)), "executed")

        result = _evaluate(db, agent_id, _policy(daily_limit_usd=10), _action(value_usd=2))

        assert result["allowed"] is False
        assert "daily_limit_usd" in result["reason"]
    finally:
        db.close()


def test_transaction_frequency_blocks() -> None:
    db, agent_id = _db_and_agent()
    try:
        create_automation_attempt(db, agent_id, AutomationActionRequest(**_action()), "prepared")

        result = _evaluate(db, agent_id, _policy(max_transactions_per_hour=1))

        assert result["allowed"] is False
        assert "max_transactions_per_hour" in result["reason"]
    finally:
        db.close()


def test_minimum_balance_blocks() -> None:
    db, agent_id = _db_and_agent()
    try:
        result = _evaluate(
            db,
            agent_id,
            _policy(min_native_balance_wei="5"),
            _action(value_wei="6"),
            current_native_balance_wei=10,
        )

        assert result["allowed"] is False
        assert "min_native_balance_wei" in result["reason"]
    finally:
        db.close()


def test_wrong_chain_blocks() -> None:
    db, agent_id = _db_and_agent()
    try:
        result = _evaluate(db, agent_id, _policy(), _action(chain_id=1))

        assert result["allowed"] is False
        assert "Chain ID" in result["reason"]
    finally:
        db.close()


def test_recipient_not_allowlisted_blocks() -> None:
    db, agent_id = _db_and_agent()
    try:
        result = _evaluate(db, agent_id, _policy(), _action(to_address=OTHER_RECIPIENT))

        assert result["allowed"] is False
        assert "Recipient" in result["reason"]
    finally:
        db.close()


def test_token_not_allowlisted_blocks() -> None:
    db, agent_id = _db_and_agent()
    try:
        result = _evaluate(
            db,
            agent_id,
            _policy(allowed_tokens=[TOKEN], allowed_actions=["erc20_transfer"]),
            _action(action_type="erc20_transfer", token_address=OTHER_TOKEN),
        )

        assert result["allowed"] is False
        assert "Token address" in result["reason"]
    finally:
        db.close()


def test_manual_mode_requires_confirmation() -> None:
    db, agent_id = _db_and_agent()
    try:
        result = _evaluate(db, agent_id, _policy(mode="manual"))

        assert result["allowed"] is True
        assert result["requires_user_confirmation"] is True
        assert result["can_auto_execute"] is False
    finally:
        db.close()


def test_semi_auto_allows_small_transaction_but_requires_confirmation_above_threshold() -> None:
    db, agent_id = _db_and_agent()
    try:
        small = _evaluate(db, agent_id, _policy(mode="semi_auto", require_confirmation_above_usd=5), _action(value_usd=1))
        large = _evaluate(db, agent_id, _policy(mode="semi_auto", require_confirmation_above_usd=5), _action(value_usd=6))

        assert small["can_auto_execute"] is True
        assert large["requires_user_confirmation"] is True
    finally:
        db.close()


def test_full_auto_requires_active_delegation() -> None:
    db, agent_id = _db_and_agent()
    try:
        result = _evaluate(db, agent_id, _policy(mode="full_auto", delegation_status="requested"))

        assert result["allowed"] is True
        assert result["delegation_required"] is True
        assert result["can_auto_execute"] is False
    finally:
        db.close()


def test_active_delegation_allows_auto_execution_when_rules_pass() -> None:
    db, agent_id = _db_and_agent()
    try:
        result = _evaluate(db, agent_id, _policy(mode="full_auto", delegation_status="active"))

        assert result["allowed"] is True
        assert result["can_auto_execute"] is True
        assert result["delegation_required"] is False
    finally:
        db.close()
