# Local MetaMask Test Frontend

This Vite React app is a local-only dashboard for testing MetaMask wallet verification, agent passports, intelligence, and the minimal Smart Account automation flow. The UI is intentionally in Russian for the current test flow. It never asks for a seed phrase or private key.

## Backend Start

From this `frontend/` directory:

```powershell
cd ..
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend docs:

```text
http://127.0.0.1:8000/docs
```

## Frontend Start

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open site:

```text
http://localhost:5173
```

MetaMask extension must be installed in the browser.

## Sepolia Smart Account config

Create `frontend/.env`.

Add these values:

```text
VITE_BACKEND_URL=http://127.0.0.1:8000
VITE_CHAIN_ID=11155111
VITE_CHAIN_NAME=Sepolia
VITE_RPC_URL=<Alchemy Sepolia RPC URL>
VITE_BUNDLER_RPC_URL=<Pimlico Sepolia Bundler RPC URL>
```

Do not commit `frontend/.env`. The real local file is ignored by Git; keep only `frontend/.env.example` in GitHub.

Restart the frontend after changing `.env`:

```powershell
npm run dev
```

Check the flow:

1. Connect MetaMask.
2. Verify Wallet.
3. Create Smart Wallet.
4. Enable Automation.
5. Run Automated Action.

## Local Hardhat Network

For real local transactions through MetaMask:

```powershell
npx hardhat node
```

Add a MetaMask network:

```text
RPC: http://127.0.0.1:8545
Chain ID: 31337
```

Import a Hardhat test account only for local testing. Then run:

```powershell
uvicorn app.main:app --reload
npm run dev
```

Open:

```text
http://localhost:5173
```

## Test Flow

1. Open `http://127.0.0.1:8000/docs` to confirm backend is running.
2. Open `http://localhost:5173`.
3. Click Check Backend.
4. Click Connect MetaMask.
5. Click Verify Wallet.
6. Confirm signature in MetaMask.
7. Check that agent id and owner_wallet appear.
8. Click Load Intelligence.
9. Prepare a transaction.
10. Send with MetaMask if wallet has gas.
11. Or use Record Fake Test tx_hash for backend-only testing.
12. Check that passport actions_history updates.

## Automation Flow

The fastest user flow is:

1. Open `http://localhost:5173`.
2. Click `Connect MetaMask`.
3. Click `Verify Wallet`.
4. Choose `Safe`, `Balanced`, or `Custom`.
5. Click `Create Smart Account / Enable Automation`.
6. Confirm MetaMask Smart Account / Delegation when the SDK is connected.
7. The agent can act only inside the saved limits.

The `Automation Setup` panel configures:

- automation enabled
- manual / semi_auto / full_auto mode
- maximum transaction value
- daily spend limit
- transactions per hour
- minimum remaining native balance
- confirmation threshold
- allowed chain IDs
- allowed tokens
- allowed recipients
- allowed actions
- emergency stop

The `Create Smart Account / Enable Automation` button saves the policy, requests delegation metadata from the backend, and tries to open MetaMask Smart Account / Delegation confirmation.

If the real MetaMask Smart Accounts SDK is not connected yet, the UI shows a safe placeholder message. Use `Confirm Test Delegation` only for local backend/UI testing:

```json
{
  "smart_account_address": "connected wallet",
  "delegation_id": "local-test-delegation-{agentId}",
  "delegation_scope": "delegationRequest.policy_scope"
}
```

The Automated Transaction Test panel evaluates the policy and then:

- returns `delegation_required` when Smart Account permission is missing
- sends a normal `eth_sendTransaction` request when user confirmation is required
- displays a smart-account execution payload when policy allows automatic execution

Automatic transactions without seed phrase require MetaMask Smart Accounts / Delegation. A normal MetaMask EOA cannot silently auto-confirm transactions.

## Create Smart Account / Enable Automation

Run the app:

