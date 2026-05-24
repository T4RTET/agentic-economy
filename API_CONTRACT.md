# Agent Reputation Passport API Contract

## Product Phases

Phase 1 secure wallet flow:

```text
connect MetaMask -> sign nonce message -> verify wallet ownership -> show agent passport -> show intelligence report
```

Phase 1 demo-compatible flow:

```text
connect wallet directly -> find/create wallet-linked AI agent -> show agent passport
```

Phase 2 is the agent labor marketplace:

```text
browse marketplace -> rent/buy agent -> completed work updates the passport
```

Safe transaction flow:

```text
check passport intelligence -> prepare transaction request -> user signs in MetaMask -> record tx hash as passport action
```

Base URL for local development:

```text
http://127.0.0.1:8000
```

Swagger/OpenAPI:

```text
http://127.0.0.1:8000/docs
```

## Secure MetaMask Flow

1. Frontend connects MetaMask and reads the selected wallet address.
2. Frontend calls `POST /auth/nonce`.
3. Frontend asks MetaMask to sign the returned `message` with `personal_sign`.
4. Frontend sends `wallet_address`, `chain_id`, `message`, and `signature` to `POST /auth/verify`.
5. Backend verifies ownership and returns the agent passport.
6. Frontend can call `GET /agents/{agent_id}/intelligence`.

Create a signable nonce:

```http
POST /auth/nonce
Content-Type: application/json

{
  "wallet_address": "0x7a4A00000000000000000000000000000000A11a",
  "chain_id": 5000
}
```

Response:

```json
{
  "wallet_address": "0x7a4A00000000000000000000000000000000A11a",
  "chain_id": 5000,
  "nonce": "generated-random-nonce",
  "message": "Agent Reputation Passport wants you to verify wallet ownership...",
  "expires_at": "2026-05-24T14:00:00+00:00"
}
```

Verify a signed message:

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

Response:

```json
{
  "verified": true,
  "wallet_address": "0x7a4A00000000000000000000000000000000A11a",
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

## Phase 1 Demo Flow

`POST /wallet/connect` is retained for backward-compatible demos. It does not prove wallet ownership; production frontend flows should use `/auth/nonce` and `/auth/verify`.

1. Reset demo data if needed:

```http
POST /demo/reset
```

2. Connect a wallet directly and get the passport:

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

If the wallet already has an agent, backend returns the existing passport.
If not, backend creates a new wallet-linked agent passport.

3. Read a wallet passport directly:

```http
GET /wallet/{wallet_address}/passport?chain_id=5000
```

4. Add a completed action to improve/change the passport:

```http
POST /agents/{agent_id}/events
Content-Type: application/json

{
  "title": "Completed guarded swap",
  "category": "swap",
  "outcome": "success",
  "value_usd": 500,
  "tx_hash": "0xmantle-demo",
  "metadata": {
    "note": "Demo action from frontend"
  }
}
```

5. Add a complaint/risk signal:

```http
POST /agents/{agent_id}/complaints
Content-Type: application/json

{
  "reason": "Agent gave a delayed execution report.",
  "severity": "medium",
  "status": "open"
}
```

6. Re-read the passport and show updated analysis:

```http
GET /agents/{agent_id}/passport
```

## Phase 1 Supporting Endpoints

Load all seeded/demo agents:

```http
GET /agents
```

Open a passport by agent id:

```http
GET /agents/{agent_id}/passport
```

Read an intelligence report:

```http
GET /agents/{agent_id}/intelligence
```

Prepare a safe transaction request:

```http
POST /agents/{agent_id}/transactions/prepare
Content-Type: application/json

{
  "recipient_address": "0x000000000000000000000000000000000000dEaD",
  "value_usd": 25,
  "value_wei": "1000000000000000",
  "chain_id": 5000,
  "reason": "Pay for completed guarded swap."
}
```

Response:

```json
{
  "from": "0x7a4A00000000000000000000000000000000A11a",
  "to": "0x000000000000000000000000000000000000dEaD",
  "value": "1000000000000000",
  "chain_id": 5000,
  "reason": "Pay for completed guarded swap.",
  "requires_user_signature": true
}
```

The backend checks the passport and intelligence report first. `deny` wallet permissions reject preparation. `limit` wallet permissions require `value_usd` to stay within `wallet_permission.recommended_limit_usd`.

Record the user-signed transaction outcome:

```http
POST /agents/{agent_id}/transactions/record
Content-Type: application/json

{
  "tx_hash": "0xtransactionhash",
  "outcome": "success",
  "value_usd": 25,
  "metadata": {
    "recipient": "0x000000000000000000000000000000000000dEaD"
  }
}
```

The record endpoint creates an agent event, so the transaction appears in `actions_history` and affects future reputation calculations. It does not sign transactions and never accepts private keys or seed phrases.

Confirm or dismiss a complaint:

```http
PATCH /agents/{agent_id}/complaints/{complaint_id}
Content-Type: application/json

{
  "status": "confirmed"
}
```

## Phase 2 Marketplace Endpoints

Marketplace endpoints are available in backend, but they are not the primary site flow yet.

Load marketplace cards:

```http
GET /marketplace/listings
```

Rent an agent:

```http
POST /marketplace/listings/{listing_id}/rent
Content-Type: application/json

{
  "renter_wallet": "0xUserWallet",
  "task_title": "Find conservative Mantle yield route",
  "task_description": "Use only low-risk pools and return a report.",
  "duration_hours": 24
}
```

Complete a rental:

```http
POST /marketplace/rentals/{rental_id}/complete
```

Read a rental:

```http
GET /marketplace/rentals/{rental_id}
```

Dispute a rental:

```http
POST /marketplace/rentals/{rental_id}/dispute
Content-Type: application/json

{
  "reason": "The delivered route exceeded the agreed risk profile."
}
```

## Response Shapes

### `GET /agents`

Returns a list of cards for the catalog page.

```json
[
  {
    "agent": {
      "id": 1,
      "name": "YieldPilot Alpha",
      "description": "Autonomous DeFi assistant...",
      "agent_type": "defi-yield-agent",
      "owner_wallet": "0x...",
      "chain_id": 5000,
      "status": "active",
      "created_at": "2026-05-19 20:30:00"
    },
    "reputation": {
      "trust_score": 82,
      "risk_level": "Low",
      "recommended_wallet_limit_usd": 5460,
      "successful_volume_usd": 4580,
      "total_events": 3,
      "complaint_count": 0
    }
  }
]
```

### `GET /agents/{agent_id}/passport`

Returns everything needed for the passport page:

- `agent`
- `reputation`
- `marketplace`
- `analysis`
- `actions_history`
- `complaints`
- `audit_log`

### `GET /agents/{agent_id}/intelligence`

Returns wallet permission, risk assessment, marketplace verdict, and suggested next actions.

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
- `listing.pricing_model`: `buy`, `rent_hourly`, `rent_daily`, `per_task`
- `listing.availability`: `available`, `rented`, `paused`
- `rental.status`: `pending`, `active`, `completed`, `disputed`, `cancelled`
