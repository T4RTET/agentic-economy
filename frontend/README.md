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

## Minimal user action automation flow

The UI is intentionally simple and Russian-first for local testing:

1. Open `http://localhost:5173`.
2. Click `Connect MetaMask`.
3. Click `Verify Wallet` and sign the verification message in MetaMask.
4. In `Настройка автоматизации`, choose a preset:
   - `Safe`: small limits, one transaction per hour.
   - `Balanced`: larger local test limits.
   - `Custom`: edit limits, recipients, tokens, chains, actions, and emergency stop.
5. Click `Enable Automation / Включить автоматизацию`.
6. Confirm Smart Account / Delegation in MetaMask when a real Smart Account SDK is connected.
7. For local backend testing without the SDK, click `Confirm Test Delegation`.
8. Use `Тест автоматического действия` to evaluate and run an action through the policy engine.

## Smart Account Automation

Normal MetaMask EOA wallets cannot silently auto-confirm transactions. Every normal wallet transaction still requires user approval in MetaMask.

Automatic execution without sharing a seed phrase requires MetaMask Smart Accounts / Delegation / Advanced Permissions. The current `frontend/src/services/smartAccount.ts` file is a safe placeholder that:

- reports whether a Smart Account SDK is available,
- refuses to fake real delegation without the explicit `Confirm Test Delegation` button,
- returns a clear error until a real MetaMask Smart Accounts integration is connected.

The frontend never asks for a seed phrase or private key. Never paste a seed phrase into this app.

`Confirm Test Delegation` is only for local backend flow testing. It stores test delegation metadata and does not grant real wallet permissions.
