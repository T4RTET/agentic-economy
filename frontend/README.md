# Local MetaMask Test Frontend

This Vite React app is a local-only dashboard for testing MetaMask wallet verification, agent passports, intelligence, prepared transactions, and transaction recording. It never asks for a seed phrase or private key.

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

The Automation Settings panel configures:

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

The MetaMask Smart Account Delegation panel requests and stores delegation metadata. The backend does not sign anything. The user must grant scoped permissions in MetaMask Smart Accounts / Delegation.

The Automated Transaction Test panel evaluates the policy and then:

- returns `delegation_required` when Smart Account permission is missing
- sends a normal `eth_sendTransaction` request when user confirmation is required
- displays a smart-account execution payload when policy allows automatic execution

Automatic transactions without seed phrase require MetaMask Smart Accounts / Delegation. A normal MetaMask EOA cannot silently auto-confirm transactions.

## Environment

Create `.env` from `.env.example`:

```text
VITE_BACKEND_URL=http://127.0.0.1:8000
VITE_CHAIN_ID=31337
VITE_CHAIN_ID_HEX=0x7a69
VITE_AGENT_NAME=My MetaMask Test Agent
VITE_AGENT_TYPE=wallet-linked-agent
```

## Safety Notes

- No private key or seed phrase is needed.
- Never paste a seed phrase into this app.
- MetaMask signs the auth message locally through `personal_sign`.
- MetaMask signs and sends transactions only after user approval.
- The backend records tx hashes; it does not sign with the user's wallet.
- Smart Account / Delegation permissions are limited by user-configured policy and can be revoked in MetaMask.
