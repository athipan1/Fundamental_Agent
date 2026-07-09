from enum import Enum
from typing import Optional, Any, Dict, TypeVar, Generic, Literal, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone

FUNDAMENTAL_AGENT_TYPE = "fundamental"
FUNDAMENTAL_AGENT_VERSION = "1.1.0"
FUNDAMENTAL_SERVICE_VERSION = "2.2.0"
SCHEMA_VERSION = "1.0"
FUNDAMENTAL_EVIDENCE_VERSION = "fundamental-evidence-v1"


class Action(str, Enum):
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"


class StandardAgentData(BaseModel):
    action: Action
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reason: str


class FundamentalEvidenceContract(BaseModel):
    evidence_version: str = FUNDAMENTAL_EVIDENCE_VERSION
    evidence_status: Literal["complete", "partial", "insufficient"]
    evidence_completeness_score: float = Field(ge=0.0, le=1.0)
    raw_scores: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    available_fields: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    missing_critical_metrics: List[str] = Field(default_factory=list)
    evidence_reasons: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    strategy_bucket_hint: None = None
    bucket_decision_authority: Literal["manager"] = "manager"
    manager_decision_required: bool = True


class FundamentalAnalysisData(StandardAgentData):
    source: str = "fundamental_agent"
    quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    growth_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    valuation_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    financial_health_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    cash_flow_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    fundamental_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    sector: Optional[str] = None
    sector_weights: Dict[str, float] = Field(default_factory=dict)
    risk_flags: List[str] = Field(default_factory=list)
    comparative_analysis: Dict[str, Any] = Field(default_factory=dict)
    key_metrics: Dict[str, Any] = Field(default_factory=dict)
    raw_scores: Dict[str, Any] = Field(default_factory=dict)
    fundamental_evidence: Optional[FundamentalEvidenceContract] = None
    evidence_version: str = FUNDAMENTAL_EVIDENCE_VERSION
    evidence_status: Literal["complete", "partial", "insufficient", "unavailable"] = "unavailable"
    evidence_completeness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    manager_decision_required: bool = True
    bucket_decision_authority: Literal["manager"] = "manager"
    confidence_cap: float = 0.80
    raw_confidence_score: Optional[float] = None
    data_quality_score: Optional[float] = None
    validation_status: str = "fundamental_validation_required_before_live"


class HealthData(BaseModel):
    status: str = "healthy"
    confidence_cap: float = 0.80
    validation_endpoint: str = "/validate/fundamental"
    evidence_version: str = FUNDAMENTAL_EVIDENCE_VERSION
    bucket_decision_authority: Literal["manager"] = "manager"


class FundamentalValidationRequest(BaseModel):
    tickers: List[str] = Field(default_factory=lambda: ["AAPL", "MSFT", "NVDA"])
    style: Literal["growth", "value", "dividend"] = "growth"
    min_data_quality_score: float = Field(0.70, ge=0.0, le=1.0)
    min_average_confidence: float = Field(0.35, ge=0.0, le=1.0)


class FundamentalValidationItem(BaseModel):
    ticker: str
    status: Literal["success", "error"]
    confidence_score: float
    data_quality_score: float
    action: Action
    risk_flags: List[str] = Field(default_factory=list)
    passed: bool
    reason: str


class FundamentalValidationReport(BaseModel):
    tickers: List[str]
    style: str
    confidence_cap: float
    tested: int
    passed_count: int
    failed_count: int
    average_confidence: float
    average_data_quality_score: float
    passed: bool
    criteria: Dict[str, Any]
    results: List[FundamentalValidationItem]


T = TypeVar("T")


class StandardAgentResponse(BaseModel, Generic[T]):
    agent_type: str = FUNDAMENTAL_AGENT_TYPE
    version: str = FUNDAMENTAL_AGENT_VERSION
    schema_version: str = SCHEMA_VERSION
    status: Literal["success", "error"]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    data: Optional[T] = None
    error: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: Optional[float] = None

    @field_validator("schema_version")
    @classmethod
    def schema_version_must_be_semantic(cls, value: str) -> str:
        parts = value.split(".")
        if not all(part.isdigit() for part in parts):
            raise ValueError('Schema version must be in semantic format (e.g., "1.0")')
        return value
