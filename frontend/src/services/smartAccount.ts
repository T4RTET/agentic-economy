type SmartAccountConfig = {
  chainId: number;
  chainName: string;
  rpcUrl: string;
  bundlerRpcUrl: string;
};

type SmartAccountConnection = {
  smartAccountAddress: string;
  chainId: number;
  status: "created" | "connected";
  note: string;
};

type CreateSmartAccountParams = {
  ownerAddress: string;
};

type DelegationParams = {
  smartAccountAddress: string;
  ownerAddress: string;
  policyScope: Record<string, unknown>;
  backendRequest: Record<string, unknown>;
};

type DelegationResult = {
  smartAccountAddress: string;
  delegationId: string;
  delegationScope: Record<string, unknown>;
  status: "active";
};

type SmartAccountExecutionResult = {
  userOperationHash: string;
  txHash?: string;
  status: "submitted" | "confirmed";
  raw?: unknown;
};

type SmartAccountExecutionPayload = {
  smart_account_address?: string;
  call?: {
    to?: string;
    value?: string;
    chainId?: string;
    data?: string;
    token?: string;
  };
};

const DEFAULT_CHAIN_ID = 11155111;
const SUPPORTED_CHAIN_ERROR = "Unsupported Smart Account chain. Add this chain to smartAccount.ts.";

declare global {
  interface Window {
    ethereum?: {
      request: (args: { method: string; params?: unknown[] | Record<string, unknown> }) => Promise<unknown>;
    };
  }
}

type EvmAddress = `0x${string}`;
type HexString = `0x${string}`;

function assertEvmAddress(address: string, label: string): EvmAddress {
  if (!/^0x[a-fA-F0-9]{40}$/.test(address)) {
    throw new Error(`${label} must be a valid EVM address.`);
  }

  return address as EvmAddress;
}

