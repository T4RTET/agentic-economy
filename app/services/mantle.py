from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.config import settings


class MantleServiceError(Exception):
    pass


class MantleService:
    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self.transport = transport

    def network_status(self) -> dict[str, Any]:
        chain_id = int(self._rpc("eth_chainId", []), 16)
        block_number = int(self._rpc("eth_blockNumber", []), 16)
        return {
            "connected": chain_id == settings.mantle_chain_id,
            "chain_id": chain_id,
            "latest_block": block_number,
            "rpc_url": settings.mantle_rpc_url,
            "explorer_url": settings.mantle_explorer_url,
            "history_sync_configured": bool(settings.etherscan_api_key),
        }

    def verify_transaction(self, tx_hash: str, expected_wallet: str | None = None) -> dict[str, Any]:
        transaction = self._rpc("eth_getTransactionByHash", [tx_hash])
        if not transaction:
            raise MantleServiceError("Transaction was not found on Mantle.")
        receipt = self._rpc("eth_getTransactionReceipt", [tx_hash])
        block = self._rpc("eth_getBlockByNumber", [transaction["blockNumber"], False]) if transaction.get("blockNumber") else None
        involved = not expected_wallet or expected_wallet.lower() in {
            str(transaction.get("from", "")).lower(),
            str(transaction.get("to", "")).lower(),
        }
        return {
            "tx_hash": tx_hash,
            "verified": bool(receipt and involved),
            "wallet_involved": involved,
            "outcome": "success" if receipt and int(receipt.get("status", "0x0"), 16) == 1 else "failed",
            "from_address": transaction.get("from"),
            "to_address": transaction.get("to"),
            "value_wei": str(int(transaction.get("value", "0x0"), 16)),
            "block_number": int(transaction["blockNumber"], 16) if transaction.get("blockNumber") else None,
            "timestamp": _timestamp(block),
            "explorer_url": f"{settings.mantle_explorer_url}/tx/{tx_hash}",
        }

    def wallet_transactions(self, wallet_address: str, limit: int = 50) -> list[dict[str, Any]]:
        if not settings.etherscan_api_key:
            raise MantleServiceError("ETHERSCAN_API_KEY is required for indexed wallet history sync.")
        params = {
            "chainid": settings.mantle_chain_id,
            "module": "account",
            "action": "txlist",
            "address": wallet_address,
            "page": 1,
            "offset": max(1, min(limit, 100)),
            "sort": "desc",
            "apikey": settings.etherscan_api_key,
        }
        try:
            with httpx.Client(timeout=20, transport=self.transport) as client:
                response = client.get(settings.etherscan_api_url, params=params)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MantleServiceError("Mantle history indexer is unavailable.") from exc
        if data.get("status") == "0" and "No transactions" not in str(data.get("message")):
            raise MantleServiceError(str(data.get("result") or data.get("message") or "History sync failed."))
        return data.get("result", []) if isinstance(data.get("result"), list) else []

    def _rpc(self, method: str, params: list[Any]) -> Any:
        try:
            with httpx.Client(timeout=15, transport=self.transport) as client:
                response = client.post(
                    settings.mantle_rpc_url,
                    json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MantleServiceError("Mantle RPC is unavailable.") from exc
        if data.get("error"):
            raise MantleServiceError(str(data["error"].get("message", "Mantle RPC request failed.")))
        return data.get("result")


def indexed_transaction_to_event(item: dict[str, Any], wallet_address: str) -> dict[str, Any]:
    is_sender = str(item.get("from", "")).lower() == wallet_address.lower()
    status = str(item.get("isError", "0")) == "0" and str(item.get("txreceipt_status", "1")) != "0"
    timestamp = datetime.fromtimestamp(int(item.get("timeStamp", 0)), tz=UTC).replace(microsecond=0).isoformat()
    tx_hash = str(item["hash"])
    return {
        "title": "Mantle outgoing transaction" if is_sender else "Mantle incoming transaction",
        "category": "onchain-transfer",
        "outcome": "success" if status else "failed",
        "value_usd": 0,
        "tx_hash": tx_hash,
        "created_at": timestamp,
        "metadata": {
            "source": "mantle-indexer",
            "from": item.get("from"),
            "to": item.get("to"),
            "value_wei": item.get("value", "0"),
            "block_number": item.get("blockNumber"),
            "explorer_url": f"{settings.mantle_explorer_url}/tx/{tx_hash}",
        },
    }


def _timestamp(block: dict[str, Any] | None) -> str | None:
    if not block or not block.get("timestamp"):
        return None
    return datetime.fromtimestamp(int(block["timestamp"], 16), tz=UTC).replace(microsecond=0).isoformat()
