# Demo Recording Checklist

Target length: **2-3 minutes**.

## Before Recording

- Open the [live demo](https://agentic-economy-passport-demo-2026.onrender.com) at least one minute early.
- Confirm the [API health endpoint](https://agentic-economy-passport-api-2026.onrender.com/health) returns `{"status":"ok"}`.
- Confirm the [Mantle status endpoint](https://agentic-economy-passport-api-2026.onrender.com/mantle/status) shows `connected: true` and `chain_id: 5000`.
- Prepare MetaMask on Mantle if demonstrating wallet verification.
- Close unrelated tabs and notifications.

## Recording Script

### 0:00-0:25 — Problem

"Autonomous AI agents are starting to manage wallets, execute DeFi actions, and complete paid work. Before giving an agent access to money, users need a verifiable way to understand its history and risk."

### 0:25-0:55 — Agent Directory

- Show Low, Medium, and High Risk agents.
- Point out Trust Score, handled volume, complaints, and recommended wallet limits.
- Explain that users can compare agents before trusting or hiring them.

### 0:55-1:35 — Agent Passport

- Open YieldPilot Alpha.
- Show the transparent Trust Score breakdown.
- Show transaction history and Mantle Explorer evidence.
- Point out the wallet limit recommendation and risk assessment.

### 1:35-2:00 — Reputation Changes

- Add a successful action or complaint.
- Show that the passport recalculates immediately.
- Explain that reputation is based on history, not a static review.

### 2:00-2:30 — Marketplace and Mantle

- Open Marketplace.
- Show that eligible agents can be rented.
- Show that High Risk agents are blocked.
- Open `/mantle/status` and mention direct Mantle mainnet RPC integration.

### 2:30-2:50 — Closing

"Agent Reputation Passport makes autonomous agents safer to use, hire, and fund. Mantle provides the verifiable evidence layer behind every trust decision."

## Final Submission Check

- Add all three team member names and contacts to DoraHacks.
- Add the live demo, GitHub, and demo video links.
- Use the project description from `SUBMISSION.md`.
- Verify links from an incognito browser.
- Do not make risky feature changes after recording.
