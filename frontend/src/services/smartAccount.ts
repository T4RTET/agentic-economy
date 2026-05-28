type DelegationParams = {
  agentId: number;
  walletAddress: string;
  policyScope: Record<string, unknown>;
  request: Record<string, unknown>;
};

type DelegationResult = {
  smartAccountAddress: string;
  delegationId: string;
  delegationScope: Record<string, unknown>;
};

type SmartAccountExecutionResult = {
  txHash?: string;
  raw?: unknown;
};

declare global {
  interface Window {
    ethereumSmartAccounts?: unknown;
  }
}

export function isSmartAccountAvailable(): boolean {
  return Boolean(window.ethereumSmartAccounts);
}

export async function requestSmartAccountDelegation(params: DelegationParams): Promise<DelegationResult> {
  void params;

  if (!isSmartAccountAvailable()) {
    throw new Error(
      "Для полной автоматизации нужен MetaMask Smart Account / Delegation. Обычный MetaMask-кошелёк не может автоматически подтверждать транзакции. Сейчас можно сохранить настройки и подтвердить delegation metadata в тестовом режиме.",
    );
  }

  throw new Error("MetaMask Smart Account SDK is not connected yet.");
}

export async function executeSmartAccountPayload(payload: Record<string, unknown>): Promise<SmartAccountExecutionResult> {
  void payload;

  if (!isSmartAccountAvailable()) {
    throw new Error("Smart Account SDK is not connected yet.");
  }

  throw new Error("Smart Account SDK is not connected yet.");
}
