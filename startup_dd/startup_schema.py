from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum
from datetime import datetime, timezone


class StartupStage(str, Enum):
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    GROWTH = "growth"


class Recommendation(str, Enum):
    STRONG_INVEST = "STRONG_INVEST"
    INVEST = "INVEST"
    CONDITIONAL_INVEST = "CONDITIONAL_INVEST"
    NEED_MORE_INFO = "NEED_MORE_INFO"
    PASS = "PASS"


class StartupMetrics(BaseModel):
    tam_eur: Optional[float] = None
    sam_eur: Optional[float] = None
    som_eur_year3: Optional[float] = None
    pricing_tiers: List[Dict] = Field(default_factory=list)
    projected_arr_year1: Optional[float] = None
    projected_arr_year3: Optional[float] = None
    projected_mrr_year1: Optional[float] = None
    target_customers_year1: Optional[int] = None
    target_customers_year3: Optional[int] = None
    gross_margin_target: Optional[float] = None
    cac_target: Optional[float] = None
    cac_initial: Optional[float] = None
    ltv_target: Optional[float] = None
    ltv_cac_ratio: Optional[float] = None
    payback_months: Optional[float] = None
    burn_rate_monthly: Optional[float] = None
    runway_months: Optional[float] = None
    mvp_status: str = "MVP"
    paying_customers: Optional[int] = None
    mrr_current: Optional[float] = None
    churn_rate_monthly: Optional[float] = None
    funding_ask_min: Optional[float] = None
    funding_ask_max: Optional[float] = None
    total_raised_to_date: Optional[float] = None
    founder_count: Optional[int] = None
    technical_founder: Optional[bool] = None
    industry_experience: Optional[bool] = None


class StartupRisk(BaseModel):
    category: str
    severity: str
    description: str
    mitigation: Optional[str] = None


class StartupInvestmentMemo(BaseModel):
    company_name: str = "Unknown"
    sector: str
    stage: StartupStage = StartupStage.PRE_SEED
    location: str = "DACH"
    analysis_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    recommendation: Recommendation = Recommendation.NEED_MORE_INFO
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    investment_thesis: str = ""
    market_dynamics: Optional[str] = None
    competitive_analysis: Optional[str] = None
    strategic_advice: Optional[str] = None
    key_strengths: List[str] = Field(default_factory=list)
    key_risks: List[StartupRisk] = Field(default_factory=list)
    metrics: StartupMetrics = Field(default_factory=StartupMetrics)
    dd_checklist: Dict[str, bool] = Field(default_factory=lambda: {
        "financials_verified": False,
        "team_background_checked": False,
        "market_size_validated": False,
        "product_demo_seen": False,
        "customer_references_checked": False,
    })
    requested_documents: List[str] = Field(default_factory=list)
    critical_questions: List[str] = Field(default_factory=list)
    visual_metrics: Optional[Dict] = None
    disclaimer: str = (
        "Diese Startup-Due-Diligence-Analyse dient ausschließlich "
        "Informationszwecken und stellt keine Anlageberatung dar. "
        "Investitionen in Startups sind mit hohem Risiko verbunden."
    )
