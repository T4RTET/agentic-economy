import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";
const HARDHAT_RPC_URL = "http://127.0.0.1:8545";
const HARDHAT_CHAIN_ID = 31337;
const HARDHAT_CHAIN_ID_HEX = "0x7a69";
const EXPECTED_CHAIN_ID = Number(import.meta.env.VITE_CHAIN_ID ?? String(HARDHAT_CHAIN_ID));
const EXPECTED_CHAIN_ID_HEX = import.meta.env.VITE_CHAIN_ID_HEX ?? HARDHAT_CHAIN_ID_HEX;
const AGENT_NAME = import.meta.env.VITE_AGENT_NAME ?? "My MetaMask Test Agent";
const AGENT_TYPE = import.meta.env.VITE_AGENT_TYPE ?? "wallet-linked-agent";
const FAKE_TX_HASH = "0xtesttransaction123";
const DEFAULT_RECIPIENT_ADDRESS = "0x6482400504F39C93469c8366b96e4A06a10b1DB9";

type EthereumProvider = {
  request(args: { method: string; params?: unknown[] | object }): Promise<unknown>;
  on?(event: "accountsChanged" | "chainChanged", handler: (value: string[] | string) => void): void;
  removeListener?(event: "accountsChanged" | "chainChanged", handler: (value: string[] | string) => void): void;
};

declare global {
  interface Window {
    ethereum?: EthereumProvider;
    ethereumSmartAccounts?: unknown;
  }
}

type AgentEvent = {
  id: number;
  title: string;
  category: string;
  outcome: string;
  value_usd: number;
  tx_hash: string | null;
  created_at: string;
};

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
  actions_history: AgentEvent[];
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
  };
  marketplace_verdict: {
    can_be_rented: boolean;
  };
  suggested_next_actions: string[];
};

type NonceResponse = {
  message: string;
};

type VerifyResponse = {
  verified: boolean;
  agent_id?: number;
  passport: AgentPassport;
};

type PreparedTransaction = {
  from?: string;
  to?: string;
  value?: string;
  chain_id?: number;
  reason?: string;
  requires_user_signature?: boolean;
  from_address?: string;
  to_address?: string;
  value_wei?: string;
  transaction_request?: Record<string, string>;
};

