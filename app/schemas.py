from typing import Any, Literal

from pydantic import BaseModel, Field


AgentStatus = Literal["active", "paused", "retired"]
EventOutcome = Literal["success", "failed", "error"]
ComplaintSeverity = Literal["low", "medium", "high"]
ComplaintStatus = Literal["open", "confirmed", "dismissed"]


class AgentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)
    agent_type: str = Field(min_length=2, max_length=80)
    owner_wallet: str = Field(min_length=6, max_length=120)
    chain_id: int = 5000
    status: AgentStatus = "active"


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


class AgentSummary(BaseModel):
    agent: Agent
    reputation: Reputation


class AgentPassport(BaseModel):
    agent: Agent
    reputation: Reputation
    actions_history: list[AgentEvent]
    complaints: list[Complaint]
    audit_log: list[dict[str, Any]]
