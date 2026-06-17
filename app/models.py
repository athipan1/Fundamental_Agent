from enum import Enum
from typing import Optional, Any, Dict, TypeVar, Generic, Literal, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class Action(str, Enum):
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"


class StandardAgentData(BaseModel):
    action: Action
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reason: str


class FundamentalAnalysisData(StandardAgentData):
    source: str = "fundamental_agent"
    quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    growth_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    valuation_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    financial_health_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    cash_flow_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    sector: Optional[str] = None
    sector_weights: Dict[str, float] = Field(default_factory=dict)
    risk_flags: List[str] = Field(default_factory=list)
    comparative_analysis: Dict[str, Any] = Field(default_factory=dict)
    key_metrics: Dict[str, Any] = Field(default_factory=dict)


class HealthData(BaseModel):
    status: str = "healthy"


T = TypeVar("T")


class StandardAgentResponse(BaseModel, Generic[T]):
    agent_type: str = "fundamental"
    version: str = "2.0.0"
    status: Literal["success", "error"]
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    data: Optional[T] = None
    error: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
