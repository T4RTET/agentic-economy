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

3. Open one passport:

```http
GET /agents/{agent_id}/passport
```

4. Add a completed action:

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

5. Add a complaint:

```http
POST /agents/{agent_id}/complaints
Content-Type: application/json

{
  "reason": "Agent gave a delayed execution report.",
  "severity": "medium",
  "status": "open"
}
```

6. Confirm or dismiss a complaint:

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
- `actions_history`
- `complaints`
- `audit_log`

## Enums

- `agent.status`: `active`, `paused`, `retired`
- `event.outcome`: `success`, `failed`, `error`
- `complaint.severity`: `low`, `medium`, `high`
- `complaint.status`: `open`, `confirmed`, `dismissed`
