import { useMemo, useState } from "react";
import type { ReactNode } from "react";

const API_BASE = "http://127.0.0.1:8000";
const DEFAULT_CHAIN_ID = 5000;
const DEFAULT_RECIPIENT = "0x000000000000000000000000000000000000dEaD";

type EthereumProvider = {
  request(args: { method: string; params?: unknown[] | object }): Promise<unknown>;
};

declare global {
  interface Window {
    ethereum?: EthereumProvider;
    ethereumSmartAccounts?: unknown;
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

type WalletNonceResponse = { message: string };

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

type AutomationMode = "manual" | "semi_auto" | "full_auto";

type AutomationPolicy = {
  automation_enabled: boolean;
  mode: AutomationMode;
  max_tx_value_usd: number;
  daily_limit_usd: number;
  max_transactions_per_hour: number;
  min_native_balance_wei: string;
  require_confirmation_above_usd: number;
  allowed_chain_ids: number[];
  allowed_tokens: string[];
  allowed_recipients: string[];
  allowed_actions: string[];
  emergency_stop: boolean;
  smart_account_address: string | null;
  delegation_id: string | null;
  delegation_status: "none" | "requested" | "active" | "revoked" | "expired";
  delegation_scope?: Record<string, unknown>;
};

type AutomationEvaluation = {
  allowed: boolean;
  requires_user_confirmation: boolean;
  can_auto_execute: boolean;
  delegation_required: boolean;
  reason: string;
  violations: string[];
};

type DelegationRequest = {
  delegation_status: string;
  message: string;
  policy_scope: Record<string, unknown>;
  request: Record<string, unknown>;
};

type AutomatedTransactionResponse = {
  executed: boolean;
  requires_user_confirmation: boolean;
  delegation_required: boolean;
  status: string;
  reason: string;
  attempt_id: number;
  transaction_request: Record<string, string> | null;
  smart_account_execution_payload: Record<string, unknown> | null;
  tx_hash: string | null;
  evaluation: AutomationEvaluation;
};

const defaultPolicyForm = {
  automation_enabled: false,
  mode: "manual" as AutomationMode,
  max_tx_value_usd: "1",
  daily_limit_usd: "10",
  max_transactions_per_hour: "3",
  min_native_balance_wei: "0",
  require_confirmation_above_usd: "0.5",
  allowed_chain_ids: String(DEFAULT_CHAIN_ID),
  allowed_tokens: "NATIVE",
  allowed_recipients: DEFAULT_RECIPIENT,
  allowed_actions: "native_transfer",
  emergency_stop: false,
};

const defaultActionForm = {
  action_type: "native_transfer",
  recipient: DEFAULT_RECIPIENT,
  token: "",
  value_wei: "1",
  value_usd: "0.01",
  chain_id: String(DEFAULT_CHAIN_ID),
  reason: "Smart Account automation test",
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

async function putJson<TResponse>(path: string, body: object): Promise<TResponse> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
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
    maximumFractionDigits: 2,
  }).format(value);
}