type RecordResponse = {
  event: AgentEvent;
  passport: AgentPassport;
  intelligence: IntelligenceReport;
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

type StatusKind = "idle" | "ok" | "error";

const defaultPolicyForm = {
  automation_enabled: false,
  mode: "manual" as AutomationMode,
  max_tx_value_usd: "1",
  daily_limit_usd: "10",
  max_transactions_per_hour: "3",
  min_native_balance_wei: "0",
  require_confirmation_above_usd: "0.5",
  allowed_chain_ids: String(HARDHAT_CHAIN_ID),
  allowed_tokens: "NATIVE",
  allowed_recipients: DEFAULT_RECIPIENT_ADDRESS,
  allowed_actions: "native_transfer",
  emergency_stop: false,
};

const defaultAutomationAction = {
  action_type: "native_transfer",
  recipient: DEFAULT_RECIPIENT_ADDRESS,
  token: "",
  value_wei: "1000000000000000",
  value_usd: "1",
  chain_id: String(HARDHAT_CHAIN_ID),
  reason: "Automated local test transaction",
};

function App() {
  const [backendStatus, setBackendStatus] = useState<StatusKind>("idle");
  const [backendMessage, setBackendMessage] = useState("Not checked");
  const [walletAddress, setWalletAddress] = useState("");
  const [chainId, setChainId] = useState<number | null>(null);
  const [verified, setVerified] = useState(false);
  const [agentId, setAgentId] = useState<number | null>(null);
  const [passport, setPassport] = useState<AgentPassport | null>(null);
  const [intelligence, setIntelligence] = useState<IntelligenceReport | null>(null);
  const [recipientAddress, setRecipientAddress] = useState(DEFAULT_RECIPIENT_ADDRESS);
  const [valueWei, setValueWei] = useState("1000000000000000");
  const [valueUsd, setValueUsd] = useState("1");
  const [reason, setReason] = useState("Local Hardhat test transaction");
  const [prepared, setPrepared] = useState<PreparedTransaction | null>(null);
  const [txHash, setTxHash] = useState("");
  const [automationPolicy, setAutomationPolicy] = useState<AutomationPolicy | null>(null);
  const [policyForm, setPolicyForm] = useState(defaultPolicyForm);
  const [automationAction, setAutomationAction] = useState(defaultAutomationAction);
  const [automationEvaluation, setAutomationEvaluation] = useState<AutomationEvaluation | null>(null);
  const [delegationRequest, setDelegationRequest] = useState<DelegationRequest | null>(null);
  const [delegationSmartAccount, setDelegationSmartAccount] = useState("");
  const [delegationId, setDelegationId] = useState("local-delegation-test");
  const [automatedResult, setAutomatedResult] = useState<AutomatedTransactionResponse | null>(null);
  const [automationMessage, setAutomationMessage] = useState("");
  const [busyAction, setBusyAction] = useState("");
  const [error, setError] = useState("");

  const chainMatches = useMemo(() => chainId === EXPECTED_CHAIN_ID, [chainId]);

  useEffect(() => {
    if (!window.ethereum?.on) return;

    const onAccountsChanged = (value: string[] | string) => {
      const accounts = Array.isArray(value) ? value : [];
      setWalletAddress(accounts[0] ?? "");
      setVerified(false);
      setAgentId(null);
      setPassport(null);
      setIntelligence(null);
      setPrepared(null);
      setTxHash("");
      setAutomatedResult(null);
    };

    const onChainChanged = (value: string[] | string) => {
      if (typeof value === "string") {
        setChainId(Number.parseInt(value, 16));
      }
      setPrepared(null);
    };

    window.ethereum.on("accountsChanged", onAccountsChanged);
    window.ethereum.on("chainChanged", onChainChanged);

    return () => {
      window.ethereum?.removeListener?.("accountsChanged", onAccountsChanged);
      window.ethereum?.removeListener?.("chainChanged", onChainChanged);
    };
  }, []);

  async function checkBackend() {
    await run("Checking backend", async () => {
      const response = await apiGet<{ status: string }>("/health");
      setBackendStatus(response.status === "ok" ? "ok" : "error");
      setBackendMessage(response.status);
    });
  }

  async function connectMetaMask() {
    await run("Connecting MetaMask", async () => {
      if (!window.ethereum) {
        throw new Error("MetaMask is not installed. Please install the browser extension.");
      }

      const accounts = (await window.ethereum.request({ method: "eth_requestAccounts" })) as string[];
      const chainHex = (await window.ethereum.request({ method: "eth_chainId" })) as string;
      setWalletAddress(accounts[0] ?? "");
      setDelegationSmartAccount(accounts[0] ?? "");
      setChainId(Number.parseInt(chainHex, 16));
    });
  }

  async function verifyWallet() {
    await run("Verifying wallet", async () => {
      requireWallet();
      const activeChainId = requireConnectedChain();

      const nonceData = await apiPost<NonceResponse>("/auth/nonce", {
        wallet_address: walletAddress,
        chain_id: activeChainId,
      });

      const signature = (await window.ethereum!.request({
        method: "personal_sign",
        params: [nonceData.message, walletAddress],
      })) as string;

      const verifyResponse = await apiPost<VerifyResponse>("/auth/verify", {
        wallet_address: walletAddress,
        chain_id: activeChainId,
        message: nonceData.message,
        signature,
        agent_name: AGENT_NAME,
        agent_type: AGENT_TYPE,
      });

      const nextAgentId = verifyResponse.agent_id ?? verifyResponse.passport.agent.id;
      setVerified(verifyResponse.verified);
      setAgentId(nextAgentId);
      setPassport(verifyResponse.passport);
    });
  }

  async function loadPassport() {
    await run("Loading passport", async () => {
      const id = requireAgentId();
      setPassport(await apiGet<AgentPassport>(`/agents/${id}/passport`));
    });
  }

  async function loadIntelligence() {
    await run("Loading intelligence", async () => {
      const id = requireAgentId();
      setIntelligence(await apiGet<IntelligenceReport>(`/agents/${id}/intelligence`));
    });
  }

  async function prepareTransaction() {
    await run("Preparing transaction", async () => {
      const id = requireAgentId();
      const activeChainId = requireHardhatChain();

      const response = await apiPost<PreparedTransaction>(`/agents/${id}/transactions/prepare`, {
        recipient_address: recipientAddress,
        value_wei: valueWei,
        value_usd: Number(valueUsd),
        chain_id: activeChainId,
        reason,
      });

      setPrepared(response);
    });
  }

  async function sendPreparedTransaction() {
    await run("Sending transaction", async () => {
      requireWallet();
      if (!prepared) {
        throw new Error("No prepared transaction yet.");
      }
      requireHardhatChain();

      const txRequest = toMetaMaskTransaction(prepared);
      const sentHash = (await window.ethereum!.request({
        method: "eth_sendTransaction",
        params: [txRequest],
      })) as string;

      setTxHash(sentHash);
      await recordTransaction(sentHash, false);
    });
  }

  async function recordRealTransaction() {
    await run("Recording transaction", async () => {
      if (!txHash) {
        throw new Error("No tx_hash yet.");
      }
      await recordTransaction(txHash, false);
    });
  }

  async function recordFakeTransaction() {
    await run("Recording fake test tx_hash", async () => {
      setTxHash(FAKE_TX_HASH);
      await recordTransaction(FAKE_TX_HASH, true);
    });
  }

  async function loadAutomationPolicy() {
    await run("Loading automation policy", async () => {
      const id = requireAgentId();
      const policy = await apiGet<AutomationPolicy>(`/agents/${id}/automation-policy`);
      setAutomationPolicy(policy);
      setPolicyForm(policyToForm(policy));
      setDelegationSmartAccount(policy.smart_account_address ?? walletAddress);
      setDelegationId(policy.delegation_id ?? "local-delegation-test");
    });
  }

  async function saveAutomationPolicy() {
    await run("Saving automation policy", async () => {
      const id = requireAgentId();
      const policy = await apiPut<AutomationPolicy>(`/agents/${id}/automation-policy`, buildPolicyPayload(policyForm));
      setAutomationPolicy(policy);
      setPolicyForm(policyToForm(policy));
    });
  }

  async function evaluateAutomationAction() {
    await run("Evaluating automation action", async () => {
      const id = requireAgentId();
      const evaluation = await apiPost<AutomationEvaluation>(
        `/agents/${id}/automation-policy/evaluate`,
        buildAutomationActionPayload(automationAction),
      );
      setAutomationEvaluation(evaluation);
      setAutomationMessage(evaluation.reason);
    });
  }

  async function requestDelegation() {
    await run("Requesting delegation", async () => {
      const id = requireAgentId();
      const response = await apiPost<DelegationRequest>(`/agents/${id}/automation/delegation/request`, {});
      setDelegationRequest(response);
      setAutomationMessage(response.message);
      const policy = await apiGet<AutomationPolicy>(`/agents/${id}/automation-policy`);
      setAutomationPolicy(policy);
      setPolicyForm(policyToForm(policy));
    });
  }

  async function confirmDelegation() {
    await run("Confirming delegation", async () => {
      const id = requireAgentId();
      if (!delegationSmartAccount) {
        throw new Error("Enter a smart account address after granting permission in MetaMask Smart Accounts.");
      }
      const policy = await apiPost<AutomationPolicy>(`/agents/${id}/automation/delegation/confirm`, {
        smart_account_address: delegationSmartAccount,
        delegation_id: delegationId,
        delegation_scope: delegationRequest?.policy_scope ?? automationPolicy?.delegation_scope ?? {},
      });
      setAutomationPolicy(policy);
      setPolicyForm(policyToForm(policy));
      setAutomationMessage("Delegation metadata stored. Automatic execution still depends on MetaMask Smart Accounts support.");
    });
  }

  async function executeAutomatedTransaction() {
    await run("Executing automated transaction", async () => {
      const id = requireAgentId();
      const response = await apiPost<AutomatedTransactionResponse>(
        `/agents/${id}/transactions/execute-automated`,
        buildAutomationActionPayload(automationAction),
      );
      setAutomatedResult(response);
      setAutomationEvaluation(response.evaluation);
      setAutomationMessage(response.reason);

      if (response.delegation_required) {
        setAutomationMessage(`${response.reason} Use Request Delegation before trying automatic execution.`);
        return;
      }

      if (response.requires_user_confirmation) {
        requireWallet();
        if (!response.transaction_request) {
          throw new Error("No transaction_request returned for MetaMask confirmation.");
        }
        const sentHash = (await window.ethereum!.request({
          method: "eth_sendTransaction",
          params: [response.transaction_request],
        })) as string;
        setTxHash(sentHash);
        await recordAutomationTransaction(sentHash);
        return;
      }

      if (response.smart_account_execution_payload) {
        if (!window.ethereumSmartAccounts) {
          setAutomationMessage(
            "Automatic transactions without seed phrase require MetaMask Smart Accounts / Delegation. A normal MetaMask EOA cannot silently auto-confirm transactions.",
          );
          return;
        }
        setAutomationMessage("MetaMask Smart Accounts Kit is available; submit the displayed execution payload with the kit.");
      }
    });
  }

  async function recordTransaction(nextTxHash: string, fake: boolean) {
    const id = requireAgentId();
    const response = await apiPost<RecordResponse>(`/agents/${id}/transactions/record`, {
      tx_hash: nextTxHash,
      outcome: "success",
      value_usd: Number(valueUsd),
      metadata: {
        source: fake ? "test_frontend_fake_record" : "frontend_hardhat_test",
        recipient: recipientAddress,
        reason,
      },
    });

    setPassport(response.passport);
    setIntelligence(response.intelligence);
  }

  async function recordAutomationTransaction(nextTxHash: string) {
    const id = requireAgentId();
    const response = await apiPost<RecordResponse>(`/agents/${id}/transactions/record`, {
      tx_hash: nextTxHash,
      outcome: "success",
      value_usd: Number(automationAction.value_usd),
      metadata: {
        source: "frontend_automation_test",
        recipient: automationAction.recipient,
        reason: automationAction.reason,
      },
    });

    setPassport(response.passport);
    setIntelligence(response.intelligence);
  }

  async function run(label: string, action: () => Promise<void>) {
    setBusyAction(label);
    setError("");
    try {
      await action();
    } catch (err) {
      setError(readableError(err));
      if (label === "Checking backend") {
        setBackendStatus("error");
        setBackendMessage("error");
      }
    } finally {
      setBusyAction("");
    }
  }

  function requireWallet() {
    if (!window.ethereum) {
      throw new Error("MetaMask is not installed. Please install the browser extension.");
    }
    if (!walletAddress) {
      throw new Error("Wallet is not connected.");
    }
  }

  function requireConnectedChain() {
    if (chainId === null) {
      throw new Error("Wrong chain. Connect MetaMask and select local Hardhat network 31337.");
    }
    return chainId;
  }

  function requireHardhatChain() {
    const activeChainId = requireConnectedChain();
    if (activeChainId !== HARDHAT_CHAIN_ID) {
      throw new Error(
        `Wrong chain. Switch MetaMask to local Hardhat network ${HARDHAT_CHAIN_ID} (${HARDHAT_CHAIN_ID_HEX}). Current chain is ${activeChainId}.`,
      );
    }
    return activeChainId;
  }

  function requireAgentId() {
    if (!agentId) {
      throw new Error("No agent id yet. Verify wallet first.");
    }
    return agentId;
  }

  return (
    <main className="shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">Local testing only</p>
          <h1>Agent Reputation Passport + MetaMask</h1>
        </div>
        <div className="header-meta">
          <span>{BACKEND_URL}</span>
          <span>Hardhat chain {HARDHAT_CHAIN_ID}</span>
        </div>
      </header>

      {error && <div className="alert error">{error}</div>}
      {busyAction && <div className="alert busy">{busyAction}</div>}

      <section className="grid">
        <Panel title="1. Backend Status">
          <button onClick={checkBackend} disabled={Boolean(busyAction)}>Check Backend</button>
          <KeyValues
            items={[
              ["Backend URL", BACKEND_URL],
              ["Status", backendMessage],
            ]}
          />
          <span className={`badge ${backendStatus}`}>{backendStatus}</span>
        </Panel>

        <Panel title="2. MetaMask Connection">
          <button onClick={connectMetaMask} disabled={Boolean(busyAction)}>Connect MetaMask</button>
          <KeyValues
            items={[
              ["Wallet", walletAddress || "Not connected"],
              ["Current chain id", chainId ? String(chainId) : "Unknown"],
              ["Expected chain id", `${EXPECTED_CHAIN_ID} (${EXPECTED_CHAIN_ID_HEX})`],
              ["Hardhat RPC", HARDHAT_RPC_URL],
            ]}
          />
          {chainId !== null && !chainMatches && <p className="warning">Wrong chain selected in MetaMask.</p>}
        </Panel>

        <Panel title="3. Verify Wallet and Bind Agent">
          <button onClick={verifyWallet} disabled={!walletAddress || Boolean(busyAction)}>Verify Wallet</button>
          <KeyValues
            items={[
              ["Verified", verified ? "true" : "false"],
              ["Agent id", agentId ? String(agentId) : "None"],
              ["Agent name", passport?.agent.name ?? "None"],
              ["Owner wallet", passport?.agent.owner_wallet ?? "None"],
              ["Chain id", passport?.agent.chain_id ? String(passport.agent.chain_id) : "None"],
            ]}
          />
        </Panel>

        <Panel title="4. Agent Passport">
          <button onClick={loadPassport} disabled={!agentId || Boolean(busyAction)}>Load Passport</button>
          <KeyValues
            items={[
              ["Agent name", passport?.agent.name ?? "None"],
              ["Owner wallet", passport?.agent.owner_wallet ?? "None"],
              ["Trust score", passport ? `${passport.reputation.trust_score}/100` : "None"],
              ["Risk level", passport?.reputation.risk_level ?? "None"],
              ["Wallet limit", passport ? `$${passport.reputation.recommended_wallet_limit_usd}` : "None"],
            ]}
          />
          <History events={passport?.actions_history ?? []} />
        </Panel>

        <Panel title="5. Agent Intelligence">
          <button onClick={loadIntelligence} disabled={!agentId || Boolean(busyAction)}>Load Intelligence</button>
          {intelligence ? (
            <div className="stack">
              <p>{intelligence.summary}</p>
              <KeyValues
                items={[
                  ["Wallet decision", intelligence.wallet_permission.decision],
                  ["Recommended limit", `$${intelligence.wallet_permission.recommended_limit_usd}`],
                  ["Reason", intelligence.wallet_permission.reason],
                  ["Risk level", intelligence.risk_assessment.risk_level],
                  ["Can be rented", String(intelligence.marketplace_verdict.can_be_rented)],
                ]}
              />
              <List title="Main risks" items={intelligence.risk_assessment.main_risks} />
              <List title="Next actions" items={intelligence.suggested_next_actions} />
            </div>
          ) : (
            <p className="muted">No intelligence loaded.</p>
          )}
        </Panel>

        <Panel title="6. Transaction Test" wide>
          <KeyValues
            items={[
              ["Current MetaMask chain id", chainId ? String(chainId) : "Unknown"],
              ["Local Hardhat RPC", HARDHAT_RPC_URL],
              ["Local Hardhat chain id", `${HARDHAT_CHAIN_ID} (${HARDHAT_CHAIN_ID_HEX})`],
            ]}
          />
          <p className="muted">Prepared transactions are signed only through MetaMask. The app never asks for a seed phrase or private key.</p>
          <div className="form-grid">
            <label>
              Recipient address
              <input value={recipientAddress} onChange={(event) => setRecipientAddress(event.target.value)} />
            </label>
            <label>
              Value wei
              <input value={valueWei} onChange={(event) => setValueWei(event.target.value)} />
            </label>
            <label>
              Value USD
              <input value={valueUsd} onChange={(event) => setValueUsd(event.target.value)} />
            </label>
            <label>
              Reason
              <input value={reason} onChange={(event) => setReason(event.target.value)} />
            </label>
          </div>
          <button onClick={prepareTransaction} disabled={Boolean(busyAction)}>Prepare Transaction</button>
          {prepared && (
            <>
              <KeyValues
                items={[
                  ["From", prepared.from ?? prepared.from_address ?? "None"],
                  ["To", prepared.to ?? prepared.to_address ?? "None"],
                  ["Value", prepared.value ?? prepared.value_wei ?? "None"],
                  ["Chain id", prepared.chain_id ? String(prepared.chain_id) : "None"],
                  ["Reason", prepared.reason ?? "None"],
                  ["Requires signature", String(prepared.requires_user_signature)],
                ]}
              />
              <pre>{JSON.stringify(prepared, null, 2)}</pre>
            </>
          )}
        </Panel>

        <Panel title="7. Send with MetaMask">
          <button onClick={sendPreparedTransaction} disabled={Boolean(busyAction)}>
            Send with MetaMask
          </button>
          <KeyValues items={[["tx_hash", txHash || "None"]]} />
          <p className="muted">If MetaMask rejects, the wallet has no gas, or the chain is wrong, the error appears above.</p>
        </Panel>

        <Panel title="8. Record Transaction">
          <button onClick={recordRealTransaction} disabled={Boolean(busyAction)}>
            Record Current tx_hash
          </button>
          <p className="muted">After recording, passport and intelligence reload automatically.</p>
        </Panel>

        <Panel title="9. Test Mode Without Real Transaction" wide>
          <p className="warning">Backend-only fake record test. This is not a real blockchain transaction.</p>
          <button onClick={recordFakeTransaction} disabled={Boolean(busyAction)}>
            Record Fake Test tx_hash
          </button>
          <code>{FAKE_TX_HASH}</code>
        </Panel>

        <Panel title="10. Automation Settings" wide>
          <div className="form-grid">
            <label className="check-row">
              <input
                type="checkbox"
                checked={policyForm.automation_enabled}
                onChange={(event) => setPolicyForm({ ...policyForm, automation_enabled: event.target.checked })}
              />
              Automation enabled
            </label>
            <label>
              Mode
              <select
                value={policyForm.mode}
                onChange={(event) => setPolicyForm({ ...policyForm, mode: event.target.value as AutomationMode })}
              >
                <option value="manual">manual</option>
                <option value="semi_auto">semi_auto</option>
                <option value="full_auto">full_auto</option>
              </select>
            </label>
            <label>
              Max tx value USD
              <input value={policyForm.max_tx_value_usd} onChange={(event) => setPolicyForm({ ...policyForm, max_tx_value_usd: event.target.value })} />
            </label>
            <label>
              Daily limit USD
              <input value={policyForm.daily_limit_usd} onChange={(event) => setPolicyForm({ ...policyForm, daily_limit_usd: event.target.value })} />
            </label>
            <label>
              Max transactions per hour
              <input value={policyForm.max_transactions_per_hour} onChange={(event) => setPolicyForm({ ...policyForm, max_transactions_per_hour: event.target.value })} />
            </label>
            <label>
              Min native balance wei
              <input value={policyForm.min_native_balance_wei} onChange={(event) => setPolicyForm({ ...policyForm, min_native_balance_wei: event.target.value })} />
            </label>
            <label>
              Require confirmation above USD
              <input value={policyForm.require_confirmation_above_usd} onChange={(event) => setPolicyForm({ ...policyForm, require_confirmation_above_usd: event.target.value })} />
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={policyForm.emergency_stop}
                onChange={(event) => setPolicyForm({ ...policyForm, emergency_stop: event.target.checked })}
              />
              Emergency stop
            </label>
            <label>
              Allowed chain ids
              <textarea value={policyForm.allowed_chain_ids} onChange={(event) => setPolicyForm({ ...policyForm, allowed_chain_ids: event.target.value })} />
            </label>
            <label>
              Allowed tokens
              <textarea value={policyForm.allowed_tokens} onChange={(event) => setPolicyForm({ ...policyForm, allowed_tokens: event.target.value })} />
            </label>
            <label>
              Allowed recipients
              <textarea value={policyForm.allowed_recipients} onChange={(event) => setPolicyForm({ ...policyForm, allowed_recipients: event.target.value })} />
            </label>
            <label>
              Allowed actions
              <textarea value={policyForm.allowed_actions} onChange={(event) => setPolicyForm({ ...policyForm, allowed_actions: event.target.value })} />
            </label>
          </div>
          <div className="button-row">
            <button onClick={loadAutomationPolicy} disabled={Boolean(busyAction)}>Load Policy</button>
            <button onClick={saveAutomationPolicy} disabled={Boolean(busyAction)}>Save Policy</button>
            <button onClick={evaluateAutomationAction} disabled={Boolean(busyAction)}>Evaluate Action</button>
          </div>
          <KeyValues
            items={[
              ["Delegation status", automationPolicy?.delegation_status ?? "none"],
              ["Smart account", automationPolicy?.smart_account_address ?? "None"],
              ["Delegation id", automationPolicy?.delegation_id ?? "None"],
            ]}
          />
          {automationEvaluation && <pre>{JSON.stringify(automationEvaluation, null, 2)}</pre>}
        </Panel>

        <Panel title="11. MetaMask Smart Account Delegation" wide>
          <p className="warning">
            Automatic transactions without seed phrase require MetaMask Smart Accounts / Delegation. A normal MetaMask EOA cannot silently auto-confirm transactions.
          </p>
          <div className="form-grid">
            <label>
              Smart account address
              <input value={delegationSmartAccount} onChange={(event) => setDelegationSmartAccount(event.target.value)} />
            </label>
            <label>
              Delegation id
              <input value={delegationId} onChange={(event) => setDelegationId(event.target.value)} />
            </label>
          </div>
          <div className="button-row">
            <button onClick={requestDelegation} disabled={Boolean(busyAction)}>Request Delegation</button>
            <button onClick={confirmDelegation} disabled={Boolean(busyAction)}>Confirm Delegation</button>
          </div>
          {automationMessage && <p className="muted">{automationMessage}</p>}
          {delegationRequest && <pre>{JSON.stringify(delegationRequest, null, 2)}</pre>}
        </Panel>

        <Panel title="12. Automated Transaction Test" wide>
          <div className="form-grid">
            <label>
              Action type
              <input value={automationAction.action_type} onChange={(event) => setAutomationAction({ ...automationAction, action_type: event.target.value })} />
            </label>
            <label>
              Recipient
              <input value={automationAction.recipient} onChange={(event) => setAutomationAction({ ...automationAction, recipient: event.target.value })} />
            </label>
            <label>
              Token
              <input value={automationAction.token} onChange={(event) => setAutomationAction({ ...automationAction, token: event.target.value })} placeholder="blank for NATIVE" />
            </label>
            <label>
              Value wei
              <input value={automationAction.value_wei} onChange={(event) => setAutomationAction({ ...automationAction, value_wei: event.target.value })} />
            </label>
            <label>
              Value USD
              <input value={automationAction.value_usd} onChange={(event) => setAutomationAction({ ...automationAction, value_usd: event.target.value })} />
            </label>
            <label>
              Chain id
              <input value={automationAction.chain_id} onChange={(event) => setAutomationAction({ ...automationAction, chain_id: event.target.value })} />
            </label>
            <label>
              Reason
              <input value={automationAction.reason} onChange={(event) => setAutomationAction({ ...automationAction, reason: event.target.value })} />
            </label>
          </div>
          <div className="button-row">
            <button onClick={evaluateAutomationAction} disabled={Boolean(busyAction)}>Evaluate Automation</button>
            <button onClick={executeAutomatedTransaction} disabled={Boolean(busyAction)}>Execute Automated Transaction</button>
          </div>
          <KeyValues items={[["tx_hash", txHash || "None"]]} />
          {automatedResult && <pre>{JSON.stringify(automatedResult, null, 2)}</pre>}
        </Panel>
      </section>
    </main>
  );
}

function Panel({ title, wide, children }: { title: string; wide?: boolean; children: ReactNode }) {
  return (
    <article className={`panel ${wide ? "wide" : ""}`}>
      <h2>{title}</h2>
      <div className="stack">{children}</div>
    </article>
  );
}

function KeyValues({ items }: { items: Array<[string, string]> }) {
  return (
    <dl className="key-values">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h3>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function History({ events }: { events: AgentEvent[] }) {
  if (!events.length) {
    return <p className="muted">No actions yet.</p>;
  }

  return (
    <div>
      <h3>Actions history</h3>
      <ul className="history">
        {events.map((event) => (
          <li key={event.id}>
            <span>{event.title}</span>
            <span>{event.outcome}</span>
            {event.tx_hash && <code>{event.tx_hash}</code>}
          </li>
        ))}
      </ul>
    </div>
  );
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${path}`);
  return parseResponse<T>(response);
}

async function apiPost<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<T>(response);
}

async function apiPut<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<T>(response);
}

async function parseResponse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data));
  }
  return data as T;
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

function buildAutomationActionPayload(form: typeof defaultAutomationAction) {
  return {
    action_type: form.action_type,
    to_address: form.recipient,
    token_address: form.token || null,
    value_wei: form.value_wei,
    value_usd: Number(form.value_usd),
    chain_id: Number(form.chain_id),
    reason: form.reason,
    metadata: {
      source: "frontend_automation_panel",
    },
  };
}

function splitList(value: string) {
  return value
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function toMetaMaskTransaction(prepared: PreparedTransaction) {
  const from = prepared.from ?? prepared.from_address ?? prepared.transaction_request?.from;
  const to = prepared.to ?? prepared.to_address ?? prepared.transaction_request?.to;
  const value = prepared.value ?? prepared.value_wei ?? prepared.transaction_request?.value;
  const chainId = prepared.chain_id ?? prepared.transaction_request?.chainId ?? EXPECTED_CHAIN_ID;

  if (!from || !to || value === undefined) {
    throw new Error("Prepared transaction is missing from, to, or value.");
  }

  return {
    from,
    to,
    value: toHexQuantity(value),
    chainId: toHexQuantity(chainId),
  };
}

function toHexQuantity(value: string | number) {
  if (typeof value === "string" && value.startsWith("0x")) {
    return value;
  }
  return `0x${BigInt(value).toString(16)}`;
}

function readableError(error: unknown) {
  const maybe = error as { code?: number; message?: string };
  const message = maybe?.message ?? String(error);
  if (maybe?.code === 4001 || message.toLowerCase().includes("user rejected")) {
    return "User rejected the MetaMask request.";
  }
  if (message.toLowerCase().includes("insufficient")) {
    return "Wallet has no gas funds or insufficient funds for this transaction.";
  }
  if (message.toLowerCase().includes("chain")) {
    return message;
  }
  if (message.toLowerCase().includes("failed to fetch")) {
    return "Backend offline or unreachable. Start FastAPI at http://127.0.0.1:8000.";
  }
  return message;
}

export default App;
