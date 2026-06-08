import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import {
  createOrConnectSmartAccount,
  executeSmartAccountPayload,
  isBundlerRpcUrlConfigured,
  isRpcUrlConfigured,
  isSmartAccountAvailable,
  isSmartAccountConfigured,
  requestSmartAccountDelegation,
} from "./services/smartAccount";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";
const DEFAULT_CHAIN_ID = Number(import.meta.env.VITE_CHAIN_ID ?? "11155111");
const AGENT_NAME = import.meta.env.VITE_AGENT_NAME ?? "My MetaMask Test Agent";
const AGENT_TYPE = import.meta.env.VITE_AGENT_TYPE ?? "wallet-linked-agent";
const DEFAULT_RECIPIENT_ADDRESS = "0x000000000000000000000000000000000000dEaD";

type EthereumProvider = {
  request(args: { method: string; params?: unknown[] | object }): Promise<unknown>;
  on?(event: "accountsChanged" | "chainChanged", handler: (value: string[] | string) => void): void;
  removeListener?(event: "accountsChanged" | "chainChanged", handler: (value: string[] | string) => void): void;
};

declare global {
  interface Window {
    ethereum?: EthereumProvider;
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

type RecordResponse = {
  event: AgentEvent;
  passport: AgentPassport;
  intelligence: IntelligenceReport;
};

type AutomationMode = "manual" | "semi_auto" | "full_auto";
type AutomationPreset = "safe" | "balanced" | "custom";

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

type PolicyDraft = {
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

type ActionDraft = {
  action_type: string;
  recipient: string;
  value_wei: string;
  value_usd: string;
  chain_id: string;
  reason: string;
};

const safePreset: PolicyDraft = {
  mode: "semi_auto",
  max_tx_value_usd: "1",
  daily_limit_usd: "5",
  max_transactions_per_hour: "1",
  min_native_balance_wei: "100000000000000000",
  require_confirmation_above_usd: "1",
  allowed_chain_ids: String(DEFAULT_CHAIN_ID),
  allowed_tokens: "NATIVE",
  allowed_recipients: DEFAULT_RECIPIENT_ADDRESS,
  allowed_actions: "native_transfer",
  emergency_stop: false,
};

const balancedPreset: PolicyDraft = {
  mode: "semi_auto",
  max_tx_value_usd: "5",
  daily_limit_usd: "20",
  max_transactions_per_hour: "3",
  min_native_balance_wei: "100000000000000000",
  require_confirmation_above_usd: "5",
  allowed_chain_ids: String(DEFAULT_CHAIN_ID),
  allowed_tokens: "NATIVE",
  allowed_recipients: DEFAULT_RECIPIENT_ADDRESS,
  allowed_actions: "native_transfer",
  emergency_stop: false,
};

const defaultAction: ActionDraft = {
  action_type: "native_transfer",
  recipient: DEFAULT_RECIPIENT_ADDRESS,
  value_wei: "1000000000000000",
  value_usd: "1",
  chain_id: String(DEFAULT_CHAIN_ID),
  reason: "Тестовое автоматическое действие агента",
};

function App() {
  const [walletAddress, setWalletAddress] = useState("");
  const [chainId, setChainId] = useState<number | null>(null);
  const [verified, setVerified] = useState(false);
  const [agentId, setAgentId] = useState<number | null>(null);
  const [passport, setPassport] = useState<AgentPassport | null>(null);
  const [intelligence, setIntelligence] = useState<IntelligenceReport | null>(null);
  const [automationPolicy, setAutomationPolicy] = useState<AutomationPolicy | null>(null);
  const [smartAccountAddress, setSmartAccountAddress] = useState("");
  const [selectedPreset, setSelectedPreset] = useState<AutomationPreset>("safe");
  const [policyDraft, setPolicyDraft] = useState<PolicyDraft>(safePreset);
  const [delegationRequest, setDelegationRequest] = useState<DelegationRequest | null>(null);
  const [automationEvaluation, setAutomationEvaluation] = useState<AutomationEvaluation | null>(null);
  const [automatedResult, setAutomatedResult] = useState<AutomatedTransactionResponse | null>(null);
  const [actionDraft, setActionDraft] = useState<ActionDraft>(defaultAction);
  const [txHash, setTxHash] = useState("");
  const [userOperationHash, setUserOperationHash] = useState("");
  const [status, setStatus] = useState("Готово");
  const [error, setError] = useState("");
  const [busyAction, setBusyAction] = useState("");

  const isAutomationEnabled = Boolean(automationPolicy?.automation_enabled && automationPolicy.delegation_status === "active");
  const walletDecision = intelligence?.wallet_permission.decision ?? "нет данных";
  const smartAccountReady = useMemo(() => isSmartAccountAvailable(), []);
  const smartAccountConfigured = useMemo(() => isSmartAccountConfigured(), []);
  const rpcUrlConfigured = useMemo(() => isRpcUrlConfigured(), []);
  const bundlerRpcUrlConfigured = useMemo(() => isBundlerRpcUrlConfigured(), []);
  const canCreateSmartAccountAutomation = Boolean(
    walletAddress && verified && agentId && intelligence?.wallet_permission.decision !== "deny" && !busyAction,
  );
  const canEnableAutomation = Boolean(canCreateSmartAccountAutomation && smartAccountAddress);

  useEffect(() => {
    if (!window.ethereum?.on) return;

    const onAccountsChanged = (value: string[] | string) => {
      const accounts = Array.isArray(value) ? value : [];
      setWalletAddress(accounts[0] ?? "");
      resetAgentState();
    };

    const onChainChanged = (value: string[] | string) => {
      if (typeof value === "string") {
        const nextChainId = Number.parseInt(value, 16);
        setChainId(nextChainId);
        setPolicyDraft((current) => ({ ...current, allowed_chain_ids: String(nextChainId) }));
        setActionDraft((current) => ({ ...current, chain_id: String(nextChainId) }));
      }
    };

    window.ethereum.on("accountsChanged", onAccountsChanged);
    window.ethereum.on("chainChanged", onChainChanged);

    return () => {
      window.ethereum?.removeListener?.("accountsChanged", onAccountsChanged);
      window.ethereum?.removeListener?.("chainChanged", onChainChanged);
    };
  }, []);

  async function connectMetaMask() {
    await run("Подключаю MetaMask", async () => {
      if (!window.ethereum) {
        throw new Error("MetaMask не установлен. Установите расширение браузера.");
      }
      const accounts = (await window.ethereum.request({ method: "eth_requestAccounts" })) as string[];
      const chainHex = (await window.ethereum.request({ method: "eth_chainId" })) as string;
      const nextWallet = accounts[0] ?? "";
      const nextChainId = Number.parseInt(chainHex, 16);
      setWalletAddress(nextWallet);
      setChainId(nextChainId);
      setPolicyDraft((current) => ({ ...current, allowed_chain_ids: String(nextChainId) }));
      setActionDraft((current) => ({ ...current, chain_id: String(nextChainId) }));
      setStatus("MetaMask подключён");
    });
  }

  async function verifyWallet() {
    await run("Проверяю владение кошельком", async () => {
      requireWallet();
      const activeChainId = requireChainId();
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

      const [nextIntelligence, nextPolicy] = await Promise.all([
        apiGet<IntelligenceReport>(`/agents/${nextAgentId}/intelligence`),
        apiGet<AutomationPolicy>(`/agents/${nextAgentId}/automation-policy`),
      ]);
      setIntelligence(nextIntelligence);
      setAutomationPolicy(nextPolicy);
      setSmartAccountAddress(nextPolicy.smart_account_address ?? "");
      if (nextPolicy.automation_enabled) {
        setPolicyDraft(policyToDraft(nextPolicy, activeChainId));
        setSelectedPreset("custom");
      } else {
        setPolicyDraft({ ...safePreset, allowed_chain_ids: String(activeChainId) });
        setSelectedPreset("safe");
      }
      setStatus("Кошелёк подтверждён, агент загружен");
    });
  }

  async function loadPassportAndIntelligence() {
    await run("Обновляю паспорт и intelligence", async () => {
      const id = requireAgentId();
      const [nextPassport, nextIntelligence, nextPolicy] = await Promise.all([
        apiGet<AgentPassport>(`/agents/${id}/passport`),
        apiGet<IntelligenceReport>(`/agents/${id}/intelligence`),
        apiGet<AutomationPolicy>(`/agents/${id}/automation-policy`),
      ]);
      setPassport(nextPassport);
      setIntelligence(nextIntelligence);
      setAutomationPolicy(nextPolicy);
      setSmartAccountAddress(nextPolicy.smart_account_address ?? "");
      setStatus("Данные агента обновлены");
    });
  }

  function applyPreset(preset: AutomationPreset) {
    setSelectedPreset(preset);
    if (preset === "custom") return;

    const base = preset === "safe" ? safePreset : balancedPreset;
    setPolicyDraft({
      ...base,
      allowed_chain_ids: policyDraft.allowed_chain_ids || String(chainId ?? DEFAULT_CHAIN_ID),
      allowed_recipients: policyDraft.allowed_recipients || actionDraft.recipient,
    });
  }

  async function createSmartWallet() {
    await run("Создаю Smart Wallet", async () => {
      requireWallet();
      const id = requireAgentId();
      const activeChainId = requireChainId();
      if (intelligence?.wallet_permission.decision === "deny") {
        throw new Error("Intelligence вернул deny: автоматизацию нельзя включить для этого агента.");
      }

      const smartWallet = await createOrConnectSmartAccount({ ownerAddress: walletAddress });
      setSmartAccountAddress(smartWallet.smartAccountAddress);

      const loadedPolicy = await apiGet<AutomationPolicy>(`/agents/${id}/automation-policy`);
      const draftToSave = loadedPolicy.automation_enabled
        ? policyToDraft(loadedPolicy, activeChainId)
        : { ...safePreset, allowed_chain_ids: String(activeChainId), allowed_recipients: DEFAULT_RECIPIENT_ADDRESS };
      if (!loadedPolicy.automation_enabled) {
        setSelectedPreset("safe");
        setPolicyDraft(draftToSave);
      }

      const savedPolicy = await apiPut<AutomationPolicy>(
        `/agents/${id}/automation-policy`,
        buildPolicyPayload(draftToSave, smartWallet.smartAccountAddress),
      );
      setAutomationPolicy(savedPolicy);
      setSmartAccountAddress(savedPolicy.smart_account_address ?? smartWallet.smartAccountAddress);
      setStatus("Smart Wallet created/connected. Automation policy saved.");
    });
  }

  async function enableAutomation() {
    await run("Включаю автоматизацию", async () => {
      requireWallet();
      const id = requireAgentId();
      if (!smartAccountAddress) {
        throw new Error("Сначала нажмите Create Smart Wallet.");
      }
      if (intelligence?.wallet_permission.decision === "deny") {
        throw new Error("Intelligence вернул deny: автоматизацию нельзя включить для этого агента.");
      }

      const currentPolicy = automationPolicy ?? (await apiGet<AutomationPolicy>(`/agents/${id}/automation-policy`));
      if (!currentPolicy.automation_enabled) {
        const activeChainId = requireChainId();
        const savedPolicy = await apiPut<AutomationPolicy>(
          `/agents/${id}/automation-policy`,
          buildPolicyPayload({ ...safePreset, allowed_chain_ids: String(activeChainId) }, smartAccountAddress),
        );
        setAutomationPolicy(savedPolicy);
      }
      const request = await apiPost<DelegationRequest>(`/agents/${id}/automation/delegation/request`, {});
      setDelegationRequest(request);

      try {
        const delegation = await requestSmartAccountDelegation({
          smartAccountAddress,
          ownerAddress: walletAddress,
          policyScope: request.policy_scope,
          backendRequest: request.request,
        });
        await confirmDelegationWithMetadata(smartAccountAddress, delegation.delegationId, delegation.delegationScope);
        const nextPolicy = await apiGet<AutomationPolicy>(`/agents/${id}/automation-policy`);
        setAutomationPolicy(nextPolicy);
        setStatus("Automation Enabled");
      } catch (smartAccountError) {
        setStatus(
          `${readableError(smartAccountError)} Для настоящей автоматизации нужен MetaMask Smart Account / Delegation. Сейчас можно использовать Confirm Test Delegation только для проверки backend-flow.`,
        );
      }
    });
  }

  async function confirmTestDelegation() {
    await run("Подтверждаю тестовую delegation", async () => {
      const id = requireAgentId();
      requireWallet();
      const request = delegationRequest ?? (await apiPost<DelegationRequest>(`/agents/${id}/automation/delegation/request`, {}));
      setDelegationRequest(request);
      const testSmartAccountAddress = smartAccountAddress || walletAddress;
      await confirmDelegationWithMetadata(
        testSmartAccountAddress,
        `local-test-delegation-${id}`,
        request.policy_scope,
      );
      const nextPolicy = await apiGet<AutomationPolicy>(`/agents/${id}/automation-policy`);
      setAutomationPolicy(nextPolicy);
      setSmartAccountAddress(nextPolicy.smart_account_address ?? testSmartAccountAddress);
      setStatus("Test delegation active");
    });
  }

  async function confirmDelegationWithMetadata(
    smartAccountAddress: string,
    delegationId: string,
    delegationScope: Record<string, unknown>,
  ) {
    const id = requireAgentId();
    const policy = await apiPost<AutomationPolicy>(`/agents/${id}/automation/delegation/confirm`, {
      smart_account_address: smartAccountAddress,
      delegation_id: delegationId,
      delegation_scope: delegationScope,
    });
    setAutomationPolicy(policy);
    setSmartAccountAddress(policy.smart_account_address ?? smartAccountAddress);
    setPolicyDraft(policyToDraft(policy, chainId ?? DEFAULT_CHAIN_ID));
  }

  async function evaluateAction() {
    await run("Проверяю действие по policy", async () => {
      const id = requireAgentId();
      const evaluation = await apiPost<AutomationEvaluation>(
        `/agents/${id}/automation-policy/evaluate`,
        buildActionPayload(actionDraft),
      );
      setAutomationEvaluation(evaluation);
      setStatus(evaluation.reason);
    });
  }

  async function runAutomatedAction() {
    await run("Запускаю автоматическое действие", async () => {
      const id = requireAgentId();
      const response = await apiPost<AutomatedTransactionResponse>(
        `/agents/${id}/transactions/execute-automated`,
        buildActionPayload(actionDraft),
      );
      setAutomatedResult(response);
      setAutomationEvaluation(response.evaluation);

      if (response.delegation_required) {
        setStatus("Enable Automation first.");
        return;
      }

      if (response.requires_user_confirmation) {
        setStatus("Нужно ручное подтверждение MetaMask");
        return;
      }

      if (response.smart_account_execution_payload) {
        try {
          const result = await executeSmartAccountPayload(response.smart_account_execution_payload);
          if (result.userOperationHash) {
            setUserOperationHash(result.userOperationHash);
            setStatus("UserOperation submitted");
          }
          if (result.txHash) {
            await recordAutomationTransaction(result.txHash, result.userOperationHash);
            setStatus("Transaction confirmed. Result recorded in passport.");
          } else if (result.userOperationHash) {
            setStatus("UserOperation submitted. Receipt not found yet. Check status later.");
          }
        } catch (smartAccountError) {
          setStatus(readableError(smartAccountError));
        }
      }
    });
  }

  async function sendAutomatedWithMetaMask() {
    await run("Отправляю через MetaMask", async () => {
      requireWallet();
      if (!automatedResult?.transaction_request) {
        throw new Error("Нет transaction_request для MetaMask.");
      }
      const sentHash = (await window.ethereum!.request({
        method: "eth_sendTransaction",
        params: [automatedResult.transaction_request],
      })) as string;
      await recordAutomationTransaction(sentHash, userOperationHash || undefined);
      setStatus("Транзакция отправлена и записана в паспорт");
    });
  }

  async function recordAutomationTransaction(nextTxHash: string, nextUserOperationHash?: string) {
    const id = requireAgentId();
    setTxHash(nextTxHash);
    const response = await apiPost<RecordResponse>(`/agents/${id}/transactions/record`, {
      tx_hash: nextTxHash,
      outcome: "success",
      value_usd: Number(actionDraft.value_usd),
      metadata: {
        source: "smart_account_user_operation",
        user_operation_hash: nextUserOperationHash,
        recipient: actionDraft.recipient,
        reason: actionDraft.reason,
      },
    });
    const nextPolicy = await apiGet<AutomationPolicy>(`/agents/${id}/automation-policy`);
    setPassport(response.passport);
    setIntelligence(response.intelligence);
    setAutomationPolicy(nextPolicy);
  }

  async function run(label: string, action: () => Promise<void>) {
    setBusyAction(label);
    setError("");
    try {
      await action();
    } catch (err) {
      setError(readableError(err));
    } finally {
      setBusyAction("");
    }
  }

  function resetAgentState() {
    setVerified(false);
    setAgentId(null);
    setPassport(null);
    setIntelligence(null);
    setAutomationPolicy(null);
    setSmartAccountAddress("");
    setDelegationRequest(null);
    setAutomationEvaluation(null);
    setAutomatedResult(null);
    setTxHash("");
    setUserOperationHash("");
  }

  function requireWallet() {
    if (!window.ethereum) {
      throw new Error("MetaMask не установлен. Установите расширение браузера.");
    }
    if (!walletAddress) {
      throw new Error("Сначала подключите MetaMask.");
    }
  }

  function requireChainId() {
    if (chainId === null) {
      throw new Error("Не удалось прочитать chain id из MetaMask.");
    }
    return chainId;
  }

  function requireAgentId() {
    if (!agentId) {
      throw new Error("Сначала подтвердите кошелёк.");
    }
    return agentId;
  }

  return (
    <main className="shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">Локальный тест AI-агента</p>
          <h1>Agent Reputation Passport + MetaMask</h1>
          <p className="muted">Сид-фраза и приватный ключ здесь не нужны и никогда не запрашиваются.</p>
        </div>
        <div className="header-actions">
          <button onClick={connectMetaMask} disabled={Boolean(busyAction)}>Подключить MetaMask</button>
          <button className="primary" onClick={verifyWallet} disabled={!walletAddress || Boolean(busyAction)}>
            Подтвердить кошелёк
          </button>
        </div>
      </header>

      {busyAction && <div className="alert busy">{busyAction}</div>}
      {error && <div className="alert error">{error}</div>}
      <div className="alert ok">{status}</div>

      <section className="grid">
        <Panel title="Кошелёк">
          <KeyValues
            items={[
              ["Backend URL", BACKEND_URL],
              ["Кошелёк", walletAddress || "Не подключён"],
              ["Chain ID", chainId === null ? "Неизвестно" : String(chainId)],
              ["Smart Account SDK", smartAccountReady ? "доступен" : "не подключён"],
              ["RPC URL configured", rpcUrlConfigured ? "true" : "false"],
              ["Bundler RPC URL configured", bundlerRpcUrlConfigured ? "true" : "false"],
            ]}
          />
        </Panel>

        <Panel title="Агент">
          <KeyValues
            items={[
              ["Кошелёк подтверждён", verified ? "true" : "false"],
              ["Agent ID", agentId ? String(agentId) : "нет"],
              ["Имя", passport?.agent.name ?? "нет"],
              ["Кошелёк владельца", passport?.agent.owner_wallet ?? "нет"],
            ]}
          />
          <button onClick={loadPassportAndIntelligence} disabled={!agentId || Boolean(busyAction)}>
            Обновить паспорт и intelligence
          </button>
        </Panel>

        <Panel title="Решение intelligence">
          {intelligence ? (
            <>
              <div className={`decision ${intelligence.wallet_permission.decision}`}>
                {intelligence.wallet_permission.decision}
              </div>
              <p>{intelligence.summary}</p>
              <KeyValues
                items={[
                  ["Risk", intelligence.risk_assessment.risk_level],
                  ["Рекомендованный лимит", `$${intelligence.wallet_permission.recommended_limit_usd}`],
                  ["Причина", intelligence.wallet_permission.reason],
                ]}
              />
            </>
          ) : (
            <p className="muted">Сначала нажмите «Подтвердить кошелёк».</p>
          )}
        </Panel>

        {verified && agentId && (
          <Panel title="Smart Wallet" wide>
            <div className="setup-summary">
              <KeyValues
                items={[
                  ["Connected wallet", walletAddress],
                  ["Agent ID", String(agentId)],
                  ["Current chain id", chainId === null ? "unknown" : String(chainId)],
                  ["Smart Account SDK", smartAccountReady ? "Available" : "Not connected"],
                  ["Smart Account config", smartAccountConfigured ? "RPC/Bundler configured" : "RPC/Bundler missing"],
                  ["RPC URL configured", rpcUrlConfigured ? "true" : "false"],
                  ["Bundler RPC URL configured", bundlerRpcUrlConfigured ? "true" : "false"],
                  ["Smart account address", smartAccountAddress || automationPolicy?.smart_account_address || "not created"],
                  ["Automation status", automationPolicy?.automation_enabled ? "enabled" : "disabled"],
                  ["Delegation status", automationPolicy?.delegation_status ?? "none"],
                  ["Mode", automationPolicy?.mode ?? policyDraft.mode],
                  ["Wallet decision", walletDecision],
                ]}
              />
            </div>

            <div className="preset-row" role="group" aria-label="Automation presets">
              <button className={selectedPreset === "safe" ? "selected" : ""} onClick={() => applyPreset("safe")}>
                Safe
              </button>
              <button className={selectedPreset === "balanced" ? "selected" : ""} onClick={() => applyPreset("balanced")}>
                Balanced
              </button>
              <button className={selectedPreset === "custom" ? "selected" : ""} onClick={() => applyPreset("custom")}>
                Custom
              </button>
            </div>

            <div className="form-grid">
              <label>
                Режим
                <select
                  value={policyDraft.mode}
                  disabled={selectedPreset !== "custom"}
                  onChange={(event) => setPolicyDraft({ ...policyDraft, mode: event.target.value as AutomationMode })}
                >
                  <option value="manual">manual</option>
                  <option value="semi_auto">semi_auto</option>
                  <option value="full_auto">full_auto</option>
                </select>
              </label>
              <NumberField
                label="Максимум за транзакцию, USD"
                value={policyDraft.max_tx_value_usd}
                disabled={selectedPreset !== "custom"}
                onChange={(value) => setPolicyDraft({ ...policyDraft, max_tx_value_usd: value })}
              />
              <NumberField
                label="Дневной лимит, USD"
                value={policyDraft.daily_limit_usd}
                disabled={selectedPreset !== "custom"}
                onChange={(value) => setPolicyDraft({ ...policyDraft, daily_limit_usd: value })}
              />
              <NumberField
                label="Максимум транзакций в час"
                value={policyDraft.max_transactions_per_hour}
                disabled={selectedPreset !== "custom"}
                onChange={(value) => setPolicyDraft({ ...policyDraft, max_transactions_per_hour: value })}
              />
              <NumberField
                label="Минимальный остаток native, wei"
                value={policyDraft.min_native_balance_wei}
                disabled={selectedPreset !== "custom"}
                onChange={(value) => setPolicyDraft({ ...policyDraft, min_native_balance_wei: value })}
              />
              <NumberField
                label="Подтверждать вручную выше, USD"
                value={policyDraft.require_confirmation_above_usd}
                disabled={selectedPreset !== "custom"}
                onChange={(value) => setPolicyDraft({ ...policyDraft, require_confirmation_above_usd: value })}
              />
              <label>
                Разрешённые chain IDs
                <textarea
                  value={policyDraft.allowed_chain_ids}
                  disabled={selectedPreset !== "custom"}
                  onChange={(event) => setPolicyDraft({ ...policyDraft, allowed_chain_ids: event.target.value })}
                />
              </label>
              <label>
                Разрешённые токены
                <textarea
                  value={policyDraft.allowed_tokens}
                  disabled={selectedPreset !== "custom"}
                  onChange={(event) => setPolicyDraft({ ...policyDraft, allowed_tokens: event.target.value })}
                />
              </label>
              <label>
                Разрешённые получатели
                <textarea
                  value={policyDraft.allowed_recipients}
                  disabled={selectedPreset !== "custom"}
                  onChange={(event) => setPolicyDraft({ ...policyDraft, allowed_recipients: event.target.value })}
                />
              </label>
              <label>
                Разрешённые действия
                <textarea
                  value={policyDraft.allowed_actions}
                  disabled={selectedPreset !== "custom"}
                  onChange={(event) => setPolicyDraft({ ...policyDraft, allowed_actions: event.target.value })}
                />
              </label>
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={policyDraft.emergency_stop}
                  disabled={selectedPreset !== "custom"}
                  onChange={(event) => setPolicyDraft({ ...policyDraft, emergency_stop: event.target.checked })}
                />
                Аварийная остановка
              </label>
            </div>

            <div className="button-row">
              <button className="primary" onClick={createSmartWallet} disabled={!canCreateSmartAccountAutomation}>
                Create Smart Wallet
              </button>
              <button onClick={enableAutomation} disabled={!canEnableAutomation}>
                Enable Automation
              </button>
              <button onClick={confirmTestDelegation} disabled={Boolean(busyAction) || !agentId}>
                Confirm Test Delegation
              </button>
            </div>

            <p className="warning">
              Only for local backend/UI testing. This is not a real on-chain Smart Account permission. Для настоящей
              автоматизации нужен MetaMask Smart Account / Delegation и заполненные VITE_RPC_URL/VITE_BUNDLER_RPC_URL.
            </p>
            {delegationRequest && <pre>{JSON.stringify(delegationRequest, null, 2)}</pre>}
          </Panel>
        )}

        {verified && agentId && (
          <Panel title="Smart Wallet Action Test" wide>
            <div className="form-grid">
              <label>
                Адрес получателя
                <input value={actionDraft.recipient} onChange={(event) => setActionDraft({ ...actionDraft, recipient: event.target.value })} />
              </label>
              <label>
                Значение, wei
                <input value={actionDraft.value_wei} onChange={(event) => setActionDraft({ ...actionDraft, value_wei: event.target.value })} />
              </label>
              <label>
                Сумма, USD
                <input value={actionDraft.value_usd} onChange={(event) => setActionDraft({ ...actionDraft, value_usd: event.target.value })} />
              </label>
              <label>
                Chain ID
                <input value={actionDraft.chain_id} onChange={(event) => setActionDraft({ ...actionDraft, chain_id: event.target.value })} />
              </label>
              <label>
                Тип действия
                <input value={actionDraft.action_type} onChange={(event) => setActionDraft({ ...actionDraft, action_type: event.target.value })} />
              </label>
              <label>
                Причина
                <input value={actionDraft.reason} onChange={(event) => setActionDraft({ ...actionDraft, reason: event.target.value })} />
              </label>
            </div>
            <div className="button-row">
              <button onClick={evaluateAction} disabled={Boolean(busyAction)}>Evaluate Automation</button>
              <button className="primary" onClick={runAutomatedAction} disabled={Boolean(busyAction)}>
                Run Automated Action
              </button>
              {automatedResult?.requires_user_confirmation && (
                <button onClick={sendAutomatedWithMetaMask} disabled={Boolean(busyAction)}>
                  Send with MetaMask
                </button>
              )}
            </div>
            <KeyValues items={[["userOperationHash", userOperationHash || "нет"], ["tx_hash", txHash || "нет"]]} />
            {automationEvaluation && <EvaluationView evaluation={automationEvaluation} />}
            {automatedResult?.smart_account_execution_payload && (
              <pre>{JSON.stringify(automatedResult.smart_account_execution_payload, null, 2)}</pre>
            )}
          </Panel>
        )}

        <Panel title="Паспорт и история" wide>
          {passport ? (
            <>
              <KeyValues
                items={[
                  ["Trust score", `${passport.reputation.trust_score}/100`],
                  ["Уровень риска", passport.reputation.risk_level],
                  ["Лимит кошелька", `$${passport.reputation.recommended_wallet_limit_usd}`],
                ]}
              />
              <History events={passport.actions_history} />
            </>
          ) : (
            <p className="muted">Паспорт появится после подтверждения кошелька.</p>
          )}
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

function NumberField({
  label,
  value,
  disabled,
  onChange,
}: {
  label: string;
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label>
      {label}
      <input value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function EvaluationView({ evaluation }: { evaluation: AutomationEvaluation }) {
  return (
    <div className="evaluation">
      <KeyValues
        items={[
          ["allowed", String(evaluation.allowed)],
          ["requires_user_confirmation", String(evaluation.requires_user_confirmation)],
          ["can_auto_execute", String(evaluation.can_auto_execute)],
          ["delegation_required", String(evaluation.delegation_required)],
          ["reason", evaluation.reason],
        ]}
      />
      {evaluation.violations.length > 0 && (
        <ul>
          {evaluation.violations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function History({ events }: { events: AgentEvent[] }) {
  if (!events.length) {
    return <p className="muted">Пока нет действий.</p>;
  }

  return (
    <ul className="history">
      {events.map((event) => (
        <li key={event.id}>
          <span>{event.title}</span>
          <span>{event.outcome}</span>
          {event.tx_hash && <code>{event.tx_hash}</code>}
        </li>
      ))}
    </ul>
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
    throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail ?? data));
  }
  return data as T;
}

function policyToDraft(policy: AutomationPolicy, fallbackChainId: number): PolicyDraft {
  return {
    mode: policy.mode,
    max_tx_value_usd: String(policy.max_tx_value_usd),
    daily_limit_usd: String(policy.daily_limit_usd),
    max_transactions_per_hour: String(policy.max_transactions_per_hour),
    min_native_balance_wei: policy.min_native_balance_wei,
    require_confirmation_above_usd: String(policy.require_confirmation_above_usd),
    allowed_chain_ids: policy.allowed_chain_ids.length ? policy.allowed_chain_ids.join(", ") : String(fallbackChainId),
    allowed_tokens: policy.allowed_tokens.length ? policy.allowed_tokens.join(", ") : "NATIVE",
    allowed_recipients: policy.allowed_recipients.length ? policy.allowed_recipients.join(", ") : DEFAULT_RECIPIENT_ADDRESS,
    allowed_actions: policy.allowed_actions.length ? policy.allowed_actions.join(", ") : "native_transfer",
    emergency_stop: policy.emergency_stop,
  };
}

function buildPolicyPayload(draft: PolicyDraft, nextSmartAccountAddress?: string) {
  return {
    automation_enabled: true,
    mode: draft.mode,
    max_tx_value_usd: Number(draft.max_tx_value_usd),
    daily_limit_usd: Number(draft.daily_limit_usd),
    max_transactions_per_hour: Number(draft.max_transactions_per_hour),
    min_native_balance_wei: draft.min_native_balance_wei,
    require_confirmation_above_usd: Number(draft.require_confirmation_above_usd),
    allowed_chain_ids: splitList(draft.allowed_chain_ids).map((item) => Number(item)),
    allowed_tokens: splitList(draft.allowed_tokens),
    allowed_recipients: splitList(draft.allowed_recipients),
    allowed_actions: splitList(draft.allowed_actions),
    emergency_stop: draft.emergency_stop,
    smart_account_address: nextSmartAccountAddress || null,
  };
}

function buildActionPayload(draft: ActionDraft) {
  return {
    action_type: draft.action_type,
    to_address: draft.recipient,
    token_address: null,
    value_wei: draft.value_wei,
    value_usd: Number(draft.value_usd),
    chain_id: Number(draft.chain_id),
    reason: draft.reason,
    metadata: {
      source: "frontend_minimal_automation_flow",
    },
  };
}

function splitList(value: string) {
  return value
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function readableError(error: unknown) {
  const maybe = error as { code?: number; message?: string };
  const message = maybe?.message ?? String(error);
  const lowerMessage = message.toLowerCase();
  if (maybe?.code === 4001 || lowerMessage.includes("user rejected")) {
    return "Пользователь отклонил запрос в MetaMask.";
  }
  if (lowerMessage.includes("failed to fetch")) {
    return "Backend недоступен. Запустите uvicorn app.main:app --reload.";
  }
  if (lowerMessage.includes("vite_rpc_url")) {
    return "RPC URL missing. Заполните VITE_RPC_URL в frontend/.env.";
  }
  if (lowerMessage.includes("vite_bundler_rpc_url")) {
    return "Bundler RPC URL missing. Заполните VITE_BUNDLER_RPC_URL в frontend/.env.";
  }
  if (lowerMessage.includes("unsupported smart account chain")) {
    return "Unsupported chain for Smart Account.";
  }
  if (lowerMessage.includes("signer adapter")) {
    return "SDK signer adapter missing. MetaMask signer adapter is required; private keys are not allowed.";
  }
  if (lowerMessage.includes("delegation") && lowerMessage.includes("required")) {
    return "Delegation is required.";
  }
  if (lowerMessage.includes("policy") && lowerMessage.includes("rejected")) {
    return "Policy rejected this action.";
  }
  if (lowerMessage.includes("useroperation")) {
    return "UserOperation failed.";
  }
  if (lowerMessage.includes("receipt not found")) {
    return "Receipt not found yet.";
  }
  if (lowerMessage.includes("smart account sdk") || lowerMessage.includes("sdk integration")) {
    return "Smart Account SDK is not connected yet.";
  }
  return message;
}

export default App;
