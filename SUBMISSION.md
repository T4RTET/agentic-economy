# DoraHacks Submission Draft

## Project Name

Agent Reputation Passport

## Tagline

A verifiable trust and risk layer for autonomous AI agents on Mantle.

## Links

- Live demo: https://agentic-economy-passport-demo-2026.onrender.com
- GitHub: https://github.com/T4RTET/agentic-economy
- API documentation: https://agentic-economy-passport-api-2026.onrender.com/docs
- Mantle connection: https://agentic-economy-passport-api-2026.onrender.com/mantle/status

## Short Description

Agent Reputation Passport helps users decide whether an autonomous AI agent can be trusted with wallets, DeFi actions, paid tasks, or marketplace work. It converts wallet ownership, transaction history, execution quality, complaints, and onchain evidence into an explainable Trust Score, Risk Level, and recommended wallet limit.

## Problem

AI agents can increasingly execute financial actions, but users have no standard way to evaluate their reliability before granting wallet access or hiring them. Existing profiles usually describe capabilities without providing verifiable execution history, risk signals, or safe permission recommendations.

## Solution

Each AI agent receives a public reputation passport containing:

- verified owner wallet;
- transparent Trust Score and score breakdown;
- Low, Medium, or High Risk Level;
- recommended wallet access limit;
- successful and failed action history;
- Mantle transaction evidence;
- complaints and marketplace disputes;
- marketplace eligibility based on risk.

## Mantle Integration

The backend connects directly to Mantle mainnet JSON-RPC and verifies network Chain ID `5000`. It can verify transaction receipts, attach Mantle Explorer links, and import indexed wallet transactions for verified owners. Imported evidence is deduplicated and immediately recalculates the agent passport.

Mantle is not used only as a payment rail. It acts as the verifiable evidence layer behind agent reputation.

## Innovation

The project combines concepts normally separated across identity, credit scoring, transaction monitoring, and labor marketplaces. Instead of assigning a static rating, it produces a continuously updated and explainable financial permission recommendation for autonomous agents.

## Business Potential

The passport can become a shared trust layer for:

- agent marketplaces;
- DeFi protocols granting delegated permissions;
- wallets offering agent automation;
- businesses hiring task agents;
- insurance and risk-monitoring providers.

Potential business models include verification fees, premium monitoring, marketplace commissions, and protocol risk APIs.

## Technical Highlights

- FastAPI modular backend and frontend-ready OpenAPI;
- MetaMask wallet ownership verification with expiring one-time nonces;
- live Mantle RPC status and transaction receipt verification;
- indexed transaction sync with duplicate protection;
- explainable reputation formula and wallet limit recommendation;
- marketplace rentals, completion, cancellation, and disputes;
- guarded Smart Account automation policy engine;
- rate limiting, readiness endpoint, Docker and Render deployment;
- 45 passing backend tests.

## Team

Add the three member names and links before submission:

1. Backend and reputation infrastructure: `[name / contact]`
2. Product and frontend experience: `[name / contact]`
3. Research and presentation: `[name / contact]`

## Future Roadmap

- automatic token and native-asset USD pricing;
- persistent PostgreSQL storage;
- onchain passport attestations;
- marketplace payment settlement;
- protocol-facing reputation API and SDK;
- continuous monitoring and alerting.
