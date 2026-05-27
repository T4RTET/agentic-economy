from __future__ import annotations

import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> None:
    wallet_address = os.getenv("METAMASK_WALLET_ADDRESS", "").strip()
    if not wallet_address:
        raise SystemExit("METAMASK_WALLET_ADDRESS is required.")

    backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
    chain_id = _env_int("CHAIN_ID", 5000)
    agent_name = os.getenv("AGENT_NAME", "My MetaMask Agent")
    agent_type = os.getenv("AGENT_TYPE", "wallet-linked-agent")

    passport = _post_json(
        f"{backend_url}/wallet/connect",
        {
            "wallet_address": wallet_address,
            "chain_id": chain_id,
            "agent_name": agent_name,
            "agent_type": agent_type,
        },
    )
    agent = passport["agent"]
    intelligence = _get_json(f"{backend_url}/agents/{agent['id']}/intelligence")

    print(f"agent_id={agent['id']}")
    print(f"owner_wallet={agent['owner_wallet']}")
    print(f"wallet_decision={intelligence['wallet_permission']['decision']}")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer.") from exc


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return _send(request)


def _get_json(url: str) -> dict[str, Any]:
    return _send(Request(url, method="GET"))


def _send(request: Request) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise SystemExit(f"Backend returned {exc.code}: {detail}") from exc
    except URLError as exc:
        raise SystemExit(f"Could not reach backend: {exc.reason}") from exc


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
