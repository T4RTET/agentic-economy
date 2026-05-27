# Agentic Economy Backend

FastAPI + SQLite backend and Vite React frontend for a safe on-chain AI agent MVP.

## What it does

- Stores AI agents, completed actions, complaints, tasks, and audit entries.
- Calculates Trust Score, Risk Level, and recommended wallet limits.
- Verifies MetaMask wallet ownership with signed messages.
- Normalizes and validates EVM wallet addresses and transaction hashes.
- Prepares MetaMask-compatible transaction requests without signing them.
- Records transaction hashes into the passport action history.
- Stores configurable automation policies for MetaMask Smart Accounts / Delegation.
- Provides an optional read-only RPC client for balances and transaction status.
- Provides a disabled-by-default autonomous executor wallet for testnet-only guarded execution.

## Safety Model

- Never ask users for seed phrases or MetaMask private keys.
- Never store user private keys in SQLite.
- Never accept private keys through API endpoints.
- User MetaMask wallets only sign auth messages and user-approved transactions.
- Normal MetaMask EOA wallets cannot silently auto-confirm transactions.
- Automatic user-wallet execution requires MetaMask Smart Accounts / Delegation with explicit user-granted limits.
- Autonomous execution uses only `AGENT_EXECUTOR_PRIVATE_KEY` from environment variables.
- Autonomous execution is disabled by default and mainnet is blocked unless explicitly enabled.
- Never paste a seed phrase into this app.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Local Frontend Test UI

The local MetaMask test UI lives in `frontend/`.

- Backend runs at `http://127.0.0.1:8000`.
- Swagger UI is at `http://127.0.0.1:8000/docs`.
- Frontend runs at `http://localhost:5173`.
- MetaMask is required for real wallet signing.
- No private key or seed phrase is needed.

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

## Core Modes

1. Demo wallet binding: `POST /wallet/connect`
   Demo-only compatibility endpoint. It does not prove wallet ownership.

2. Secure MetaMask binding: `POST /auth/nonce` then `POST /auth/verify`
   Proves wallet ownership and links a normalized checksum wallet to an agent passport.

3. User-approved transaction mode:
   `POST /agents/{agent_id}/transactions/prepare` returns a MetaMask transaction request.
   The frontend sends it through MetaMask, then calls `POST /agents/{agent_id}/transactions/record`.

4. Autonomous testnet executor mode:
   `POST /agents/{agent_id}/transactions/execute-autonomous` uses a separate executor wallet.
   It is disabled by default, guarded by policy checks, and must never use a user MetaMask private key.

5. MetaMask Smart Account automation:
   `GET/PUT /agents/{agent_id}/automation-policy` configures limits, allowlists, frequency, minimum balance, and emergency stop.
   `POST /agents/{agent_id}/automation/delegation/request` returns delegation metadata for MetaMask Smart Accounts.
   `POST /agents/{agent_id}/automation/delegation/confirm` stores the granted smart-account delegation metadata.
   `POST /agents/{agent_id}/transactions/execute-automated` evaluates the policy and returns either a normal MetaMask transaction request, a delegation-required response, or a smart-account execution payload.

## Wallet Automation

Normal MetaMask wallets require user approval for every transaction. The backend will not try to bypass that, and it never asks for a seed phrase or private key.

Smart Account / Delegation mode allows limited automatic execution after the user grants scoped permissions. The policy controls:

- maximum transaction value
- daily spend limit
- transactions per hour
- minimum remaining native balance
- allowed chain IDs
- allowed recipients
- allowed tokens, including `NATIVE`
- allowed action types
- emergency stop

Users control these limits and can revoke delegation in MetaMask.

## Bind a MetaMask Address for Demo Testing

The helper script `scripts/bind_metamask_wallet.py` binds a public MetaMask wallet address to an AI agent through the demo `/wallet/connect` endpoint.

Example `.env` values:

```text
METAMASK_WALLET_ADDRESS=0x6482400504F39C93469c8366b96e4A06a10b1DB9
CHAIN_ID=5000
AGENT_NAME=My MetaMask Agent
AGENT_TYPE=wallet-linked-agent
BACKEND_URL=http://127.0.0.1:8000
```

Run:

```powershell
uvicorn app.main:app --reload
python scripts/bind_metamask_wallet.py
```

Expected result:

```text
passport.agent.owner_wallet == METAMASK_WALLET_ADDRESS
```

This script uses `/wallet/connect`, so it binds the public address for demo/testing. For secure proof of wallet ownership, use `/auth/nonce` + `/auth/verify` with a MetaMask signature.

## API

- `GET /health`
- `POST /auth/nonce`
- `POST /auth/verify`
- `POST /wallet/connect`
- `GET /wallet/{wallet_address}/passport`
- `GET /wallet/{wallet_address}/balance`
- `GET /agents`
- `POST /agents`
- `GET /agents/{agent_id}/passport`
- `GET /agents/{agent_id}/intelligence`
- `POST /agents/{agent_id}/transactions/prepare`
- `POST /agents/{agent_id}/transactions/record`
- `POST /agents/{agent_id}/transactions/execute-autonomous`
- `GET /agents/{agent_id}/automation-policy`
- `PUT /agents/{agent_id}/automation-policy`
- `POST /agents/{agent_id}/automation-policy/evaluate`
- `POST /agents/{agent_id}/automation/delegation/request`
- `POST /agents/{agent_id}/automation/delegation/confirm`
- `POST /agents/{agent_id}/transactions/execute-automated`
- `GET /transactions/{tx_hash}/status`
- `GET /agent-executor/status`
- `POST /agents/{agent_id}/tasks/plan`
- `POST /agents/{agent_id}/tasks/{task_id}/execute`
- marketplace, rental, complaint, event, and demo reset endpoints from the original MVP

See `API_CONTRACT.md` for frontend integration details.

## Frontend

The MetaMask frontend lives in `frontend/`.

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

## Autonomous Executor Env

Copy `.env.example` and set only testnet values at first.

```text
RPC_URL=
CHAIN_ID=5000
AGENT_EXECUTOR_ENABLED=false
AGENT_EXECUTOR_PRIVATE_KEY=
AGENT_EXECUTOR_ALLOW_MAINNET=false
AGENT_MAX_TX_VALUE_WEI=1000000000000000
AGENT_DAILY_LIMIT_USD=10
AGENT_ALLOWED_RECIPIENTS=
AGENT_ALLOWED_CHAIN_IDS=5000
```

## Tests

```powershell
python -m pytest tests -p no:cacheprovider
```

Manual scripts:

```powershell
python scripts/manual_verified_wallet_transaction_test.py
python scripts/manual_autonomous_executor_test.py
```