export default function App() {
  const [walletAddress, setWalletAddress] = useState("");
  const [chainId, setChainId] = useState(DEFAULT_CHAIN_ID);
  const [passport, setPassport] = useState<AgentPassport | null>(null);
  const [intelligence, setIntelligence] = useState<IntelligenceReport | null>(null);
  const [status, setStatus] = useState("Idle");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [policy, setPolicy] = useState<AutomationPolicy | null>(null);
  const [policyForm, setPolicyForm] = useState(defaultPolicyForm);
  const [actionForm, setActionForm] = useState(defaultActionForm);
  const [evaluation, setEvaluation] = useState<AutomationEvaluation | null>(null);
  const [delegationRequest, setDelegationRequest] = useState<DelegationRequest | null>(null);
  const [smartAccountAddress, setSmartAccountAddress] = useState("");
  const [delegationId, setDelegationId] = useState("local-smart-account-delegation");
  const [automatedResult, setAutomatedResult] = useState<AutomatedTransactionResponse | null>(null);
  const [txHash, setTxHash] = useState("");

  const agentId = passport?.agent.id ?? null;
  const canVerify = useMemo(() => Boolean(walletAddress && !busy), [walletAddress, busy]);

  async function run(label: string, action: () => Promise<void>) {
    setBusy(true);
    setError("");
    setStatus(label);
    try {
      await action();
    } catch (err) {
      setError(readableError(err));
    } finally {
      setBusy(false);
    }
  }

  async function connectMetaMask() {
    await run("Connecting", async () => {
      if (!window.ethereum) {
        throw new Error("MetaMask is not available in this browser.");
      }
      const accounts = (await window.ethereum.request({ method: "eth_requestAccounts" })) as string[];
      const chainHex = (await window.ethereum.request({ method: "eth_chainId" })) as string;
      setWalletAddress(accounts[0] ?? "");
      setSmartAccountAddress(accounts[0] ?? "");
      setChainId(Number.parseInt(chainHex, 16));
      setStatus("Connected");
    });
  }

  async function verifyWallet() {
    if (!window.ethereum || !walletAddress) return;
    await run("Verifying", async () => {
      const nonce = await postJson<WalletNonceResponse>("/auth/nonce", {
        wallet_address: walletAddress,
        chain_id: chainId,
      });
      const signature = (await window.ethereum!.request({
        method: "personal_sign",
        params: [nonce.message, walletAddress],
      })) as string;
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
    });
  }

  async function loadPolicy() {
    await run("Loading policy", async () => {
      const id = requireAgentId();
      const nextPolicy = await getJson<AutomationPolicy>(`/agents/${id}/automation-policy`);
      setPolicy(nextPolicy);
      setPolicyForm(policyToForm(nextPolicy));
      setSmartAccountAddress(nextPolicy.smart_account_address ?? walletAddress);
      setDelegationId(nextPolicy.delegation_id ?? "local-smart-account-delegation");
      setStatus("Policy loaded");
    });
  }

  async function savePolicy() {
    await run("Saving policy", async () => {
      const id = requireAgentId();
      const nextPolicy = await putJson<AutomationPolicy>(`/agents/${id}/automation-policy`, buildPolicyPayload(policyForm));
      setPolicy(nextPolicy);
      setPolicyForm(policyToForm(nextPolicy));
      setStatus("Policy saved");
    });
  }

  async function evaluateAutomation() {
    await run("Evaluating action", async () => {
      const id = requireAgentId();
      const result = await postJson<AutomationEvaluation>(
        `/agents/${id}/automation-policy/evaluate`,
        buildActionPayload(actionForm),
      );
      setEvaluation(result);
      setStatus(result.reason);
    });
  }

  async function requestDelegation() {
    await run("Requesting delegation", async () => {
      const id = requireAgentId();
      const result = await postJson<DelegationRequest>(`/agents/${id}/automation/delegation/request`, {});
      setDelegationRequest(result);
      await loadPolicy();
      setStatus(result.message);
    });
  }

  async function confirmDelegation() {
    await run("Confirming delegation", async () => {
      const id = requireAgentId();
      if (!smartAccountAddress) {
        throw new Error("Enter a smart account address after granting permission in MetaMask Smart Accounts.");
      }
      const nextPolicy = await postJson<AutomationPolicy>(`/agents/${id}/automation/delegation/confirm`, {
        smart_account_address: smartAccountAddress,
        delegation_id: delegationId,
        delegation_scope: delegationRequest?.policy_scope ?? policy?.delegation_scope ?? {},
      });
      setPolicy(nextPolicy);
      setPolicyForm(policyToForm(nextPolicy));
      setStatus("Delegation metadata stored");
    });
  }

  async function executeAutomated() {
    await run("Executing automation", async () => {
      const id = requireAgentId();
      const result = await postJson<AutomatedTransactionResponse>(
        `/agents/${id}/transactions/execute-automated`,
        buildActionPayload(actionForm),
      );
      setAutomatedResult(result);
      setEvaluation(result.evaluation);
      setStatus(result.reason);

      if (result.delegation_required) return;

      if (result.requires_user_confirmation) {
        if (!window.ethereum) throw new Error("MetaMask is not available in this browser.");
        if (!result.transaction_request) throw new Error("No transaction request returned for MetaMask confirmation.");
        const sentHash = (await window.ethereum.request({
          method: "eth_sendTransaction",
          params: [result.transaction_request],
        })) as string;
        setTxHash(sentHash);
        setStatus("Transaction sent with MetaMask");
        return;
      }

      if (result.smart_account_execution_payload && !window.ethereumSmartAccounts) {
        setStatus("Smart Account execution payload is ready; submit it with MetaMask Smart Accounts Kit.");
      }
    });
  }

  function requireAgentId() {
    if (!agentId) {
      throw new Error("Verify a wallet before configuring automation.");
    }
    return agentId;
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Agentic Economy</p>
          <h1>Agent Reputation Passport</h1>
        </div>
        <div className="actions">
          <button type="button" onClick={connectMetaMask} disabled={busy}>Connect MetaMask</button>
          <button type="button" className="primary" onClick={verifyWallet} disabled={!canVerify}>Verify Wallet</button>
        </div>
      </header>

      <section className="status-row" aria-live="polite">
        <span className="status-pill">{status}</span>
        {walletAddress && <span className="wallet-pill">{shortAddress(walletAddress)}</span>}
        {error && <span className="error-text">{error}</span>}
      </section>

      <section className="workspace">
        <Panel title="Wallet">
          <Facts
            items={[
              ["Address", walletAddress || "Not connected"],
              ["Chain ID", String(chainId)],
              ["Backend", API_BASE],
            ]}
          />
        </Panel>

        <Panel title="Passport">
          {passport ? (
            <Facts
              items={[
                ["Agent", passport.agent.name],
                ["Trust Score", `${passport.reputation.trust_score}/100`],
                ["Risk", passport.reputation.risk_level],
              ]}
            />
          ) : <p className="empty-state">No verified passport yet.</p>}
        </Panel>

        <Panel title="Decision" className="decision-panel">
          {intelligence ? (
            <>
              <div className={`decision ${intelligence.wallet_permission.decision}`}>{intelligence.wallet_permission.decision}</div>
              <p>{intelligence.summary}</p>
              <p>{intelligence.wallet_permission.reason}</p>
              <Facts
                compact
                items={[
                  ["Limit", formatUsd(intelligence.wallet_permission.recommended_limit_usd)],
                  ["Confidence", intelligence.risk_assessment.confidence],
                ]}
              />
            </>
          ) : <p className="empty-state">No decision yet.</p>}
        </Panel>

        <Panel title="Smart Account Automation" wide>
          <p className="warning">Automatic transactions without seed phrase require MetaMask Smart Accounts / Delegation. A normal MetaMask EOA cannot silently auto-confirm transactions.</p>
          <div className="form-grid">
            <label className="check-row">
              <input type="checkbox" checked={policyForm.automation_enabled} onChange={(event) => setPolicyForm({ ...policyForm, automation_enabled: event.target.checked })} />
              Automation enabled
            </label>
            <label>
              Mode
              <select value={policyForm.mode} onChange={(event) => setPolicyForm({ ...policyForm, mode: event.target.value as AutomationMode })}>
                <option value="manual">manual</option>
                <option value="semi_auto">semi_auto</option>
                <option value="full_auto">full_auto</option>
              </select>
            </label>
            <label>Max tx value USD<input value={policyForm.max_tx_value_usd} onChange={(event) => setPolicyForm({ ...policyForm, max_tx_value_usd: event.target.value })} /></label>
            <label>Daily limit USD<input value={policyForm.daily_limit_usd} onChange={(event) => setPolicyForm({ ...policyForm, daily_limit_usd: event.target.value })} /></label>
            <label>Max transactions/hour<input value={policyForm.max_transactions_per_hour} onChange={(event) => setPolicyForm({ ...policyForm, max_transactions_per_hour: event.target.value })} /></label>
            <label>Min native balance wei<input value={policyForm.min_native_balance_wei} onChange={(event) => setPolicyForm({ ...policyForm, min_native_balance_wei: event.target.value })} /></label>
            <label>Confirm above USD<input value={policyForm.require_confirmation_above_usd} onChange={(event) => setPolicyForm({ ...policyForm, require_confirmation_above_usd: event.target.value })} /></label>
            <label className="check-row">
              <input type="checkbox" checked={policyForm.emergency_stop} onChange={(event) => setPolicyForm({ ...policyForm, emergency_stop: event.target.checked })} />
              Emergency stop
            </label>
            <label>Allowed chain IDs<textarea value={policyForm.allowed_chain_ids} onChange={(event) => setPolicyForm({ ...policyForm, allowed_chain_ids: event.target.value })} /></label>
            <label>Allowed tokens<textarea value={policyForm.allowed_tokens} onChange={(event) => setPolicyForm({ ...policyForm, allowed_tokens: event.target.value })} /></label>
            <label>Allowed recipients<textarea value={policyForm.allowed_recipients} onChange={(event) => setPolicyForm({ ...policyForm, allowed_recipients: event.target.value })} /></label>
            <label>Allowed actions<textarea value={policyForm.allowed_actions} onChange={(event) => setPolicyForm({ ...policyForm, allowed_actions: event.target.value })} /></label>
          </div>
          <div className="button-row">
            <button type="button" onClick={loadPolicy} disabled={busy || !agentId}>Load Policy</button>
            <button type="button" onClick={savePolicy} disabled={busy || !agentId}>Save Policy</button>
            <button type="button" onClick={evaluateAutomation} disabled={busy || !agentId}>Evaluate Action</button>
          </div>
          {policy && <Facts compact items={[["Delegation", policy.delegation_status], ["Smart account", policy.smart_account_address ?? "None"]]} />}
          {evaluation && <pre>{JSON.stringify(evaluation, null, 2)}</pre>}
        </Panel>

        <Panel title="Delegation" wide>
          <div className="form-grid">
            <label>Smart account address<input value={smartAccountAddress} onChange={(event) => setSmartAccountAddress(event.target.value)} /></label>
            <label>Delegation ID<input value={delegationId} onChange={(event) => setDelegationId(event.target.value)} /></label>
          </div>
          <div className="button-row">
            <button type="button" onClick={requestDelegation} disabled={busy || !agentId}>Request Delegation</button>
            <button type="button" onClick={confirmDelegation} disabled={busy || !agentId}>Confirm Delegation</button>
          </div>
          {delegationRequest && <pre>{JSON.stringify(delegationRequest, null, 2)}</pre>}
        </Panel>

        <Panel title="Automated Transaction Test" wide>
          <div className="form-grid">
            <label>Action type<input value={actionForm.action_type} onChange={(event) => setActionForm({ ...actionForm, action_type: event.target.value })} /></label>
            <label>Recipient<input value={actionForm.recipient} onChange={(event) => setActionForm({ ...actionForm, recipient: event.target.value })} /></label>
            <label>Token<input value={actionForm.token} onChange={(event) => setActionForm({ ...actionForm, token: event.target.value })} placeholder="blank for NATIVE" /></label>
            <label>Value wei<input value={actionForm.value_wei} onChange={(event) => setActionForm({ ...actionForm, value_wei: event.target.value })} /></label>
            <label>Value USD<input value={actionForm.value_usd} onChange={(event) => setActionForm({ ...actionForm, value_usd: event.target.value })} /></label>
            <label>Chain ID<input value={actionForm.chain_id} onChange={(event) => setActionForm({ ...actionForm, chain_id: event.target.value })} /></label>
            <label>Reason<input value={actionForm.reason} onChange={(event) => setActionForm({ ...actionForm, reason: event.target.value })} /></label>
          </div>
          <div className="button-row">
            <button type="button" onClick={evaluateAutomation} disabled={busy || !agentId}>Evaluate Automation</button>
            <button type="button" className="primary" onClick={executeAutomated} disabled={busy || !agentId}>Execute Automated Transaction</button>
          </div>
          {txHash && <p><strong>tx_hash:</strong> {txHash}</p>}
          {automatedResult && <pre>{JSON.stringify(automatedResult, null, 2)}</pre>}
        </Panel>
      </section>
    </main>
  );
}

