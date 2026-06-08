from __future__ import annotations

import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen


API_BASE = "http://127.0.0.1:8000"


def post_json(path: str, payload: dict) -> dict:
    request = Request(
        f"{API_BASE}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"{path} failed: {exc.code} {detail}") from exc


def main() -> None:
    if os.getenv("AGENT_EXECUTOR_ENABLED", "false").lower() not in {"1", "true", "yes", "on"}:
        raise SystemExit("AGENT_EXECUTOR_ENABLED must be true for this manual test.")
    if not os.getenv("RPC_URL"):
        raise SystemExit("RPC_URL is required.")
    if not os.getenv("AGENT_EXECUTOR_PRIVATE_KEY"):
        raise SystemExit("AGENT_EXECUTOR_PRIVATE_KEY is required.")

    chain_id = int(os.getenv("CHAIN_ID", "5000"))
    if chain_id == 1 and os.getenv("AGENT_EXECUTOR_ALLOW_MAINNET", "false").lower() not in {"1", "true", "yes", "on"}:
        raise SystemExit("Refusing mainnet autonomous execution unless AGENT_EXECUTOR_ALLOW_MAINNET=true.")

    agent_id = int(os.getenv("AGENT_ID", "1"))
    to_address = os.getenv("TO_ADDRESS", "0x000000000000000000000000000000000000dEaD")
    value_wei = os.getenv("VALUE_WEI", "1")
    value_usd = float(os.getenv("VALUE_USD", "0.01"))

    result = post_json(
        f"/agents/{agent_id}/transactions/execute-autonomous",
        {
            "to_address": to_address,
            "value_wei": value_wei,
            "value_usd": value_usd,
            "chain_id": chain_id,
            "metadata": {"manual_script": True},
            "confirm_policy_ack": True,
        },
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
