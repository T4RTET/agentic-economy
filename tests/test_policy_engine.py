from app.services.policy_engine import evaluate_transaction_policy


OWNER = "0x1234567890AbcdEF1234567890aBcdef12345678"
RECIPIENT = "0x000000000000000000000000000000000000dEaD"
OTHER_RECIPIENT = "0x1111111111111111111111111111111111111111"


def _passport(chain_id: int = 5000, complaints: list[dict] | None = None) -> dict:
    return {
        "agent": {"id": 1, "owner_wallet": OWNER, "chain_id": chain_id},
        "complaints": complaints or [],
        "actions_history": [],
    }


def _intelligence(decision: str = "allow", limit: int = 100, risk_level: str = "Low") -> dict:
    return {
        "wallet_permission": {"decision": decision, "recommended_limit_usd": limit, "reason": "test"},
        "risk_assessment": {"risk_level": risk_level},
    }


def _transaction(value_usd: float = 1, chain_id: int = 5000, to_address: str = RECIPIENT) -> dict:
    return {"to_address": to_address, "chain_id": chain_id, "value_wei": "1", "value_usd": value_usd}


def test_deny_decision_blocks_transactions() -> None:
    policy = evaluate_transaction_policy(1, _passport(), _intelligence("deny"), _transaction(), "metamask")

    assert policy["allowed"] is False
    assert "deny" in policy["reason"]


def test_over_limit_blocks_transactions() -> None:
    policy = evaluate_transaction_policy(1, _passport(), _intelligence(limit=10), _transaction(11), "metamask")

    assert policy["allowed"] is False
    assert "recommended wallet limit" in policy["reason"]


def test_recipient_allowlist_blocks(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ALLOWED_RECIPIENTS", OTHER_RECIPIENT)

    policy = evaluate_transaction_policy(1, _passport(), _intelligence(), _transaction(), "metamask")

    assert policy["allowed"] is False
    assert "allowlist" in policy["reason"]


def test_autonomous_mode_blocked_when_executor_disabled(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_EXECUTOR_ENABLED", "false")
    monkeypatch.delenv("AGENT_EXECUTOR_PRIVATE_KEY", raising=False)

    policy = evaluate_transaction_policy(1, _passport(), _intelligence(), _transaction(), "autonomous")

    assert policy["allowed"] is False
    assert "Autonomous executor is disabled" in policy["reason"]


def test_mainnet_autonomous_execution_blocked_by_default(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_EXECUTOR_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTOR_PRIVATE_KEY", "0x" + "1" * 64)
    monkeypatch.setenv("AGENT_ALLOWED_CHAIN_IDS", "1")
    monkeypatch.setenv("AGENT_EXECUTOR_ALLOW_MAINNET", "false")

    policy = evaluate_transaction_policy(1, _passport(chain_id=1), _intelligence(), _transaction(chain_id=1), "autonomous")

    assert policy["allowed"] is False
    assert "mainnet" in policy["reason"]
