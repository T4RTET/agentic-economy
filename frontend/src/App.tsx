import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  executeSmartAccountPayload,
  isSmartAccountAvailable,
  requestSmartAccountDelegation,
} from "./services/smartAccount";

const API_BASE = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";
const DEFAULT_CHAIN_ID = Number(import.meta.env.VITE_CHAIN_ID ?? 5000);
const DEFAULT_AGENT_NAME = import.meta.env.VITE_AGENT_NAME ?? "My MetaMask Test Agent";
const DEFAULT_AGENT_TYPE = import.meta.env.VITE_AGENT_TYPE ?? "wallet-linked-agent";
const DEFAULT_RECIPIENT = "0x000000000000000000000000000000000000dEaD";

type EthereumProvider = {
  request(args: { method: string; params?: unknown[] | Record<string, unknown> }): Promise<unknown>;
  on?(event: string, handler: (value: unknown) => void): void;
  removeListener?(event: string, handler: (value: unknown) => void): void;
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

type WalletNonceResponse = { message: string };

type WalletVerifyResponse = {
  verified: boolean;
  agent_id?: number;
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
type PresetName = "safe" | "balanced" | "custom";

type AutomationPolicy = {
  id: number;
  agent_id: number;
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
  delegation_scope: Record<string, unknown>;
};

type PolicyForm = {
  automation_enabled: boolean;
  mode: AutomationMode;
  max_tx_value_usd: string;
  daily_limit_usd: string;
  max_transactions_per_hour: string;
  min_native_balance_wei: string;
  require_confirmation_above_usd: string;
  allowed_chain_ids: string;
  allowed_tokens: string;
  allowed_recipients: string;
  allowed_actions: string;
  emergency_stop: boolean;
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
  agent_id: number;
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

type ActionForm = {
  action_type: string;
  recipient: string;
  token: string;
  value_wei: string;
  value_usd: string;
  chain_id: string;
  reason: string;
};

const defaultActionForm: ActionForm = {
  action_type: "native_transfer",
  recipient: DEFAULT_RECIPIENT,
  token: "",
  value_wei: "1000000000000000",
  value_usd: "1",
  chain_id: String(DEFAULT_CHAIN_ID),
  reason: "Локальный тест автоматического действия",
};

function presetPolicy(preset: PresetName, chainId: number, recipient: string): PolicyForm {
  const baseRecipient = recipient || DEFAULT_RECIPIENT;
  if (preset === "balanced") {
    return {
      automation_enabled: true,
      mode: "semi_auto",
      max_tx_value_usd: "5",
      daily_limit_usd: "20",
      max_transactions_per_hour: "3",
      min_native_balance_wei: "100000000000000000",
      require_confirmation_above_usd: "5",
      allowed_chain_ids: String(chainId),
      allowed_tokens: "NATIVE",
      allowed_recipients: baseRecipient,
      allowed_actions: "native_transfer",
      emergency_stop: false,
    };
  }

  return {
    automation_enabled: true,
    mode: "semi_auto",
    max_tx_value_usd: "1",
    daily_limit_usd: "5",
    max_transactions_per_hour: "1",
    min_native_balance_wei: "100000000000000000",
    require_confirmation_above_usd: "1",
    allowed_chain_ids: String(chainId),
    allowed_tokens: "NATIVE",
    allowed_recipients: baseRecipient,
    allowed_actions: "native_transfer",
    emergency_stop: false,
  };
}

export default function App() {
  const [walletAddress, setWalletAddress] = useState("");
  const [chainId, setChainId] = useState(DEFAULT_CHAIN_ID);
  const [passport, setPassport] = useState<AgentPassport | null>(null);
  const [intelligence, setIntelligence] = useState<IntelligenceReport | null>(null);
  const [policy, setPolicy] = useState<AutomationPolicy | null>(null);
  const [policyForm, setPolicyForm] = useState<PolicyForm>(() => presetPolicy("safe", DEFAULT_CHAIN_ID, DEFAULT_RECIPIENT));
  const [preset, setPreset] = useState<PresetName>("safe");
  const [delegationRequest, setDelegationRequest] = useState<DelegationRequest | null>(null);
  const [smartAccountMessage, setSmartAccountMessage] = useState("");
  const [evaluation, setEvaluation] = useState<AutomationEvaluation | null>(null);
  const [actionForm, setActionForm] = useState<ActionForm>(defaultActionForm);
  const [automatedResult, setAutomatedResult] = useState<AutomatedTransactionResponse | null>(null);
  const [txHash, setTxHash] = useState("");
  const [status, setStatus] = useState("Готово");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const agentId = passport?.agent.id ?? null;
  const verified = Boolean(agentId && passport);
  const automationEnabled = Boolean(policy?.automation_enabled && policy.delegation_status === "active");
  const canEnableAutomation = useMemo(() => {
    return Boolean(walletAddress && agentId && intelligence?.wallet_permission.decision !== "deny" && !busy);
  }, [agentId, busy, intelligence, walletAddress]);

  useEffect(() => {
    const provider = window.ethereum;
    if (!provider?.on) return;

    const handleAccounts = (value: unknown) => {
      const accounts = Array.isArray(value) ? value : [];
      const nextAccount = typeof accounts[0] === "string" ? accounts[0] : "";
      setWalletAddress(nextAccount);
      setPassport(null);
      setIntelligence(null);
      setPolicy(null);
    };

    const handleChain = (value: unknown) => {
      if (typeof value === "string") {
        const parsed = Number.parseInt(value, 16);
        setChainId(Number.isFinite(parsed) ? parsed : DEFAULT_CHAIN_ID);
        setActionForm((current) => ({ ...current, chain_id: String(Number.isFinite(parsed) ? parsed : DEFAULT_CHAIN_ID) }));
      }
    };

    provider.on("accountsChanged", handleAccounts);
    provider.on("chainChanged", handleChain);

    return () => {
      provider.removeListener?.("accountsChanged", handleAccounts);
      provider.removeListener?.("chainChanged", handleChain);
    };
  }, []);

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
    await run("Подключаю MetaMask", async () => {
      if (!window.ethereum) throw new Error("MetaMask не установлен. Установите расширение браузера.");
      const accounts = (await window.ethereum.request({ method: "eth_requestAccounts" })) as string[];
      const chainHex = (await window.ethereum.request({ method: "eth_chainId" })) as string;
      const nextChainId = Number.parseInt(chainHex, 16);
      const nextWallet = accounts[0] ?? "";
      setWalletAddress(nextWallet);
      setChainId(nextChainId);
      setPolicyForm(presetPolicy(preset, nextChainId, actionForm.recipient));
      setActionForm((current) => ({ ...current, chain_id: String(nextChainId) }));
      setStatus("MetaMask подключён");
    });
  }

  async function verifyWallet() {
    await run("Проверяю владение кошельком", async () => {
      if (!window.ethereum) throw new Error("MetaMask не установлен.");
      if (!walletAddress) throw new Error("Сначала подключите MetaMask.");
      const nonce = await postJson<WalletNonceResponse>("/auth/nonce", {
        wallet_address: walletAddress,
        chain_id: chainId,
      });
      const signature = (await window.ethereum.request({
        method: "personal_sign",
        params: [nonce.message, walletAddress],
      })) as string;
      const verifiedWallet = await postJson<WalletVerifyResponse>("/auth/verify", {
        wallet_address: walletAddress,
        chain_id: chainId,
        message: nonce.message,
        signature,
        agent_name: DEFAULT_AGENT_NAME,
        agent_type: DEFAULT_AGENT_TYPE,
      });
      setPassport(verifiedWallet.passport);
      const report = await getJson<IntelligenceReport>(`/agents/${verifiedWallet.passport.agent.id}/intelligence`);
      setIntelligence(report);
      const nextPolicy = await getJson<AutomationPolicy>(`/agents/${verifiedWallet.passport.agent.id}/automation-policy`);
      setPolicy(nextPolicy);
      setPolicyForm(policyToForm(nextPolicy));
      setStatus("Кошелёк подтверждён, агент привязан");
    });
  }

  async function loadPolicy() {
    await run("Загружаю policy", async () => {
      const id = requireAgentId();
      const nextPolicy = await getJson<AutomationPolicy>(`/agents/${id}/automation-policy`);
      setPolicy(nextPolicy);
      setPolicyForm(policyToForm(nextPolicy));
      setStatus("Policy загружена");
    });
  }

  async function enableAutomation() {
    await run("Включаю автоматизацию", async () => {
      const id = requireAgentId();
      if (!walletAddress) throw new Error("Сначала подключите MetaMask.");
      if (intelligence?.wallet_permission.decision === "deny") {
        throw new Error("Intelligence запрещает wallet-действия для этого агента.");
      }

      const savedPolicy = await putJson<AutomationPolicy>(`/agents/${id}/automation-policy`, buildPolicyPayload(policyForm));
      setPolicy(savedPolicy);
      const request = await postJson<DelegationRequest>(`/agents/${id}/automation/delegation/request`, {});
      setDelegationRequest(request);

      try {
        await requestSmartAccountDelegation({
          agentId: id,
          walletAddress,
          policyScope: request.policy_scope,
          request: request.request,
        });
        setSmartAccountMessage("MetaMask Smart Account delegation запрошен через SDK.");
      } catch (err) {
        setSmartAccountMessage(readableError(err));
      }

      setStatus("Настройки сохранены. Подтвердите delegation в MetaMask или используйте локальный тест.");
    });
  }

  async function confirmTestDelegation() {
    await run("Подтверждаю test delegation", async () => {
      const id = requireAgentId();
      if (!walletAddress) throw new Error("Сначала подключите MetaMask.");
      const scope = delegationRequest?.policy_scope ?? policy?.delegation_scope ?? buildPolicyPayload(policyForm);
      const nextPolicy = await postJson<AutomationPolicy>(`/agents/${id}/automation/delegation/confirm`, {
        smart_account_address: walletAddress,
        delegation_id: `local-test-delegation-${id}`,
        delegation_scope: scope,
      });
      setPolicy(nextPolicy);
      setPolicyForm(policyToForm(nextPolicy));
      setStatus("Automation Enabled");
    });
  }

  async function evaluateAction() {
    await run("Проверяю действие через policy engine", async () => {
      const id = requireAgentId();
      const result = await postJson<AutomationEvaluation>(`/agents/${id}/automation-policy/evaluate`, buildActionPayload(actionForm));
      setEvaluation(result);
      setStatus(result.reason);
    });
  }

  async function runAutomatedAction() {
    await run("Запускаю автоматическое действие", async () => {
      const id = requireAgentId();
      const result = await postJson<AutomatedTransactionResponse>(
        `/agents/${id}/transactions/execute-automated`,
        buildActionPayload(actionForm),
      );
      setAutomatedResult(result);
      setEvaluation(result.evaluation);
      setStatus(result.reason);

      if (result.delegation_required) {
        setSmartAccountMessage("Нужно включить Automation / Delegation.");
        return;
      }

      if (result.smart_account_execution_payload) {
        try {
          const smartResult = await executeSmartAccountPayload(result.smart_account_execution_payload);
          if (smartResult.txHash) setTxHash(smartResult.txHash);
          setSmartAccountMessage("Smart Account payload отправлен через SDK.");
        } catch (err) {
          setSmartAccountMessage(readableError(err));
        }
      }
    });
  }

  async function sendWithMetaMask() {
    await run("Отправляю через MetaMask", async () => {
      if (!window.ethereum) throw new Error("MetaMask не установлен.");
      if (!automatedResult?.transaction_request) throw new Error("Нет подготовленной транзакции для MetaMask.");
      const sentHash = (await window.ethereum.request({
        method: "eth_sendTransaction",
        params: [automatedResult.transaction_request],
      })) as string;
      setTxHash(sentHash);
      setStatus("Транзакция отправлена через MetaMask");
    });
  }

  function applyPreset(nextPreset: PresetName) {
    setPreset(nextPreset);
    if (nextPreset !== "custom") {
      setPolicyForm(presetPolicy(nextPreset, chainId, actionForm.recipient));
    }
  }

  function updatePolicyField<Key extends keyof PolicyForm>(key: Key, value: PolicyForm[Key]) {
    setPreset("custom");
    setPolicyForm((current) => ({ ...current, [key]: value }));
  }

  function requireAgentId() {
    if (!agentId) throw new Error("Сначала подтвердите кошелёк и привяжите агента.");
    return agentId;
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Agentic Economy</p>
          <h1>AI-агент с MetaMask Automation</h1>
          <p className="lead">Одна кнопка включает policy, Smart Account delegation и безопасный тест автоматического действия.</p>
        </div>
        <div className="header-actions">
          <button type="button" onClick={connectMetaMask} disabled={busy}>Connect MetaMask</button>
          <button type="button" className="primary" onClick={verifyWallet} disabled={busy || !walletAddress}>Verify Wallet</button>
        </div>
      </header>

      <section className="status-row" aria-live="polite">
        <span className="status-pill">{status}</span>
        <span className="wallet-pill">Backend: {API_BASE}</span>
        {walletAddress && <span className="wallet-pill">{shortAddress(walletAddress)}</span>}
        {error && <span className="error-text">{error}</span>}
      </section>

      <section className="workspace">
        <Panel title="MetaMask">
          <Facts
            items={[
              ["Кошелёк", walletAddress || "Не подключён"],
              ["Chain ID", String(chainId)],
              ["Smart Account SDK", isSmartAccountAvailable() ? "доступен" : "не подключён"],
            ]}
          />
          <p className="hint">Seed phrase и private key здесь не нужны и никогда не отправляются в backend.</p>
        </Panel>

        <Panel title="Паспорт агента">
          {passport ? (
            <Facts
              items={[
                ["Agent ID", String(passport.agent.id)],
                ["Имя", passport.agent.name],
                ["Owner wallet", passport.agent.owner_wallet],
                ["Trust score", `${passport.reputation.trust_score}/100`],
                ["Risk", passport.reputation.risk_level],
              ]}
            />
          ) : <p className="empty-state">Подключите MetaMask и нажмите Verify Wallet.</p>}
        </Panel>

        <Panel title="Intelligence">
          {intelligence ? (
            <>
              <div className={`decision ${intelligence.wallet_permission.decision}`}>{intelligence.wallet_permission.decision}</div>
              <p>{intelligence.summary}</p>
              <p>{intelligence.wallet_permission.reason}</p>
              <Facts
                compact
                items={[
                  ["Риск", intelligence.risk_assessment.risk_level],
                  ["Лимит", formatUsd(intelligence.wallet_permission.recommended_limit_usd)],
                  ["Можно арендовать", intelligence.marketplace_verdict.can_be_rented ? "да" : "нет"],
                ]}
              />
            </>
          ) : <p className="empty-state">Intelligence появится после Verify Wallet.</p>}
        </Panel>

        {verified && (
          <Panel title="Настройка автоматизации" wide>
            <div className="setup-summary">
              <Facts
                compact
                items={[
                  ["Agent ID", String(agentId)],
                  ["Wallet", walletAddress],
                  ["Automation", automationEnabled ? "Automation Enabled" : policy?.automation_enabled ? "policy saved" : "off"],
                  ["Delegation", policy?.delegation_status ?? "none"],
                  ["Risk decision", intelligence?.wallet_permission.decision ?? "unknown"],
                  ["Recommended limit", formatUsd(intelligence?.wallet_permission.recommended_limit_usd ?? 0)],
                ]}
              />
            </div>

            <div className="preset-row" role="group" aria-label="Automation presets">
              <button type="button" className={preset === "safe" ? "selected" : ""} onClick={() => applyPreset("safe")}>Safe</button>
              <button type="button" className={preset === "balanced" ? "selected" : ""} onClick={() => applyPreset("balanced")}>Balanced</button>
              <button type="button" className={preset === "custom" ? "selected" : ""} onClick={() => applyPreset("custom")}>Custom</button>
            </div>

            <div className="form-grid">
              <label className="check-row">
                <input type="checkbox" checked={policyForm.automation_enabled} onChange={(event) => updatePolicyField("automation_enabled", event.target.checked)} />
                automation_enabled
              </label>
              <label>mode
                <select value={policyForm.mode} onChange={(event) => updatePolicyField("mode", event.target.value as AutomationMode)}>
                  <option value="manual">manual</option>
                  <option value="semi_auto">semi_auto</option>
                  <option value="full_auto">full_auto</option>
                </select>
              </label>
              <TextInput label="max_tx_value_usd" value={policyForm.max_tx_value_usd} onChange={(value) => updatePolicyField("max_tx_value_usd", value)} />
              <TextInput label="daily_limit_usd" value={policyForm.daily_limit_usd} onChange={(value) => updatePolicyField("daily_limit_usd", value)} />
              <TextInput label="max_transactions_per_hour" value={policyForm.max_transactions_per_hour} onChange={(value) => updatePolicyField("max_transactions_per_hour", value)} />
              <TextInput label="min_native_balance_wei" value={policyForm.min_native_balance_wei} onChange={(value) => updatePolicyField("min_native_balance_wei", value)} />
              <TextInput label="require_confirmation_above_usd" value={policyForm.require_confirmation_above_usd} onChange={(value) => updatePolicyField("require_confirmation_above_usd", value)} />
              <label className="check-row">
                <input type="checkbox" checked={policyForm.emergency_stop} onChange={(event) => updatePolicyField("emergency_stop", event.target.checked)} />
                emergency_stop
              </label>
              <TextArea label="allowed_chain_ids" value={policyForm.allowed_chain_ids} onChange={(value) => updatePolicyField("allowed_chain_ids", value)} />
              <TextArea label="allowed_tokens" value={policyForm.allowed_tokens} onChange={(value) => updatePolicyField("allowed_tokens", value)} />
              <TextArea label="allowed_recipients" value={policyForm.allowed_recipients} onChange={(value) => updatePolicyField("allowed_recipients", value)} />
              <TextArea label="allowed_actions" value={policyForm.allowed_actions} onChange={(value) => updatePolicyField("allowed_actions", value)} />
            </div>

            <div className="button-row">
              <button type="button" onClick={loadPolicy} disabled={busy || !agentId}>Load Policy</button>
              <button type="button" className="primary" onClick={enableAutomation} disabled={!canEnableAutomation}>Enable Automation / Включить автоматизацию</button>
              <button type="button" onClick={confirmTestDelegation} disabled={busy || !agentId}>Confirm Test Delegation</button>
            </div>

            <p className={automationEnabled ? "alert ok" : "alert"}>
              {automationEnabled
                ? "Automation Enabled: delegation active, действия всё равно проходят через policy engine и лимиты."
                : "Для полной автоматизации нужен MetaMask Smart Account / Delegation. Обычный MetaMask EOA не может автоматически подтверждать транзакции."}
            </p>
            {smartAccountMessage && <p className="hint">{smartAccountMessage}</p>}
            {delegationRequest && <JsonBlock title="Delegation request" value={delegationRequest} />}
          </Panel>
        )}

        {verified && (
          <Panel title="Тест автоматического действия" wide>
            <div className="form-grid">
              <TextInput label="action_type" value={actionForm.action_type} onChange={(value) => setActionForm({ ...actionForm, action_type: value })} />
              <TextInput label="recipient address" value={actionForm.recipient} onChange={(value) => setActionForm({ ...actionForm, recipient: value })} />
              <TextInput label="token" value={actionForm.token} onChange={(value) => setActionForm({ ...actionForm, token: value })} placeholder="пусто для NATIVE" />
              <TextInput label="value_wei" value={actionForm.value_wei} onChange={(value) => setActionForm({ ...actionForm, value_wei: value })} />
              <TextInput label="value_usd" value={actionForm.value_usd} onChange={(value) => setActionForm({ ...actionForm, value_usd: value })} />
              <TextInput label="chain_id" value={actionForm.chain_id} onChange={(value) => setActionForm({ ...actionForm, chain_id: value })} />
              <TextInput label="reason" value={actionForm.reason} onChange={(value) => setActionForm({ ...actionForm, reason: value })} />
            </div>

            <div className="button-row">
              <button type="button" onClick={evaluateAction} disabled={busy || !agentId}>Evaluate Action</button>
              <button type="button" className="primary" onClick={runAutomatedAction} disabled={busy || !agentId}>Run Automated Action</button>
              {automatedResult?.requires_user_confirmation && (
                <button type="button" onClick={sendWithMetaMask} disabled={busy}>Send with MetaMask</button>
              )}
            </div>

            {evaluation && <Evaluation value={evaluation} />}
            {txHash && <p className="alert ok">txHash: {txHash}</p>}
            {automatedResult && <JsonBlock title="Automated response" value={automatedResult} />}
          </Panel>
        )}
      </section>
    </main>
  );
}

function Panel({ title, wide, children }: { title: string; wide?: boolean; children: ReactNode }) {
  return <article className={`panel ${wide ? "wide" : ""}`}><h2>{title}</h2>{children}</article>;
}

function TextInput({ label, value, onChange, placeholder }: { label: string; value: string; onChange(value: string): void; placeholder?: string }) {
  return <label>{label}<input value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} /></label>;
}

function TextArea({ label, value, onChange }: { label: string; value: string; onChange(value: string): void }) {
  return <label>{label}<textarea value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function Facts({ items, compact }: { items: Array<[string, string]>; compact?: boolean }) {
  return <dl className={`facts ${compact ? "compact" : ""}`}>{items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

function JsonBlock({ title, value }: { title: string; value: unknown }) {
  return <details className="json-block"><summary>{title}</summary><pre>{JSON.stringify(value, null, 2)}</pre></details>;
}

function Evaluation({ value }: { value: AutomationEvaluation }) {
  return (
    <div className="evaluation">
      <strong>{value.allowed ? "Разрешено" : "Заблокировано"}</strong>
      <span>confirmation: {String(value.requires_user_confirmation)}</span>
      <span>auto: {String(value.can_auto_execute)}</span>
      <span>delegation_required: {String(value.delegation_required)}</span>
      <p>{value.reason}</p>
      {value.violations.length > 0 && <ul>{value.violations.map((item) => <li key={item}>{item}</li>)}</ul>}
    </div>
  );
}

async function getJson<TResponse>(path: string): Promise<TResponse> {
  const response = await fetch(`${API_BASE}${path}`);
  return parseResponse<TResponse>(response);
}

async function postJson<TResponse>(path: string, body: object): Promise<TResponse> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseResponse<TResponse>(response);
}

async function putJson<TResponse>(path: string, body: object): Promise<TResponse> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseResponse<TResponse>(response);
}

async function parseResponse<TResponse>(response: Response): Promise<TResponse> {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "Запрос к backend завершился ошибкой";
    throw new Error(detail);
  }
  return data as TResponse;
}

function policyToForm(policy: AutomationPolicy): PolicyForm {
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

function buildPolicyPayload(form: PolicyForm) {
  return {
    automation_enabled: form.automation_enabled,
    mode: form.mode,
    max_tx_value_usd: Number(form.max_tx_value_usd),
    daily_limit_usd: Number(form.daily_limit_usd),
    max_transactions_per_hour: Number(form.max_transactions_per_hour),
    min_native_balance_wei: form.min_native_balance_wei,
    require_confirmation_above_usd: Number(form.require_confirmation_above_usd),
    allowed_chain_ids: splitList(form.allowed_chain_ids).map((item) => Number(item)).filter((item) => Number.isFinite(item)),
    allowed_tokens: splitList(form.allowed_tokens),
    allowed_recipients: splitList(form.allowed_recipients),
    allowed_actions: splitList(form.allowed_actions),
    emergency_stop: form.emergency_stop,
  };
}

function buildActionPayload(form: ActionForm) {
  return {
    action_type: form.action_type,
    to_address: form.recipient,
    token_address: form.token || null,
    value_wei: form.value_wei,
    value_usd: Number(form.value_usd),
    chain_id: Number(form.chain_id),
    reason: form.reason,
    metadata: { source: "frontend_minimal_automation_ux" },
  };
}

function splitList(value: string) {
  return value.split(/[\n,]+/).map((item) => item.trim()).filter(Boolean);
}

function shortAddress(address: string): string {
  if (address.length <= 12) return address;
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("ru-RU", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(value);
}

function readableError(error: unknown): string {
  const maybe = error as { code?: number; message?: string };
  const message = maybe?.message ?? String(error);
  const lower = message.toLowerCase();
  if (maybe?.code === 4001 || lower.includes("user rejected") || lower.includes("rejected")) {
    return "Пользователь отклонил запрос в MetaMask.";
  }
  if (lower.includes("failed to fetch")) {
    return "Backend недоступен. Запустите uvicorn app.main:app --reload на http://127.0.0.1:8000.";
  }
  if (lower.includes("insufficient funds")) {
    return "Недостаточно средств для газа или суммы транзакции.";
  }
  if (lower.includes("chain")) {
    return `Проверьте сеть MetaMask. Текущий/ожидаемый Chain ID должен совпадать с настройками действия.`;
  }
  return message;
}
