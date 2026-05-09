import logging
from typing import Dict, Any
from .startup_schema import StartupMetrics, StartupStage, Recommendation

logger = logging.getLogger(__name__)


class StartupEvaluator:
    """Bewertet extrahierte Startup-Metriken und kalkuliert Score."""

    WEIGHTS = {
        "market": 0.25,
        "product": 0.20,
        "business_model": 0.20,
        "team": 0.15,
        "traction": 0.10,
        "financials": 0.10,
    }

    def evaluate(self, metrics: StartupMetrics, llm_confidence: float) -> Recommendation:
        score = self._calculate_score(metrics)
        combined = 0.6 * score + 0.4 * llm_confidence
        if combined >= 0.7 and metrics.ltv_cac_ratio and metrics.ltv_cac_ratio >= 3:
            return Recommendation.INVEST
        elif combined >= 0.5 and metrics.tam_eur and metrics.tam_eur > 100_000_000:
            return Recommendation.CONDITIONAL_INVEST
        elif combined >= 0.3:
            return Recommendation.NEED_MORE_INFO
        return Recommendation.PASS

    def _calculate_score(self, metrics: StartupMetrics) -> float:
        scores = {}
        tam_score = min(1.0, (metrics.tam_eur or 0) / 1_000_000_000)
        sam_score = min(1.0, (metrics.sam_eur or 0) / 500_000_000)
        scores["market"] = 0.6 * tam_score + 0.4 * sam_score
        ltv_cac = metrics.ltv_cac_ratio or 0
        gross_margin = (metrics.gross_margin_target or 0) / 100
        scores["business_model"] = (
            0.3 * min(1.0, ltv_cac / 10) +
            0.3 * min(1.0, gross_margin / 0.8) +
            0.2 * min(1.0, (metrics.payback_months or 99) / 12) +
            0.2 * min(1.0, (metrics.target_customers_year1 or 0) / 500)
        )
        scores["financials"] = 0.5 * min(1.0, (metrics.funding_ask_min or 0) / 500_000) + \
                               0.5 * (1.0 if metrics.funding_ask_max else 0.3)
        scores["traction"] = min(1.0, (metrics.paying_customers or 0) / 50)
        scores["product"] = 0.7 + 0.3 * (1.0 if metrics.technical_founder else 0)
        scores["team"] = 0.5 + 0.25 * (1.0 if metrics.founder_count and metrics.founder_count >= 2 else 0) + \
                         0.25 * (1.0 if metrics.industry_experience else 0)
        total = sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        return min(1.0, max(0.0, total))

    def calculate_confidence(self, llm_says: float, metrics: StartupMetrics) -> float:
        data_completeness = self._data_completeness(metrics)
        return round((0.6 * llm_says + 0.4 * data_completeness), 2)

    def _data_completeness(self, metrics: StartupMetrics) -> float:
        fields = [
            metrics.tam_eur, metrics.sam_eur, metrics.pricing_tiers,
            metrics.cac_target, metrics.ltv_target, metrics.churn_rate_monthly,
            metrics.funding_ask_min, metrics.founder_count,
        ]
        present = sum(1 for f in fields if f is not None and f != [])
        return present / len(fields)
