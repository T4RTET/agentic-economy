# Agent Reputation Passport API Contract

## Product Phases

Phase 1 is the current site flow:

```text
connect wallet -> find/create wallet-linked AI agent -> show agent passport
```

Phase 2 is the agent labor marketplace:

```text
browse marketplace -> rent/buy agent -> completed work updates the passport
```

Base URL for local development:

```text
http://127.0.0.1:8000
```

Swagger/OpenAPI:

```text
http://127.0.0.1:8000/docs
```

## Phase 1 Demo Flow

1. Reset demo data if needed:

```http
POST /demo/reset
```

2. Connect a wallet and get the passport:

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

`analysis` is a frontend-ready explanation block:

```json
{
  "summary": "Trust Score 82/100, Risk Level Low.",
  "strengths": ["3 successful action(s) recorded"],
  "risk_flags": ["No active risk flags"],
  "recommendation": "Suitable for broader wallet permissions within the recommended limit."
}
```

### `GET /marketplace/listings`

Returns agent marketplace cards with price, availability, capabilities, Trust Score, Risk Level, and marketplace stats.

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
    },
    "marketplace": {
      "listing": {
        "id": 1,
        "agent_id": 1,
        "pricing_model": "rent_daily",
        "price_usd": 240,
        "price_token": "USD",
        "availability": "available",
        "capabilities": ["defi-routing", "risk-checks"],
        "terms": "Best for conservative wallet automation with capped permissions.",
        "created_at": "2026-05-19 20:30:00",
        "updated_at": "2026-05-19 20:30:00"
      },
      "stats": {
        "rentals_count": 0,
        "completed_rentals": 0,
        "disputed_rentals": 0,
        "completion_rate": 0
      }
    }
  }
]
```

## Enums

- `agent.status`: `active`, `paused`, `retired`
- `event.outcome`: `success`, `failed`, `error`
- `complaint.severity`: `low`, `medium`, `high`
- `complaint.status`: `open`, `confirmed`, `dismissed`
- `listing.pricing_model`: `buy`, `rent_hourly`, `rent_daily`, `per_task`
- `listing.availability`: `available`, `rented`, `paused`
- `rental.status`: `pending`, `active`, `completed`, `disputed`, `cancelled`
