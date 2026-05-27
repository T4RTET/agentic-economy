from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from eth_account import Account
from eth_account.messages import encode_defunct


API_BASE = "http://127.0.0.1:8000"
RECIPIENT = "0x000000000000000000000000000000000000dEaD"


def post_json(path: str, payload: dict) -> dict:
    request = Request(
        f"{API_BASE}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"{path} failed: {exc.code} {detail}") from exc


def main() -> None:
    account = Account.create()
    print(f"Generated local test account: {account.address}")

    nonce = post_json("/auth/nonce", {"wallet_address": account.address, "chain_id": 5000})
    signature = Account.sign_message(encode_defunct(text=nonce["message"]), account.key).signature.hex()
    verified = post_json(
        "/auth/verify",
        {
            "wallet_address": account.address,
            "chain_id": 5000,
            "message": nonce["message"],
            "signature": signature,
            "agent_name": "Manual Verified Wallet Agent",
        },
    )

    agent_id = verified["agent_id"]
    prepared = post_json(
        f"/agents/{agent_id}/transactions/prepare",
        {
            "to_address": RECIPIENT,
            "value_wei": "1",
            "value_usd": 0.01,
            "chain_id": 5000,
            "metadata": {"manual_script": True},
        },
    )
    recorded = post_json(
        f"/agents/{agent_id}/transactions/record",
        {
            "tx_hash": "0x" + "2" * 64,
            "outcome": "success",
            "value_usd": 0.01,
            "metadata": {"manual_script": True, "fake_tx_hash": True},
        },
    )

    print(json.dumps({"verified": verified, "prepared": prepared, "recorded": recorded}, indent=2))


if __name__ == "__main__":
    main()
