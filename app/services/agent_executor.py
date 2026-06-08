from __future__ import annotations

import os
from typing import Any

from eth_account import Account

from app.services.policy_engine import evaluate_transaction_policy
from app.services.wallet_utils import int_to_hex_quantity, normalize_wallet_address


class AgentExecutorError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def is_executor_enabled() -> bool:
    return os.getenv("AGENT_EXECUTOR_ENABLED", "false").lower() in {"1", "true", "yes", "on"}


def get_executor_address() -> str | None:
    private_key = os.getenv("AGENT_EXECUTOR_PRIVATE_KEY")
    if not private_key:
        return None
    return normalize_wallet_address(Account.from_key(private_key).address)


def execute_transaction_if_allowed(
    agent_id: int,
    request: dict[str, Any],
    passport: dict[str, Any],
    intelligence: dict[str, Any],
) -> dict[str, Any]:
    policy = evaluate_transaction_policy(agent_id, passport, intelligence, request, "autonomous")
    if not policy["allowed"]:
        return {
            "executed": False,
            "status": "rejected",
            "reason": policy["reason"],
            "violations": policy["violations"],
        }

    private_key = os.getenv("AGENT_EXECUTOR_PRIVATE_KEY")
    if not is_executor_enabled():
        raise AgentExecutorError("Autonomous executor is disabled. Use /transactions/prepare and sign with MetaMask.")
    if not private_key:
        raise AgentExecutorError("AGENT_EXECUTOR_PRIVATE_KEY is not configured.")

    web3 = _web3()
    account = Account.from_key(private_key)
    executor_address = normalize_wallet_address(account.address)
    to_address = normalize_wallet_address(request["to_address"])
    chain_id = int(request["chain_id"])
    value_wei = int(request["value_wei"])

    tx = {
        "from": executor_address,
        "to": to_address,
        "value": value_wei,
        "chainId": chain_id,
        "nonce": web3.eth.get_transaction_count(executor_address),
    }
    gas_estimate = web3.eth.estimate_gas(tx)
    tx["gas"] = gas_estimate
    tx["gasPrice"] = web3.eth.gas_price

    required_balance = value_wei + (int(tx["gas"]) * int(tx["gasPrice"]))
    balance = int(web3.eth.get_balance(executor_address))
    if balance < required_balance:
        raise AgentExecutorError("Executor wallet balance is too low for value plus estimated gas.")

    signed = Account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction).hex()
    return {
        "executed": True,
        "status": "submitted",
        "tx_hash": tx_hash,
        "executor_address": executor_address,
        "transaction_request": {
            "from": executor_address,
            "to": to_address,
            "value": int_to_hex_quantity(value_wei),
            "chainId": int_to_hex_quantity(chain_id),
        },
    }


def _web3():
    rpc_url = os.getenv("RPC_URL")
    if not rpc_url:
        raise AgentExecutorError("RPC_URL is not configured.")

    try:
        from web3 import Web3
    except Exception as exc:
        raise AgentExecutorError("web3 is not installed.") from exc

    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise AgentExecutorError("RPC_URL is not reachable.")
    return web3
