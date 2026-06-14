# Agentic Economy Backend

FastAPI + SQLite backend for the Agent Reputation Passport MVP.

## What it does

- Stores AI agents, completed actions, complaints, and audit entries.
- Calculates Trust Score, Risk Level, score breakdown, and recommended wallet limit from wallet verification, transaction history, transaction quality, activity frequency, on-chain evidence, task diversity, value experience, and complaints.
- Verifies MetaMask wallet ownership with signed messages.
- Keeps the legacy wallet connect endpoint available for demo flows.
- Adds configurable MetaMask Smart Account / Delegation automation policies for safe automatic transaction preparation.
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
- `GET /ready`
- `GET /mantle/status`
- `POST /mantle/transactions/verify`
- `POST /mantle/agents/{agent_id}/sync`
- `GET /project/hackathon-alignment`
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
- `GET /agents/{agent_id}/automation-policy`
- `PUT /agents/{agent_id}/automation-policy`
- `POST /agents/{agent_id}/automation-policy/evaluate`
- `POST /agents/{agent_id}/automation/delegation/request`
- `POST /agents/{agent_id}/automation/delegation/confirm`
- `POST /agents/{agent_id}/transactions/execute-automated`
- `GET /marketplace/listings`
- `POST /marketplace/agents/{agent_id}/listing`
- `POST /marketplace/listings/{listing_id}/rent`
- `GET /marketplace/rentals/{rental_id}`
- `GET /marketplace/rentals?renter_wallet=0x...`
- `POST /marketplace/rentals/{rental_id}/complete`
- `POST /marketplace/rentals/{rental_id}/dispute`
- `POST /marketplace/rentals/{rental_id}/cancel`
- `POST /demo/reset`

`POST /wallet/connect` remains available for backward-compatible demos. Frontends should use `POST /auth/nonce` followed by `POST /auth/verify` for secure MetaMask wallet ownership verification.

## Smart Account Automation

Normal MetaMask EOA wallets cannot silently auto-confirm transactions. Every normal wallet transaction still needs user approval in MetaMask.

Automatic execution without sharing a seed phrase requires MetaMask Smart Accounts / Delegation / Advanced Permissions. Automation policies support:

- max transaction value
- daily spend limit
- transactions per hour
- minimum remaining native balance
- allowed chain IDs
- allowed tokens
- allowed recipients
- allowed action types
- emergency stop
- delegation metadata and status

The backend does not ask for seed phrases, does not accept private keys, and does not sign user-wallet transactions. It evaluates policy and returns either a normal MetaMask transaction request for user confirmation or a Smart Account execution payload for the frontend to submit through MetaMask Smart Accounts tooling.

Never paste a seed phrase into this app.

## Presentation Demo Flow

The frontend is a complete Agent Reputation Passport demo backed by the live API:

1. Compare Low, Medium, and High risk agents in the directory.
2. Open a passport and explain the Trust Score, Risk Level, wallet limit, and score factors.
3. Show verifiable action history, onchain evidence, and complaints.
4. Add a successful or failed action and show the score update immediately.
5. Submit a complaint and show the new public risk signal.
6. Connect MetaMask to find a wallet-linked passport or issue a new one.

## Optional Smart Account Automation Flow

The frontend now has a simplified Russian-language setup path for automation:

1. Open `http://localhost:5173`.
2. Click `Connect MetaMask`.
3. Click `Verify Wallet` and sign the ownership message in MetaMask.
4. Choose the `Safe`, `Balanced`, or `Custom` automation preset.
5. Click `Enable Automation / Включить автоматизацию`.
6. Confirm Smart Account / Delegation in MetaMask when a real SDK is connected.
7. For local backend/UI testing, click `Confirm Test Delegation` to store test delegation metadata.
8. The agent can then evaluate automated actions and only act inside policy limits.

Safety notes:

- Do not enter a seed phrase.
- Do not enter a private key.
- A normal MetaMask EOA cannot silently auto-confirm transactions.
- Real automation requires MetaMask Smart Account / Delegation.
- Test Delegation is only for local backend flow testing.

See `API_CONTRACT.md` for frontend integration details.

## Frontend

The complete passport demo frontend lives in `frontend/`.

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

## Mantle Sync

Transaction verification uses the public Mantle JSON-RPC endpoint directly. Full wallet-history discovery requires an indexed API because standard Ethereum JSON-RPC cannot search every transaction by wallet address.

Set `ETHERSCAN_API_KEY` to enable `POST /mantle/agents/{agent_id}/sync`. The endpoint:

- requires prior wallet ownership verification through `/auth/nonce` and `/auth/verify`;
- imports indexed Mantle transactions;
- skips already-known transaction hashes;
- stores explorer-ready evidence;
- recalculates the passport immediately.

Copy `.env.example` for all runtime settings.

## Production

`render.yaml` and `Dockerfile` provide a deployable backend configuration. The Render blueprint stores SQLite on a persistent disk for the hackathon MVP. A PostgreSQL migration should be done as a dedicated repository-layer replacement after the MVP; the current repository intentionally keeps SQLite-specific queries rather than claiming partial PostgreSQL compatibility.

## Tests

```powershell
python -m pytest tests -p no:cacheprovider
```
