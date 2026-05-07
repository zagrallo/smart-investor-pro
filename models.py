from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum


class ActionEnum(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    PASS = "PASS"
    NEED_MORE_INFO = "NEED_MORE_INFO"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskAssessment(BaseModel):
    category: str
    level: RiskLevel
    description: str
    mitigation: Optional[str] = None


class InvestmentMemo(BaseModel):
    company_name: str
    sector: str
    investment_thesis: str
    financial_highlights: dict
    market_opportunity: str
    competitive_advantages: List[str]
    key_risks: List[RiskAssessment]
    recommended_action: ActionEnum
    confidence_score: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditEntry(BaseModel):
    id: int
    user_id: str
    action: str
    model_used: str
    cost_usd: float
    tokens_used: int
    disclaimer_accepted: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
