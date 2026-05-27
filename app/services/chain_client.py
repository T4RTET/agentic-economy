from __future__ import annotations

import os
from typing import Any, Literal

from app.services.wallet_utils import normalize_wallet_address, validate_tx_hash


TransactionStatus = Literal["pending", "success", "failed", "not_found"]


class ChainClientUnavailable(Exception):
    pass


def configured_chain_id() -> int:
    return int(os.getenv("CHAIN_ID", "5000"))


def get_native_balance(wallet_address: str) -> int:
    web3 = _web3()
    return int(web3.eth.get_balance(normalize_wallet_address(wallet_address)))


def get_transaction_receipt(tx_hash: str) -> dict[str, Any] | None:
    if not validate_tx_hash(tx_hash):
        raise ValueError("Invalid transaction hash")

    web3 = _web3()
    try:
        receipt = web3.eth.get_transaction_receipt(tx_hash)
    except Exception as exc:
        if "not found" in str(exc).lower():
            return None
        raise
    return dict(receipt) if receipt else None


def get_transaction_status(tx_hash: str) -> TransactionStatus:
    if not validate_tx_hash(tx_hash):
        raise ValueError("Invalid transaction hash")

    web3 = _web3()
    try:
        receipt = web3.eth.get_transaction_receipt(tx_hash)
    except Exception as exc:
        if "not found" not in str(exc).lower():
            raise
        try:
            web3.eth.get_transaction(tx_hash)
            return "pending"
        except Exception:
            return "not_found"

    if receipt is None:
        return "pending"
    return "success" if int(receipt.get("status", 0)) == 1 else "failed"


def _web3():
    rpc_url = os.getenv("RPC_URL")
    if not rpc_url:
        raise ChainClientUnavailable("RPC_URL is not configured.")

    try:
        from web3 import Web3
    except Exception as exc:
        raise ChainClientUnavailable("web3 is not installed.") from exc

    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise ChainClientUnavailable("RPC_URL is not reachable.")
    return web3
