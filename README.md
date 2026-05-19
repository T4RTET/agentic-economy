# Agentic Economy Backend

FastAPI + SQLite backend for the Agent Reputation Passport MVP.

## What it does

- Stores AI agents, completed actions, complaints, and audit entries.
- Calculates Trust Score, Risk Level, and recommended wallet limit.
- Exposes a frontend-friendly API for a Vite React demo flow.
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
- `GET /agents`
- `POST /agents`
- `GET /agents/{agent_id}/passport`
- `POST /agents/{agent_id}/events`
- `POST /agents/{agent_id}/complaints`
- `PATCH /agents/{agent_id}/complaints/{complaint_id}`
- `GET /agents/{agent_id}/reputation`
- `POST /demo/reset`

See `API_CONTRACT.md` for frontend integration details.

## Tests

```powershell
pytest
```
