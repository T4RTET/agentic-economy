# Agent Reputation Passport Frontend

Minimal Vite React frontend for testing MetaMask wallet ownership verification and Smart Account automation policy flows.

## Setup

```powershell
npm install
npm run dev
```

Backend must be running:

```powershell
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:5173
```

MetaMask extension must be installed in the browser.

## Smart Account Automation

Normal MetaMask EOA wallets cannot silently auto-confirm transactions. Every normal wallet transaction still requires user approval in MetaMask.

Automatic execution without sharing a seed phrase requires MetaMask Smart Accounts / Delegation / Advanced Permissions. Use the UI to:

1. Verify the wallet with `POST /auth/nonce` and `POST /auth/verify`.
2. Load and save automation limits.
3. Request delegation metadata from the backend.
4. Grant scoped permission in MetaMask Smart Accounts / Delegation.
5. Confirm delegation metadata back to the backend.
6. Evaluate or prepare an automated transaction payload.

The frontend never asks for a seed phrase or private key. Never paste a seed phrase into this app.
