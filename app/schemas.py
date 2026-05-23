from typing import Any, Literal

from pydantic import BaseModel, Field


AgentStatus = Literal["active", "paused", "retired"]
EventOutcome = Literal["success", "failed", "error"]
ComplaintSeverity = Literal["low", "medium", "high"]
ComplaintStatus = Literal["open", "confirmed", "dismissed"]
PricingModel = Literal["buy", "rent_hourly", "rent_daily", "per_task"]
ListingAvailability = Literal["available", "rented", "paused"]
RentalStatus = Literal["pending", "active", "completed", "disputed", "cancelled"]


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


class DemoResetResponse(BaseModel):
    status: Literal["reset"]
    agents_seeded: int