function Panel({ title, wide, className, children }: { title: string; wide?: boolean; className?: string; children: ReactNode }) {
  return <article className={`panel ${wide ? "wide" : ""} ${className ?? ""}`}><h2>{title}</h2>{children}</article>;
}

function Facts({ items, compact }: { items: Array<[string, string]>; compact?: boolean }) {
  return <dl className={`facts ${compact ? "compact" : ""}`}>{items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

function policyToForm(policy: AutomationPolicy) {
  return {
    automation_enabled: policy.automation_enabled,
    mode: policy.mode,
    max_tx_value_usd: String(policy.max_tx_value_usd),
    daily_limit_usd: String(policy.daily_limit_usd),
    max_transactions_per_hour: String(policy.max_transactions_per_hour),
    min_native_balance_wei: policy.min_native_balance_wei,
    require_confirmation_above_usd: String(policy.require_confirmation_above_usd),
    allowed_chain_ids: policy.allowed_chain_ids.join(", "),
    allowed_tokens: policy.allowed_tokens.join(", "),
    allowed_recipients: policy.allowed_recipients.join(", "),
    allowed_actions: policy.allowed_actions.join(", "),
    emergency_stop: policy.emergency_stop,
  };
}

function buildPolicyPayload(form: typeof defaultPolicyForm) {
  return {
    automation_enabled: form.automation_enabled,
    mode: form.mode,
    max_tx_value_usd: Number(form.max_tx_value_usd),
    daily_limit_usd: Number(form.daily_limit_usd),
    max_transactions_per_hour: Number(form.max_transactions_per_hour),
    min_native_balance_wei: form.min_native_balance_wei,
    require_confirmation_above_usd: Number(form.require_confirmation_above_usd),
    allowed_chain_ids: splitList(form.allowed_chain_ids).map((item) => Number(item)),
    allowed_tokens: splitList(form.allowed_tokens),
    allowed_recipients: splitList(form.allowed_recipients),
    allowed_actions: splitList(form.allowed_actions),
    emergency_stop: form.emergency_stop,
  };
}

function buildActionPayload(form: typeof defaultActionForm) {
  return {
    action_type: form.action_type,
    to_address: form.recipient,
    token_address: form.token || null,
    value_wei: form.value_wei,
    value_usd: Number(form.value_usd),
    chain_id: Number(form.chain_id),
    reason: form.reason,
    metadata: { source: "frontend_smart_account_automation" },
  };
}

function splitList(value: string) {
  return value.split(/[\n,]+/).map((item) => item.trim()).filter(Boolean);
}

function readableError(error: unknown) {
  const maybe = error as { code?: number; message?: string };
  const message = maybe?.message ?? String(error);
  if (maybe?.code === 4001 || message.toLowerCase().includes("user rejected")) {
    return "User rejected the MetaMask request.";
  }
  if (message.toLowerCase().includes("failed to fetch")) {
    return "Backend offline or unreachable. Start FastAPI at http://127.0.0.1:8000.";
  }
  return message;
}
