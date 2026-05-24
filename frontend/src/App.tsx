import { useMemo, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

type EthereumProvider = {
  request(args: { method: string; params?: unknown[] | object }): Promise<unknown>;
};

declare global {
  interface Window {
    ethereum?: EthereumProvider;
  }
}

type AgentPassport = {
  agent: {
    id: number;
    name: string;
    owner_wallet: string;
    chain_id: number;
  };
  reputation: {
    trust_score: number;
    risk_level: "Low" | "Medium" | "High";
    recommended_wallet_limit_usd: number;
  };
};

type WalletNonceResponse = {
  message: string;
};

type WalletVerifyResponse = {
  verified: boolean;
  passport: AgentPassport;
};

type IntelligenceReport = {
  summary: string;
  wallet_permission: {
    decision: "allow" | "limit" | "deny";
    recommended_limit_usd: number;
    reason: string;
  };
  risk_assessment: {
    risk_level: "Low" | "Medium" | "High";
    main_risks: string[];
    confidence: "low" | "medium" | "high";
  };
  marketplace_verdict: {
    can_be_listed: boolean;
    can_be_rented: boolean;
    reason: string;
  };
  suggested_next_actions: string[];
};

async function postJson<TResponse>(path: string, body: object): Promise<TResponse> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail ?? "Request failed");
  }
  return data as TResponse;
}

async function getJson<TResponse>(path: string): Promise<TResponse> {
  const response = await fetch(`${API_BASE}${path}`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail ?? "Request failed");
  }
  return data as TResponse;
}

function shortAddress(address: string): string {
  if (address.length <= 12) return address;
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export default function App() {
  const [walletAddress, setWalletAddress] = useState("");
  const [chainId, setChainId] = useState(5000);
  const [passport, setPassport] = useState<AgentPassport | null>(null);
  const [intelligence, setIntelligence] = useState<IntelligenceReport | null>(null);
  const [status, setStatus] = useState("Idle");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const canVerify = useMemo(() => Boolean(walletAddress && !busy), [walletAddress, busy]);

  async function connectMetaMask() {
    setError("");
    if (!window.ethereum) {
      setError("MetaMask is not available in this browser.");
      return;
    }

    setBusy(true);
    setStatus("Connecting");
    try {
      const accounts = (await window.ethereum.request({ method: "eth_requestAccounts" })) as string[];
      const chainHex = (await window.ethereum.request({ method: "eth_chainId" })) as string;
      setWalletAddress(accounts[0] ?? "");
      setChainId(Number.parseInt(chainHex, 16));
      setStatus("Connected");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Wallet connection failed.");
      setStatus("Idle");
    } finally {
      setBusy(false);
    }
  }

  async function verifyWallet() {
    if (!window.ethereum || !walletAddress) return;

    setBusy(true);
    setError("");
    setStatus("Requesting nonce");
    try {
      const nonce = await postJson<WalletNonceResponse>("/auth/nonce", {
        wallet_address: walletAddress,
        chain_id: chainId,
      });

      setStatus("Awaiting signature");
      const signature = (await window.ethereum.request({
        method: "personal_sign",
        params: [nonce.message, walletAddress],
      })) as string;

      setStatus("Verifying");
      const verified = await postJson<WalletVerifyResponse>("/auth/verify", {
        wallet_address: walletAddress,
        chain_id: chainId,
        message: nonce.message,
        signature,
        agent_name: `Agent ${shortAddress(walletAddress)}`,
        agent_type: "wallet-linked-agent",
      });

      setPassport(verified.passport);
      const report = await getJson<IntelligenceReport>(`/agents/${verified.passport.agent.id}/intelligence`);
      setIntelligence(report);
      setStatus("Verified");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Wallet verification failed.");
      setStatus("Connected");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Agentic Economy</p>
          <h1>Agent Reputation Passport</h1>
        </div>
        <div className="actions">
          <button type="button" onClick={connectMetaMask} disabled={busy}>
            Connect MetaMask
          </button>
          <button type="button" className="primary" onClick={verifyWallet} disabled={!canVerify}>
            Verify Wallet
          </button>
        </div>
      </header>

      <section className="status-row" aria-live="polite">
        <span className="status-pill">{status}</span>
        {walletAddress && <span className="wallet-pill">{shortAddress(walletAddress)}</span>}
        {error && <span className="error-text">{error}</span>}
      </section>

      <section className="workspace">
        <article className="panel">
          <h2>Wallet</h2>
          <dl className="facts">
            <div>
              <dt>Address</dt>
              <dd>{walletAddress || "Not connected"}</dd>
            </div>
            <div>
              <dt>Chain ID</dt>
              <dd>{chainId}</dd>
            </div>
            <div>
              <dt>Backend</dt>
              <dd>{API_BASE}</dd>
            </div>
          </dl>
        </article>

        <article className="panel">
          <h2>Passport</h2>
          {passport ? (
            <dl className="facts">
              <div>
                <dt>Agent</dt>
                <dd>{passport.agent.name}</dd>
              </div>
              <div>
                <dt>Trust Score</dt>
                <dd>{passport.reputation.trust_score}/100</dd>
              </div>
              <div>
                <dt>Risk</dt>
                <dd>{passport.reputation.risk_level}</dd>
              </div>
            </dl>
          ) : (
            <p className="empty-state">No verified passport yet.</p>
          )}
        </article>

        <article className="panel decision-panel">
          <h2>Decision</h2>
          {intelligence ? (
            <>
              <div className={`decision ${intelligence.wallet_permission.decision}`}>
                {intelligence.wallet_permission.decision}
              </div>
              <p>{intelligence.summary}</p>
              <p>{intelligence.wallet_permission.reason}</p>
              <dl className="facts compact">
                <div>
                  <dt>Limit</dt>
                  <dd>{formatUsd(intelligence.wallet_permission.recommended_limit_usd)}</dd>
                </div>
                <div>
                  <dt>Confidence</dt>
                  <dd>{intelligence.risk_assessment.confidence}</dd>
                </div>
              </dl>
            </>
          ) : (
            <p className="empty-state">No decision yet.</p>
          )}
        </article>

        <article className="panel">
          <h2>Risk Notes</h2>
          {intelligence ? (
            <>
              <ul className="plain-list">
                {intelligence.risk_assessment.main_risks.map((risk) => (
                  <li key={risk}>{risk}</li>
                ))}
              </ul>
              <p>{intelligence.marketplace_verdict.reason}</p>
            </>
          ) : (
            <p className="empty-state">No risks loaded.</p>
          )}
        </article>

        <article className="panel wide">
          <h2>Next Actions</h2>
          {intelligence ? (
            <ul className="plain-list columns">
              {intelligence.suggested_next_actions.map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          ) : (
            <p className="empty-state">Verify a wallet to load actions.</p>
          )}
        </article>
      </section>
    </main>
  );
}
