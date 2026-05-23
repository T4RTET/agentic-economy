# Agentic Economy Backend

FastAPI + SQLite backend for the Agent Reputation Passport MVP.

## What it does

- Stores AI agents, completed actions, complaints, and audit entries.
- Calculates Trust Score, Risk Level, and recommended wallet limit.
- Connects a wallet to an AI-agent passport for the phase 1 demo flow.
- Exposes a frontend-friendly API for a Vite React demo flow.
- Keeps marketplace/rental endpoints available as phase 2 backend groundwork.
- Ships with demo seed data for three agents: Low, Medium, and High risk.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

Open Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

## API

- `GET /health`
- `POST /wallet/connect`
- `GET /wallet/{wallet_address}/passport`
- `GET /agents`
- `POST /agents`
- `GET /agents/{agent_id}/passport`
- `POST /agents/{agent_id}/events`
- `POST /agents/{agent_id}/complaints`
- `PATCH /agents/{agent_id}/complaints/{complaint_id}`
- `GET /agents/{agent_id}/reputation`
- `GET /marketplace/listings`
- `POST /marketplace/agents/{agent_id}/listing`
- `POST /marketplace/listings/{listing_id}/rent`
- `GET /marketplace/rentals/{rental_id}`
- `POST /marketplace/rentals/{rental_id}/complete`
- `POST /marketplace/rentals/{rental_id}/dispute`
- `POST /demo/reset`

See `API_CONTRACT.md` for frontend integration details.

## Tests

```powershell
pytest
```