```powershell
cd ..
uvicorn app.main:app --reload
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Then:

1. Click `Connect MetaMask`.
2. Click `Verify Wallet`.
3. Click `Create Smart Account / Enable Automation`.
4. If a real MetaMask Smart Accounts SDK is connected, confirm Smart Account / Delegation in MetaMask.
5. If the SDK is not connected, use `Confirm Test Delegation (test-only)` only for local backend-flow testing.

The button saves a Safe preset when automation is not configured yet, requests delegation metadata, then calls the frontend Smart Account service. The current service is a safe placeholder until MetaMask Smart Accounts / Advanced Permissions SDK code is wired in.

Warnings:

- Do not enter a seed phrase.
- Do not enter a private key.
- A normal MetaMask EOA does not support silent transaction confirmation.
- Real automation requires MetaMask Smart Account / Delegation.
- Test Delegation is not a real on-chain permission.

## Create Smart Wallet in MetaMask

Create `frontend/.env`:

```text
VITE_BACKEND_URL=http://127.0.0.1:8000
VITE_CHAIN_ID=11155111
VITE_CHAIN_NAME=Sepolia
VITE_RPC_URL=<your_rpc_url>
VITE_BUNDLER_RPC_URL=<your_bundler_rpc_url>
VITE_AGENT_NAME=My MetaMask Test Agent
VITE_AGENT_TYPE=wallet-linked-agent
```

Start the backend:

```powershell
uvicorn app.main:app --reload
```

Start the frontend:

```powershell
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
3. Create Smart Wallet.
4. Enable Automation.
5. Confirm Delegation.
6. Run Smart Wallet Action Test.

`VITE_RPC_URL` is used for network reads. `VITE_BUNDLER_RPC_URL` is required for UserOperation submission. If either value is empty, the Smart Wallet service returns a clear error and does not pretend that a real on-chain smart account was created.

`Confirm Test Delegation` is only for checking the frontend/backend flow locally. It is not a real Smart Account permission.

## Real MetaMask Smart Account Automation

Real automatic execution needs:

1. An RPC URL.
2. A Bundler RPC URL.
3. A supported testnet chain:
   - `11155111` Sepolia
   - `84532` Base Sepolia
   - `421614` Arbitrum Sepolia
   - `11155420` Optimism Sepolia
   - `80002` Polygon Amoy

Create `frontend/.env`:

```text
VITE_BACKEND_URL=http://127.0.0.1:8000
VITE_CHAIN_ID=11155111
VITE_CHAIN_NAME=Sepolia
VITE_RPC_URL=<your_rpc_url>
VITE_BUNDLER_RPC_URL=<your_bundler_rpc_url>
```

Run:

```powershell
uvicorn app.main:app --reload
cd frontend
npm install
npm run dev
```

Flow:

1. Connect MetaMask.
2. Verify Wallet.
3. Create Smart Wallet.
4. Enable Automation.
5. Confirm Delegation in MetaMask.
6. Evaluate Action.
7. Run Automated Action.
8. Submit UserOperation through Bundler.
9. Show `userOperationHash` / `txHash`.

The service never imports `privateKeyToAccount`, never accepts a private key, and never stores secrets. If the current SDK requires a signer adapter that is not available through MetaMask/Advanced Permissions, the UI shows a clear error and keeps `Confirm Test Delegation` as a local backend/UI test only.

## Full Smart Account Automation Setup

Real Smart Account automation needs RPC access, Bundler access, and a MetaMask wallet that supports Smart Accounts / Advanced Permissions.

1. Get an RPC URL.
2. Get a Bundler RPC URL.
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
- Send UserOperation.
- Get `userOperationHash` / `txHash`.
- Record result in passport.

Warnings:

- Do not enter a seed phrase.
- Do not enter a private key.
- A normal MetaMask EOA requires manual confirmation.
- Automation without per-transaction confirmation is only for Smart Account / Delegation / UserOperation.
- Test Delegation is not a real on-chain permission.

## Environment

Create `.env` from `.env.example`:

```text
VITE_BACKEND_URL=http://127.0.0.1:8000
VITE_CHAIN_ID=11155111
VITE_CHAIN_NAME=Sepolia
VITE_RPC_URL=<your_rpc_url>
VITE_BUNDLER_RPC_URL=<your_bundler_rpc_url>
```

## Safety Notes

- No private key or seed phrase is needed.
- Never paste a seed phrase into this app.
- Never paste a private key into this app.
- MetaMask signs the auth message locally through `personal_sign`.
- MetaMask signs and sends transactions only after user approval.
- A normal MetaMask EOA cannot silently auto-confirm transactions.
- Real automation requires MetaMask Smart Account / Delegation / Advanced Permissions.
- The backend records tx hashes; it does not sign with the user's wallet.
- Smart Account / Delegation permissions are limited by user-configured policy and can be revoked in MetaMask.
