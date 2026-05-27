# Agentic Economy Backend

FastAPI + SQLite backend for the Agent Reputation Passport MVP.

## What it does

- Stores AI agents, completed actions, complaints, and audit entries.
- Calculates Trust Score, Risk Level, and recommended wallet limit.
- Verifies MetaMask wallet ownership with signed messages.
- Keeps the legacy wallet connect endpoint available for demo flows.
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
- `POST /auth/nonce`
- `POST /auth/verify`
- `POST /wallet/connect`
- `GET /wallet/{wallet_address}/passport`
- `GET /agents`
- `POST /agents`
- `GET /agents/{agent_id}/passport`
- `GET /agents/{agent_id}/intelligence`
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

`POST /wallet/connect` remains available for backward-compatible demos. Frontends should use `POST /auth/nonce` followed by `POST /auth/verify` for secure MetaMask wallet ownership verification.

See `API_CONTRACT.md` for frontend integration details.

## Frontend

The minimal MetaMask test frontend lives in `frontend/`.

```powershell
cd frontend
npm install
npm run dev
```

Run the backend first:

```powershell
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:5173
```

MetaMask must be installed in the browser.

## Tests

```powershell
python -m pytest tests -p no:cacheprovider
```