function assertHex(value: string, label: string): HexString {
  if (!/^0x[a-fA-F0-9]*$/.test(value)) {
    throw new Error(`${label} must be a hex string.`);
  }

  return value as HexString;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function isSmartAccountConfigured(): boolean {
  return Boolean(import.meta.env.VITE_CHAIN_ID && isRpcUrlConfigured() && isBundlerRpcUrlConfigured());
}

export function isSmartAccountAvailable(): boolean {
  return isSmartAccountConfigured() && Boolean(window.ethereum);
}

export function isRpcUrlConfigured(): boolean {
  return Boolean(String(import.meta.env.VITE_RPC_URL || "").trim());
}

export function isBundlerRpcUrlConfigured(): boolean {
  return Boolean(String(import.meta.env.VITE_BUNDLER_RPC_URL || "").trim());
}

export function getSmartAccountConfig(): SmartAccountConfig {
  const rpcUrl = String(import.meta.env.VITE_RPC_URL || "").trim();
  const bundlerRpcUrl = String(import.meta.env.VITE_BUNDLER_RPC_URL || "").trim();
  const chainId = Number(import.meta.env.VITE_CHAIN_ID ?? DEFAULT_CHAIN_ID);
  const chainName = String(import.meta.env.VITE_CHAIN_NAME || "Sepolia");

  if (!rpcUrl) {
    throw new Error("VITE_RPC_URL is missing. Add RPC URL to frontend/.env.");
  }
  if (!bundlerRpcUrl) {
    throw new Error("VITE_BUNDLER_RPC_URL is missing. Add Bundler RPC URL to frontend/.env.");
  }
  if (!Number.isFinite(chainId)) {
    throw new Error("VITE_CHAIN_ID must be a valid numeric chain id.");
  }
  if (chainId !== DEFAULT_CHAIN_ID) {
    console.warn("Current .env is configured for Sepolia chain id 11155111.");
  }

  return { chainId, chainName, rpcUrl, bundlerRpcUrl };
}

export async function getSupportedChain(chainId = Number(import.meta.env.VITE_CHAIN_ID ?? DEFAULT_CHAIN_ID)) {
  const { arbitrumSepolia, baseSepolia, optimismSepolia, polygonAmoy, sepolia } = await import("viem/chains");
  const chains = [sepolia, baseSepolia, arbitrumSepolia, optimismSepolia, polygonAmoy];
  const chain = chains.find((item) => item.id === chainId);
  if (!chain) {
    throw new Error(SUPPORTED_CHAIN_ERROR);
  }
  return chain;
}

export async function createSmartAccountClients() {
  const config = getSmartAccountConfig();
  const { createPublicClient, http } = await import("viem");
  const { createBundlerClient } = await import("viem/account-abstraction");
  const chain = await getSupportedChain(config.chainId);

  return {
    config,
    chain,
    publicClient: createPublicClient({ chain, transport: http(config.rpcUrl) }),
    bundlerClient: createBundlerClient({ chain, transport: http(config.bundlerRpcUrl) }),
  };
}

async function getConnectedOwnerAddress(expectedAddress?: string): Promise<EvmAddress> {
  if (!window.ethereum) {
    throw new Error("MetaMask is required to create or connect a Smart Account.");
  }

  const accountsResult = await window.ethereum.request({ method: "eth_requestAccounts" });
  const accounts = Array.isArray(accountsResult) ? accountsResult.map(String) : [];
  const connectedAddress = accounts[0];
  if (!connectedAddress) {
    throw new Error("MetaMask did not return a connected account.");
  }

  if (expectedAddress) {
    const expected = assertEvmAddress(expectedAddress, "Connected wallet address");
    const matchingAccount = accounts.find((account) => account.toLowerCase() === expected.toLowerCase());
    if (!matchingAccount) {
      throw new Error("Connected MetaMask account does not match the verified wallet.");
    }
    return assertEvmAddress(matchingAccount, "Connected MetaMask account");
  }

  return assertEvmAddress(connectedAddress, "Connected MetaMask account");
}

async function buildMetaMaskSmartAccount(ownerAddress?: string) {
  const connectedOwner = await getConnectedOwnerAddress(ownerAddress);
  const { chain, config, publicClient, bundlerClient } = await createSmartAccountClients();
  const { createWalletClient, custom } = await import("viem");
  const { Implementation, toMetaMaskSmartAccount } = await import("@metamask/smart-accounts-kit");

  const walletClient = createWalletClient({
    account: connectedOwner,
    chain,
    transport: custom(window.ethereum!),
  });

  try {
    const smartAccount = await toMetaMaskSmartAccount({
      client: publicClient,
      implementation: Implementation.Hybrid,
      deployParams: [connectedOwner, [], [], []],
      deploySalt: "0x",
      signer: { walletClient },
    } as never);

    return { smartAccount, connectedOwner, config, publicClient, bundlerClient };
  } catch (error) {
    const message = errorMessage(error);
    if (message.toLowerCase().includes("signer") || message.toLowerCase().includes("walletclient")) {
      throw new Error("MetaMask signer adapter is required for real Smart Account creation. User private keys are not allowed.");
    }
    throw new Error(`MetaMask Smart Account creation failed: ${message}`);
  }
}

export async function createOrConnectSmartAccount(params: CreateSmartAccountParams): Promise<SmartAccountConnection> {
  if (!params.ownerAddress) {
    throw new Error("Connected wallet address is required to create a Smart Account.");
  }

  const { config, smartAccount } = await buildMetaMaskSmartAccount(params.ownerAddress);
  const smartAccountAddress = assertEvmAddress(String(smartAccount.address), "Smart Account address");

  return {
    smartAccountAddress,
    chainId: config.chainId,
    status: "connected",
    note: "Smart Wallet created/connected. No seed phrase or private key was handled by this app.",
  };
}

export async function requestSmartAccountDelegation(params: DelegationParams): Promise<DelegationResult> {
  await createSmartAccountClients();
  const smartAccountAddress = assertEvmAddress(params.smartAccountAddress, "Smart Account address");
  const ownerAddress = assertEvmAddress(params.ownerAddress, "Owner address");

  if (!window.ethereum) {
    throw new Error("MetaMask is required to request Smart Account Delegation.");
  }

  const request = {
    ...params.backendRequest,
    smart_account_address: smartAccountAddress,
    owner_address: ownerAddress,
    policy_scope: params.policyScope,
  };

  try {
    const result = await window.ethereum.request({
      method: "wallet_requestExecutionPermissions",
      params: [request],
    });
    const delegationId = extractDelegationId(result);
    return {
      smartAccountAddress,
      delegationId,
      delegationScope: { ...params.policyScope, wallet_response: result },
      status: "active",
    };
  } catch (firstError) {
    try {
      const result = await window.ethereum.request({
        method: "wallet_grantPermissions",
        params: [request],
      });
      const delegationId = extractDelegationId(result);
      return {
        smartAccountAddress,
        delegationId,
        delegationScope: { ...params.policyScope, wallet_response: result },
        status: "active",
      };
    } catch (secondError) {
      const firstMessage = errorMessage(firstError);
      const secondMessage = errorMessage(secondError);
      if (firstMessage.includes("User rejected") || secondMessage.includes("User rejected")) {
        throw new Error("User rejected transaction or permission request.");
      }
      throw new Error(
        `MetaMask Smart Account Delegation SDK is not connected yet. Use Confirm Test Delegation only for local backend tests. Details: ${secondMessage || firstMessage}`,
      );
    }
  }
}

export async function requestDelegation(params: DelegationParams): Promise<DelegationResult> {
  return requestSmartAccountDelegation(params);
}

export async function executeSmartAccountPayload(
  payload: Record<string, unknown>,
): Promise<SmartAccountExecutionResult> {
  const executionPayload = payload as SmartAccountExecutionPayload;
  const call = executionPayload.call;
  if (!call?.to || !call.value) {
    throw new Error("Smart Account payload is missing call.to or call.value.");
  }

  const { smartAccount, bundlerClient } = await buildMetaMaskSmartAccount();
  const expectedSmartAccount = executionPayload.smart_account_address;
  if (expectedSmartAccount && String(smartAccount.address).toLowerCase() !== expectedSmartAccount.toLowerCase()) {
    throw new Error("Connected Smart Account does not match backend automation policy.");
  }

  const calls = [
    {
      to: assertEvmAddress(call.to, "UserOperation call.to"),
      value: BigInt(call.value),
      data: call.data ? assertHex(call.data, "UserOperation call.data") : undefined,
    },
  ];

  try {
    const userOperationHash = String(
      await (bundlerClient as never as { sendUserOperation: (args: unknown) => Promise<unknown> }).sendUserOperation({
        account: smartAccount,
        calls,
      }),
    );

    const receipt = await waitForUserOperationReceipt(bundlerClient, userOperationHash);
    const txHash = extractTransactionHash(receipt);

    return {
      userOperationHash,
      txHash,
      status: txHash ? "confirmed" : "submitted",
      raw: receipt,
    };
  } catch (error) {
    throw new Error(`UserOperation failed: ${errorMessage(error)}`);
  }
}

function extractDelegationId(result: unknown): string {
  if (typeof result === "string" && result.trim()) {
    return result;
  }
  if (Array.isArray(result) && result.length > 0) {
    return extractDelegationId(result[0]);
  }
  if (result && typeof result === "object") {
    const record = result as Record<string, unknown>;
    const candidate = record.delegationId ?? record.id ?? record.context ?? record.permissionContext;
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate;
    }
  }
  return `metamask-delegation-${Date.now()}`;
}

async function waitForUserOperationReceipt(bundlerClient: unknown, userOperationHash: string): Promise<unknown> {
  const client = bundlerClient as {
    waitForUserOperationReceipt?: (args: { hash: string; timeout?: number }) => Promise<unknown>;
    getUserOperationReceipt?: (args: { hash: string }) => Promise<unknown>;
  };

  try {
    if (client.waitForUserOperationReceipt) {
      return await client.waitForUserOperationReceipt({ hash: userOperationHash, timeout: 30_000 });
    }
    if (client.getUserOperationReceipt) {
      return await client.getUserOperationReceipt({ hash: userOperationHash });
    }
  } catch {
    return undefined;
  }

  return undefined;
}

function extractTransactionHash(receipt: unknown): string | undefined {
  if (!receipt || typeof receipt !== "object") {
    return undefined;
  }

  const record = receipt as Record<string, unknown>;
  const nestedReceipt = record.receipt && typeof record.receipt === "object" ? (record.receipt as Record<string, unknown>) : {};
  const candidate = record.transactionHash ?? nestedReceipt.transactionHash;
  return typeof candidate === "string" ? candidate : undefined;
}
