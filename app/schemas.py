from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field, field_validator

from app.services.wallet_utils import is_non_negative_integer_string, normalize_wallet_address


AgentStatus = Literal["active", "paused", "retired"]
EventOutcome = Literal["success", "failed", "error"]
ComplaintSeverity = Literal["low", "medium", "high"]
ComplaintStatus = Literal["open", "confirmed", "dismissed"]
PricingModel = Literal["buy", "rent_hourly", "rent_daily", "per_task"]
ListingAvailability = Literal["available", "rented", "paused"]
RentalStatus = Literal["pending", "active", "completed", "disputed", "cancelled"]
WalletPermissionDecision = Literal["allow", "limit", "deny"]
RiskAssessmentConfidence = Literal["low", "medium", "high"]
AutomationMode = Literal["manual", "semi_auto", "full_auto"]
DelegationStatus = Literal["none", "requested", "active", "revoked", "expired"]
AutomationAttemptStatus = Literal["prepared", "requires_confirmation", "delegation_required", "executed", "rejected", "failed"]


class AgentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)
    agent_type: str = Field(min_length=2, max_length=80)
    owner_wallet: str = Field(min_length=6, max_length=120)
    chain_id: int = 5000
    status: AgentStatus = "active"


class WalletConnect(BaseModel):
    wallet_address: str = Field(min_length=6, max_length=120)
    chain_id: int = 5000
    agent_name: str | None = Field(default=None, min_length=2, max_length=120)
    agent_type: str = Field(default="wallet-linked-agent", min_length=2, max_length=80)


class WalletNonceRequest(BaseModel):
    wallet_address: str = Field(min_length=6, max_length=120)
    chain_id: int = 5000


class WalletNonceResponse(BaseModel):
    wallet_address: str
    chain_id: int
    nonce: str
    message: str
    expires_at: str


class WalletVerifyRequest(BaseModel):
    wallet_address: str = Field(min_length=6, max_length=120)
    chain_id: int = 5000
    message: str = Field(min_length=1)
    signature: str = Field(min_length=1)
    agent_name: str | None = Field(default=None, min_length=2, max_length=120)
    agent_type: str = Field(default="wallet-linked-agent", min_length=2, max_length=80)


class Agent(BaseModel):
    id: int
    name: str
    description: str
    agent_type: str
    owner_wallet: str
    chain_id: int
    status: AgentStatus
    created_at: str


class AgentEventCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    category: str = Field(min_length=2, max_length=80)
    outcome: EventOutcome
    value_usd: float = Field(default=0, ge=0)
    tx_hash: str | None = Field(default=None, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentEvent(BaseModel):
    id: int
    agent_id: int
    title: str
    category: str
    outcome: EventOutcome
    value_usd: float
    tx_hash: str | None
    metadata: dict[str, Any]
    created_at: str


class AutomationPolicy(BaseModel):
    id: int
    agent_id: int
    automation_enabled: bool
    mode: AutomationMode
    max_tx_value_usd: float
    daily_limit_usd: float
    max_transactions_per_hour: int
    min_native_balance_wei: str
    require_confirmation_above_usd: float
    allowed_chain_ids: list[int]
    allowed_tokens: list[str]
    allowed_recipients: list[str]
    allowed_actions: list[str]
    emergency_stop: bool
    smart_account_address: str | None = None
    delegation_id: str | None = None
    delegation_status: DelegationStatus
    delegation_scope: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class AutomationPolicyUpdate(BaseModel):
    automation_enabled: bool = False
    mode: AutomationMode = "manual"
    max_tx_value_usd: float = Field(default=0, ge=0)
    daily_limit_usd: float = Field(default=0, ge=0)
    max_transactions_per_hour: int = Field(default=0, ge=0)
    min_native_balance_wei: str = "0"
    require_confirmation_above_usd: float = Field(default=0, ge=0)
    allowed_chain_ids: list[int] = Field(default_factory=list)
    allowed_tokens: list[str] = Field(default_factory=list)
    allowed_recipients: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    emergency_stop: bool = False

    @field_validator("min_native_balance_wei")
    @classmethod
    def validate_min_native_balance(cls, value: str) -> str:
        return _validate_wei_string(value)

    @field_validator("allowed_chain_ids")
    @classmethod
    def validate_allowed_chain_ids(cls, values: list[int]) -> list[int]:
        if any(item <= 0 for item in values):
            raise ValueError("allowed_chain_ids must contain positive integers")
        return values

    @field_validator("allowed_tokens")
    @classmethod
    def validate_allowed_tokens(cls, values: list[str]) -> list[str]:
        return _normalize_token_list(values)

    @field_validator("allowed_recipients")
    @classmethod
    def validate_allowed_recipients(cls, values: list[str]) -> list[str]:
        return _normalize_address_list(values)


class AutomationActionRequest(BaseModel):
    action_type: str = Field(default="native_transfer", min_length=2, max_length=80)
    to_address: str = Field(validation_alias=AliasChoices("to_address", "recipient", "recipient_address"), min_length=6, max_length=120)
    token_address: str | None = Field(default=None, min_length=6, max_length=120)
    value_wei: str = Field(min_length=1, max_length=120)
    value_usd: float = Field(default=0, ge=0)
    chain_id: int = 5000
    reason: str = Field(default="Automated wallet action", max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    current_native_balance_wei: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("to_address")
    @classmethod
    def normalize_to_address(cls, value: str) -> str:
        return _normalize_address(value)

    @field_validator("token_address")
    @classmethod
    def normalize_token_address(cls, value: str | None) -> str | None:
        return _normalize_optional_address(value)

    @field_validator("value_wei")
    @classmethod
    def validate_value_wei(cls, value: str) -> str:
        return _validate_wei_string(value)

    @field_validator("current_native_balance_wei")
    @classmethod
    def validate_current_native_balance(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_wei_string(value)


class AutomationEvaluationResponse(BaseModel):
    allowed: bool
    requires_user_confirmation: bool
    can_auto_execute: bool
    delegation_required: bool
    reason: str
    violations: list[str]


class DelegationRequestResponse(BaseModel):
    agent_id: int
    delegation_status: DelegationStatus
    message: str
    policy_scope: dict[str, Any]
    request: dict[str, Any]


class DelegationConfirmRequest(BaseModel):
    smart_account_address: str = Field(min_length=6, max_length=120)
    delegation_id: str = Field(min_length=2, max_length=200)
    delegation_scope: dict[str, Any] = Field(default_factory=dict)

    @field_validator("smart_account_address")
    @classmethod
    def normalize_smart_account_address(cls, value: str) -> str:
        return _normalize_address(value)


class AutomatedTransactionRequest(AutomationActionRequest):
    pass


class AutomatedTransactionResponse(BaseModel):
    executed: bool = False
    requires_user_confirmation: bool = False
    delegation_required: bool = False
    status: AutomationAttemptStatus
    reason: str
    attempt_id: int
    transaction_request: dict[str, Any] | None = None
    smart_account_execution_payload: dict[str, Any] | None = None
    tx_hash: str | None = None
    evaluation: AutomationEvaluationResponse


class ComplaintCreate(BaseModel):
    reason: str = Field(min_length=4, max_length=1000)
    severity: ComplaintSeverity
    status: ComplaintStatus = "open"


class ComplaintUpdate(BaseModel):
    status: ComplaintStatus


class Complaint(BaseModel):
    id: int
    agent_id: int
    reason: str
    severity: ComplaintSeverity
    status: ComplaintStatus
    created_at: str


class Reputation(BaseModel):
    trust_score: int
    risk_level: Literal["Low", "Medium", "High"]
    recommended_wallet_limit_usd: int
    successful_volume_usd: float
    total_events: int
    complaint_count: int
    score_breakdown: dict[str, Any]


class MarketplaceListingCreate(BaseModel):
    pricing_model: PricingModel
    price_usd: float = Field(ge=0)
    price_token: str = Field(default="USD", min_length=2, max_length=24)
    availability: ListingAvailability = "available"
    capabilities: list[str] = Field(default_factory=list)
    terms: str = Field(default="", max_length=1000)


class MarketplaceListing(BaseModel):
    id: int
    agent_id: int
    pricing_model: PricingModel
    price_usd: float
    price_token: str
    availability: ListingAvailability
    capabilities: list[str]
    terms: str
    created_at: str
    updated_at: str


class MarketplaceStats(BaseModel):
    rentals_count: int
    completed_rentals: int
    disputed_rentals: int
    completion_rate: float


class MarketplaceInfo(BaseModel):
    listing: MarketplaceListing | None
    stats: MarketplaceStats


class MarketplaceCard(BaseModel):
    agent: Agent
    reputation: Reputation
    marketplace: MarketplaceInfo


class PassportAnalysis(BaseModel):
    summary: str
    strengths: list[str]
    risk_flags: list[str]
    recommendation: str


class RentalCreate(BaseModel):
    renter_wallet: str = Field(min_length=6, max_length=120)
    task_title: str = Field(min_length=2, max_length=160)
    task_description: str = Field(default="", max_length=1000)
    duration_hours: int = Field(default=1, gt=0, le=720)


class Rental(BaseModel):
    id: int
    listing_id: int
    agent_id: int
    renter_wallet: str
    task_title: str
    task_description: str
    duration_hours: int
    agreed_price_usd: float
    status: RentalStatus
    created_at: str
    completed_at: str | None


class AgentSummary(BaseModel):
    agent: Agent
    reputation: Reputation


class AgentPassport(BaseModel):
    agent: Agent
    reputation: Reputation
    marketplace: MarketplaceInfo
    analysis: PassportAnalysis
    actions_history: list[AgentEvent]
    complaints: list[Complaint]
    audit_log: list[dict[str, Any]]


class WalletVerifyResponse(BaseModel):
    verified: bool
    wallet_address: str
    chain_id: int
    passport: AgentPassport


class WalletPermissionReport(BaseModel):
    decision: WalletPermissionDecision
    recommended_limit_usd: int
    reason: str


class RiskAssessmentReport(BaseModel):
    risk_level: Literal["Low", "Medium", "High"]
    main_risks: list[str]
    confidence: RiskAssessmentConfidence


class MarketplaceVerdictReport(BaseModel):
    can_be_listed: bool
    can_be_rented: bool
    reason: str


class AgentIntelligenceReport(BaseModel):
    summary: str
    wallet_permission: WalletPermissionReport
    risk_assessment: RiskAssessmentReport
    marketplace_verdict: MarketplaceVerdictReport
    suggested_next_actions: list[str]


class DemoResetResponse(BaseModel):
    status: Literal["reset"]
    agents_seeded: int


def _normalize_address(value: str) -> str:
    try:
        return normalize_wallet_address(value)
    except ValueError as exc:
        raise ValueError("Invalid EVM address") from exc


def _normalize_optional_address(value: str | None) -> str | None:
    if value in {None, ""}:
        return None
    return _normalize_address(value)


def _normalize_address_list(values: list[str]) -> list[str]:
    return [_normalize_address(value) for value in values]


def _normalize_token_list(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        if value.upper() == "NATIVE":
            normalized.append("NATIVE")
        else:
            normalized.append(_normalize_address(value))
    return normalized


def _validate_wei_string(value: str) -> str:
    if not is_non_negative_integer_string(value):
        raise ValueError("Value must be a non-negative integer string")
    return value
