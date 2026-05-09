import logging
from typing import Any

logger = logging.getLogger(__name__)


def _sanity_check_metrics(metrics: dict):
    ltv = metrics.get("ltv_target")
    cac = metrics.get("cac_target")
    if ltv is not None and cac is not None and ltv > 0 and cac > 0 and ltv == cac:
        logger.warning("Suspicious metrics: ltv_target == cac_target == %s. LTV should be much larger than CAC.", ltv)


def compute_visuals(memo: dict) -> dict:
    metrics = memo.get("metrics", {})
    risks = memo.get("key_risks", [])
    _sanity_check_metrics(metrics)

    radar = _compute_radar(memo, metrics)
    scorecard = _compute_scorecard(radar)
    unit = _compute_unit_economics(metrics)
    projections = _compute_projections(metrics)

    return {
        "scorecard_total": scorecard,
        "radar_scores": radar,
        "unit_economics": unit,
        "projections": projections,
    }


def _compute_radar(memo: dict, metrics: dict) -> dict:
    base = {
        "market": 5.0,
        "product": 5.0,
        "team": 5.0,
        "financials": 5.0,
        "competition": 5.0,
        "execution": 5.0,
    }
    tam = metrics.get("tam_eur") or 0
    sam = metrics.get("sam_eur") or 0
    if tam > 0:
        base["market"] = min(10.0, round(5 + (tam / 500_000_000), 1))
    if sam > 0:
        base["market"] = max(base["market"], min(10.0, round(5 + (sam / 100_000_000), 1)))

    strengths = memo.get("key_strengths", [])
    base["product"] = min(10.0, round(5 + len(strengths) * 0.6, 1))

    ltv_cac = metrics.get("ltv_cac_ratio") or 0
    gm = metrics.get("gross_margin_target") or metrics.get("gross_margin_pct") or 0
    base["financials"] = min(10.0, round(3 + (ltv_cac / 4) + (gm / 20), 1))

    base["competition"] = min(10.0, round(5 + len(strengths) * 0.4, 1))

    severities = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
    risk_penalty = sum(severities.get(r.get("severity", "LOW"), 0) for r in memo.get("key_risks", [])) * 0.5
    base["execution"] = max(1.0, min(10.0, round(8 - risk_penalty, 1)))

    base["team"] = max(1.0, min(10.0, round(base["execution"] - 0.5, 1)))

    return base


def _compute_scorecard(radar: dict) -> int:
    weights = {"market": 0.20, "product": 0.20, "team": 0.15, "financials": 0.20, "competition": 0.15, "execution": 0.10}
    total = sum(radar.get(k, 5) * weights[k] for k in weights)
    return min(100, max(0, round(total * 10)))


def _compute_unit_economics(metrics: dict) -> dict:
    ltv = metrics.get("ltv_target") or 0
    cac = metrics.get("cac_target") or 1
    ratio = round(ltv / cac, 1) if cac > 0 else 0

    gm = metrics.get("gross_margin_target") or metrics.get("gross_margin_pct") or 0

    payback = metrics.get("payback_months") or (metrics.get("payback_weeks", 0) / 4.33) if metrics.get("payback_weeks") else None

    benchmark = "top_5_percent" if ratio > 20 else ("top_10_percent" if ratio > 10 else ("good" if ratio > 3 else "below_average"))

    return {
        "ltv_cac_ratio": ratio,
        "payback_months": round(payback, 1) if payback else None,
        "gross_margin_pct": gm,
        "benchmark_comparison": benchmark,
    }


def _compute_projections(metrics: dict) -> dict:
    arr_y1 = metrics.get("projected_arr_year1") or 0
    arr_y3 = metrics.get("projected_arr_year3") or 0
    mrr_y1 = metrics.get("projected_mrr_year1") or 0
    customers_y1 = metrics.get("target_customers_year1") or 0
    customers_y3 = metrics.get("target_customers_year3") or 0
    churn = metrics.get("churn_rate_monthly") or 0
    funding = metrics.get("funding_ask_max") or metrics.get("funding_ask_min") or 0
    burn = metrics.get("burn_rate_monthly") or 0

    arr_y2 = round(arr_y1 * (1 + ((arr_y3 / arr_y1) ** 0.5 - 1) if arr_y1 > 0 else 0), 0) if arr_y3 and arr_y1 else 0

    cagr = round(((arr_y3 / arr_y1) ** (1/2) - 1) * 100, 1) if arr_y1 > 0 and arr_y3 > 0 else None

    if burn > 0:
        runway = round(funding / (burn * 12), 1) if funding > 0 else None
    else:
        runway = None

    breakdown = {
        "fixed_costs_monthly": burn or 7500,
    }
    if mrr_y1 > 0:
        breakdown["break_even_mrr"] = round(breakdown["fixed_costs_monthly"] / 0.78, 0)
        breakdown["break_even_month"] = round(breakdown["break_even_mrr"] / (mrr_y1 / 12), 0) if mrr_y1 > 0 else None
    else:
        breakdown["break_even_mrr"] = round(breakdown["fixed_costs_monthly"] / 0.78, 0)
        breakdown["break_even_month"] = None

    return {
        "arr_year1": arr_y1,
        "arr_year2": arr_y2,
        "arr_year3": arr_y3,
        "cagr_pct": cagr,
        "customers_year1": customers_y1,
        "customers_year3": customers_y3,
        "monthly_churn_pct": churn,
        "runway_months": runway,
        "breakdown": breakdown,
    }
