# Agent Reputation Passport API Contract

Base URL for local development:

```text
http://127.0.0.1:8000
```

Swagger/OpenAPI:

```text
http://127.0.0.1:8000/docs
```

## Demo Flow

1. Reset demo data:

```http
POST /demo/reset
```

2. Load agent cards:

```http
GET /agents
```

3. Load marketplace cards:

```http
GET /marketplace/listings
```

4. Open one passport:

```http
GET /agents/{agent_id}/passport
```

5. Add a completed action:

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

6. Rent an agent:

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

7. Complete a rental:

```http
POST /marketplace/rentals/{rental_id}/complete
```

8. Read a rental:

```http
GET /marketplace/rentals/{rental_id}
```

9. Dispute a rental:

```http
POST /marketplace/rentals/{rental_id}/dispute
Content-Type: application/json

{
  "reason": "The delivered route exceeded the agreed risk profile."
}
```

10. Add a complaint directly:

```http
POST /agents/{agent_id}/complaints
Content-Type: application/json

{
  "reason": "Agent gave a delayed execution report.",
  "severity": "medium",
  "status": "open"
}
```

11. Confirm or dismiss a complaint:

```http
PATCH /agents/{agent_id}/complaints/{complaint_id}
Content-Type: application/json

{
  "status": "confirmed"
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
- `actions_history`
- `complaints`
- `audit_log`

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
