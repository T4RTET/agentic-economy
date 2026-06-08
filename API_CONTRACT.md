# Agent Reputation Passport API Contract

Base URL:

```text
http://127.0.0.1:8000
```

Swagger/OpenAPI:

```text
http://127.0.0.1:8000/docs
```

## Mode 1: Demo Wallet Binding

`POST /wallet/connect` is retained for demos and compatibility. It does not prove wallet ownership.

```http
POST /wallet/connect
Content-Type: application/json

{
  "wallet_address": "0x7a4A00000000000000000000000000000000A11a",
  "chain_id": 5000,
  "agent_name": "YieldPilot Alpha",
  "agent_type": "defi-yield-agent"
}
```

The backend validates and stores wallet addresses in checksum format.

## Mode 2: Secure MetaMask Binding

1. Frontend connects MetaMask and reads the selected wallet address.
2. Frontend calls `POST /auth/nonce`.
3. Frontend asks MetaMask to sign `message` with `personal_sign`.
4. Frontend sends `wallet_address`, `chain_id`, `message`, and `signature` to `POST /auth/verify`.
5. Backend verifies ownership and returns `agent_id` and the passport.
6. Frontend calls `GET /agents/{agent_id}/intelligence`.

```http
POST /auth/nonce
Content-Type: application/json

{
  "wallet_address": "0x7a4A00000000000000000000000000000000A11a",
  "chain_id": 5000
}
```

```json
{
  "wallet_address": "0x7A4A00000000000000000000000000000000a11a",
  "chain_id": 5000,
  "nonce": "generated-random-nonce",
  "message": "Agent Reputation Passport wants you to verify wallet ownership...",
  "expires_at": "2026-05-24T14:00:00+00:00"
}
```

```http
POST /auth/verify
Content-Type: application/json

{
  "wallet_address": "0x7a4A00000000000000000000000000000000A11a",
  "chain_id": 5000,
  "message": "Agent Reputation Passport wants you to verify wallet ownership...",
  "signature": "0x...",
  "agent_name": "YieldPilot Alpha",
  "agent_type": "defi-yield-agent"
}
```

```json
{
  "verified": true,
  "agent_id": 1,
  "wallet_address": "0x7A4A00000000000000000000000000000000a11a",
  "chain_id": 5000,
  "passport": {
    "agent": {},
    "reputation": {},
    "marketplace": {},
    "analysis": {},
    "actions_history": [],
    "complaints": [],
    "audit_log": []
  }
}
```

Nonce messages expire, can be used only once, and do not authorize transactions or transfers.

## Mode 3: User-Approved Transaction Mode

`POST /agents/{agent_id}/transactions/prepare` checks the passport, intelligence report, wallet decision, recommended limit, complaint state, chain ID, and recipient address. It does not sign or send.

```http
POST /agents/{agent_id}/transactions/prepare
Content-Type: application/json

{
  "to_address": "0x000000000000000000000000000000000000dEaD",
  "value_wei": "1000000000000000",
  "value_usd": 1.5,
  "chain_id": 5000,
  "title": "Prepared wallet transaction",
  "category": "wallet-transaction",
  "metadata": {
    "purpose": "testnet payment"
  }
}
```

Response:

```json
{
  "agent_id": 1,
  "from_address": "0x7A4A00000000000000000000000000000000a11a",
  "to_address": "0x000000000000000000000000000000000000dEaD",
  "chain_id": 5000,
  "value_wei": "1000000000000000",
  "value_usd": 1.5,
  "requires_user_signature": true,
  "wallet_decision": "allow",
  "recommended_limit_usd": 5460,
  "transaction_request": {
    "from": "0x7A4A00000000000000000000000000000000a11a",
    "to": "0x000000000000000000000000000000000000dEaD",
    "value": "0x38d7ea4c68000",
    "chainId": "0x1388"
  },
  "reason": "Policy checks passed."
}
```

Frontend sends the returned `transaction_request` with:

```ts
ethereum.request({ method: "eth_sendTransaction", params: [transaction_request] })
```

Then the frontend records the result:

```http
POST /agents/{agent_id}/transactions/record
Content-Type: application/json

{
  "tx_hash": "0x1111111111111111111111111111111111111111111111111111111111111111",
  "outcome": "success",
  "value_usd": 1.5,
  "title": "Wallet transaction recorded",
  "category": "wallet-transaction",
  "metadata": {
    "recipient": "0x000000000000000000000000000000000000dEaD"
  }
}
```

The backend stores `tx_hash`, adds `source=transaction_record` and `recorded_by=wallet_ui_or_agent`, then returns the event, updated passport, and updated intelligence report.

## Mode 4: Autonomous Testnet Executor Mode

`POST /agents/{agent_id}/transactions/execute-autonomous` uses a separate executor wallet loaded from `AGENT_EXECUTOR_PRIVATE_KEY`. It is disabled by default.

```http
POST /agents/{agent_id}/transactions/execute-autonomous
Content-Type: application/json

{
  "to_address": "0x000000000000000000000000000000000000dEaD",
  "value_wei": "1",
  "value_usd": 0.01,
  "chain_id": 5000,
  "metadata": {
    "purpose": "tiny testnet transfer"
  },
  "confirm_policy_ack": true
}
```

If disabled:

```json
{
  "detail": "Autonomous executor is disabled. Use /transactions/prepare and sign with MetaMask."
}
```

If enabled and allowed:

```json
{
  "executed": true,
  "tx_hash": "0x...",
  "executor_address": "0x...",
  "passport": {},
  "intelligence": {}
}
```

Autonomous execution requires all policy checks to pass:

- wallet decision is not `deny`
- `value_usd` is within the recommended limit
- `value_wei` is within `AGENT_MAX_TX_VALUE_WEI`
- recipient is allowed when `AGENT_ALLOWED_RECIPIENTS` is set
- chain ID is in `AGENT_ALLOWED_CHAIN_IDS`
- mainnet is blocked unless `AGENT_EXECUTOR_ALLOW_MAINNET=true`
- executor wallet has enough balance for value plus estimated gas

## Mode 5: MetaMask Smart Account Automation

Normal MetaMask EOA wallets cannot silently auto-confirm transactions. Every normal EOA transaction still requires user approval in MetaMask. Automatic execution for a user-controlled wallet requires MetaMask Smart Accounts / Delegation / Advanced Permissions. Never paste a seed phrase into this app.

Get or create the current policy:

```http
GET /agents/{agent_id}/automation-policy
```

Update policy limits:

```http
PUT /agents/{agent_id}/automation-policy
Content-Type: application/json

{
  "automation_enabled": true,
  "mode": "semi_auto",
  "max_tx_value_usd": 5,
  "daily_limit_usd": 25,
  "max_transactions_per_hour": 3,
  "min_native_balance_wei": "0",
  "require_confirmation_above_usd": 2,
  "allowed_chain_ids": [31337],
  "allowed_tokens": ["NATIVE"],
  "allowed_recipients": ["0x000000000000000000000000000000000000dEaD"],
  "allowed_actions": ["native_transfer"],
  "emergency_stop": false
}
```

Evaluate an action without executing:

```http
POST /agents/{agent_id}/automation-policy/evaluate
Content-Type: application/json

{
  "action_type": "native_transfer",
  "to_address": "0x000000000000000000000000000000000000dEaD",
  "value_wei": "1000000000000000",
  "value_usd": 1,
  "chain_id": 31337,
  "reason": "local test"
}
```

Request delegation metadata:

```http
POST /agents/{agent_id}/automation/delegation/request
```

Confirm delegation after the user grants Smart Account permission in MetaMask:

```http
POST /agents/{agent_id}/automation/delegation/confirm
Content-Type: application/json

{
  "smart_account_address": "0x...",
  "delegation_id": "metamask-delegation-id",
  "delegation_scope": {}
}
```

Prepare automated execution:

```http
POST /agents/{agent_id}/transactions/execute-automated
Content-Type: application/json

{
  "action_type": "native_transfer",
  "to_address": "0x000000000000000000000000000000000000dEaD",
  "value_wei": "1000000000000000",
  "value_usd": 1,
  "chain_id": 31337,
  "reason": "local test"
}
```

The response can be one of:

- `delegation_required=true`: grant Smart Account delegation first.
- `requires_user_confirmation=true`: submit `transaction_request` with normal MetaMask `eth_sendTransaction`.
- `smart_account_execution_payload`: submit with MetaMask Smart Accounts Kit. The backend does not sign it.

## Agent Tasks

Plan:

```http
POST /agents/{agent_id}/tasks/plan
Content-Type: application/json

{
  "goal": "Send 0.001 MNT to 0x000000000000000000000000000000000000dEaD",
  "mode": "metamask",
  "estimated_value_usd": 1.5,
  "to_address": "0x000000000000000000000000000000000000dEaD",
  "value_wei": "1000000000000000",
  "chain_id": 5000
}
```

Execute:

```http
POST /agents/{agent_id}/tasks/{task_id}/execute
```

MetaMask tasks return a `transaction_request` with `requires_user_signature=true`. Autonomous tasks use the guarded executor flow.

## Read-Only Chain Endpoints

These require `RPC_URL`; otherwise they return `503`.

```http
GET /wallet/{wallet_address}/balance?chain_id=5000
GET /transactions/{tx_hash}/status
```

Balance response:

```json
{
  "wallet_address": "0xChecksumAddress",
  "chain_id": 5000,
  "balance_wei": "1000000000000000"
}
```

Status response:

```json
{
  "tx_hash": "0x...",
  "status": "pending"
}
```

## Intelligence

```http
GET /agents/{agent_id}/intelligence
```

```json
{
  "summary": "YieldPilot Alpha has Trust Score 82/100 with Low risk. Wallet access decision: allow.",
  "wallet_permission": {
    "decision": "allow",
    "recommended_limit_usd": 5460,
    "reason": "Trust Score 82/100 and Risk Level Low produce a allow decision."
  },
  "risk_assessment": {
    "risk_level": "Low",
    "main_risks": ["No active risk flags."],
    "confidence": "high"
  },
  "marketplace_verdict": {
    "can_be_listed": true,
    "can_be_rented": true,
    "reason": "Low-risk agent is marketplace-ready within the recommended wallet limit."
  },
  "suggested_next_actions": ["Allow broader permissions within the recommended wallet limit."]
}
```

## Enums

- `agent.status`: `active`, `paused`, `retired`
- `event.outcome`: `success`, `failed`, `error`
- `complaint.severity`: `low`, `medium`, `high`
- `complaint.status`: `open`, `confirmed`, `dismissed`
- `task.mode`: `metamask`, `autonomous`
- `task.status`: `planned`, `requires_signature`, `executed`, `completed`, `rejected`, `failed`
- `rental.status`: `pending`, `active`, `completed`, `disputed`, `cancelled`
