from enum import Enum
from typing import Optional, Any, Dict, TypeVar, Generic
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class Action(str, Enum):
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"


class FundamentalAnalysisData(BaseModel):
    action: Action
    confidence_score: float
    reason: str
    source: str = "fundamental_agent"


class HealthData(BaseModel):
    status: str = "healthy"


T = TypeVar("T")


class StandardResponse(BaseModel, Generic[T]):
    agent_type: str = "fundamental"
    version: str = "2.0.0"
    status: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    data: T
    error: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
