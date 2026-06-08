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

## Minimal User Action Automation Flow

The frontend is optimized for the shortest safe flow:

1. Open `http://localhost:5173`.
2. Click `Connect MetaMask`.
3. Click `Verify Wallet`.
4. Choose an automation preset: `Safe`, `Balanced`, or `Custom`.
5. Click `Create Smart Account / Enable Automation`.
6. Confirm MetaMask Smart Account / Delegation when the SDK is connected.
7. The agent can act only inside the saved policy limits.

Warnings:

- Never enter a seed phrase.
- Never enter a private key.
- A normal MetaMask EOA cannot silently auto-confirm transactions.
- Real automation requires MetaMask Smart Account / Delegation / Advanced Permissions.
- `Confirm Test Delegation` is only for local backend/UI testing without the real Smart Account SDK.

## Create Smart Account / Enable Automation

This button is available after the wallet is connected, verified, and the intelligence decision is not `deny`.

Flow:

1. The frontend loads `GET /agents/{agent_id}/automation-policy` if the policy is not already loaded.
2. If automation is not configured, it saves the Safe preset with `PUT /agents/{agent_id}/automation-policy`.
3. It requests delegation metadata with `POST /agents/{agent_id}/automation/delegation/request`.
4. It tries to create/connect a MetaMask Smart Account and request scoped delegation.
5. If the real Smart Accounts SDK is not connected, it shows a safe placeholder message.
6. `Confirm Test Delegation` can store local test metadata for backend-flow testing only.

Safe preset:

```json
{
  "automation_enabled": true,
  "mode": "semi_auto",
  "max_tx_value_usd": 1,
  "daily_limit_usd": 5,
  "max_transactions_per_hour": 1,
  "min_native_balance_wei": "100000000000000000",
  "require_confirmation_above_usd": 1,
  "allowed_chain_ids": ["current MetaMask chain id"],
  "allowed_tokens": ["NATIVE"],
  "allowed_recipients": ["0x000000000000000000000000000000000000dEaD"],
  "allowed_actions": ["native_transfer"],
  "emergency_stop": false
}
```

Test Delegation is not a real on-chain permission. It exists only to test the backend and UI flow without MetaMask Smart Accounts Kit.

## Create Smart Wallet in MetaMask

To test the real Smart Wallet path, create `frontend/.env`:

```text
VITE_BACKEND_URL=http://127.0.0.1:8000
VITE_CHAIN_ID=11155111
VITE_CHAIN_NAME=Sepolia
VITE_RPC_URL=<your_rpc_url>
VITE_BUNDLER_RPC_URL=<your_bundler_rpc_url>
VITE_AGENT_NAME=My MetaMask Test Agent
VITE_AGENT_TYPE=wallet-linked-agent
```

Run:

```powershell
uvicorn app.main:app --reload
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Flow:

1. Connect MetaMask.
2. Verify Wallet.
3. Click `Create Smart Wallet`.
4. Click `Enable Automation`.
5. Confirm Delegation when the MetaMask Smart Accounts SDK is connected.
6. Run `Smart Wallet Action Test`.

If `VITE_RPC_URL` or `VITE_BUNDLER_RPC_URL` is missing, the UI shows a clear error and does not pretend that a real on-chain Smart Wallet was created.

Warnings:

- Do not enter a seed phrase.
- Do not enter a private key.
- A normal MetaMask EOA cannot automatically confirm transactions.
- Real automation requires Smart Account / Delegation.
- `Confirm Test Delegation` is only for UI/backend testing and does not create a real on-chain permission.

## Real MetaMask Smart Account Automation

Real automatic execution needs a wallet-side Smart Account / Delegation setup plus RPC and bundler access.

1. Get an RPC URL for a supported testnet.
2. Get a Bundler RPC URL for the same chain.
3. Create `frontend/.env`:

```text
VITE_BACKEND_URL=http://127.0.0.1:8000
VITE_CHAIN_ID=11155111
VITE_CHAIN_NAME=Sepolia
VITE_RPC_URL=<your_rpc_url>
VITE_BUNDLER_RPC_URL=<your_bundler_rpc_url>
VITE_AGENT_NAME=My MetaMask Test Agent
VITE_AGENT_TYPE=wallet-linked-agent
```

Supported Smart Account chain IDs in the frontend service:

- `11155111` Sepolia
- `84532` Base Sepolia
- `421614` Arbitrum Sepolia
- `11155420` Optimism Sepolia
- `80002` Polygon Amoy

Run:

```powershell
uvicorn app.main:app --reload
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, then:

1. Connect MetaMask.
2. Verify Wallet.
3. Create Smart Wallet.
4. Enable Automation.
5. Confirm Delegation in MetaMask.
6. Evaluate Action.
7. Run Automated Action.
8. Submit UserOperation through the Bundler.
9. Show `userOperationHash` / `txHash`.

If the current MetaMask Smart Accounts SDK requires a signer adapter that is not exposed by `window.ethereum`, the frontend stops with a clear error instead of asking for a private key. Do not enter a seed phrase or private key. Normal MetaMask EOA transactions still require manual confirmation. Automatic execution without manual confirmation is only for Smart Account / Delegation / Advanced Permissions. Test Delegation is not a real on-chain permission.

## Full Smart Account Automation Setup

Real Smart Account automation needs RPC access, Bundler access, and a MetaMask wallet that supports Smart Accounts / Advanced Permissions.

1. Get an RPC URL for the target testnet.
2. Get a Bundler RPC URL for the same chain.
3. Create `frontend/.env`.
4. Add:

```text
VITE_BACKEND_URL=http://127.0.0.1:8000
VITE_CHAIN_ID=11155111
VITE_CHAIN_NAME=Sepolia
VITE_RPC_URL=<your_rpc_url>
VITE_BUNDLER_RPC_URL=<your_bundler_rpc_url>
```

5. Do not commit `frontend/.env`.
6. Start the backend:

```powershell
uvicorn app.main:app --reload
```

7. Start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

8. Flow:

- Connect MetaMask.
- Verify Wallet.
- Create Smart Wallet.
- Enable Automation.
- Confirm Delegation in MetaMask.
- Evaluate Action.
- Run Automated Action.
- Send UserOperation through the Bundler.
- Get `userOperationHash` / `txHash`.
- Record result in passport.

Warnings:

- Do not enter a seed phrase.
- Do not enter a private key.
- A normal MetaMask EOA requires manual confirmation.
- Automation without per-transaction confirmation is only for Smart Account / Delegation / UserOperation.
- Test Delegation is not a real on-chain permission.

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
