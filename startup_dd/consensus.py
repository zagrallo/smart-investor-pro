import logging
from typing import Any
from .startup_schema import Recommendation

logger = logging.getLogger(__name__)

WEIGHTS = {"deepseek": 0.4, "gemini": 0.4}


def calculate_consensus(provider_results: dict[str, dict]) -> dict[str, Any]:
    parsed_list = [(name, r.get("parsed")) for name, r in provider_results.items() if r.get("parsed") is not None]
    if not parsed_list:
        return {"confidence_score": 0.0, "recommendation": "NEED_MORE_INFO", "agreement_pct": 0.0, "winner": None}
    if len(parsed_list) == 1:
        p = parsed_list[0][1]
        rec = getattr(p, "recommended_action", None) or getattr(p, "recommendation", None)
        return {"confidence_score": float(p.confidence_score), "recommendation": rec.value if hasattr(rec, "value") else str(rec), "agreement_pct": 100.0, "winner": parsed_list[0][0]}

    weighted_sum = 0.0
    weight_total = 0.0
    recommendations = []
    tam_values = []
    for name, p in parsed_list:
        w = WEIGHTS.get(name, 0.2)
        weighted_sum += float(p.confidence_score) * w
        weight_total += w
        rec = getattr(p, "recommended_action", None) or getattr(p, "recommendation", None)
        recommendations.append(rec.value if hasattr(rec, "value") else str(rec))
        metrics = getattr(p, "metrics", None)
        if metrics and metrics.tam_eur is not None:
            tam_values.append(metrics.tam_eur)

    consensus_conf = weighted_sum / weight_total if weight_total > 0 else 0.0

    agreement = _check_field_agreement(recommendations, tam_values)
    if agreement.get("recommendation_match"):
        consensus_conf = min(1.0, consensus_conf + 0.05)
    if agreement.get("tam_within_10pct"):
        consensus_conf = min(1.0, consensus_conf + 0.03)

    best = max(parsed_list, key=lambda x: float(x[1].confidence_score))
    logger.info("Consensus v2: conf=%.2f rec=%s agreement=%.0f%% winner=%s", consensus_conf, agreement.get("majority_rec"), agreement.get("pct"), best[0])

    return {
        "confidence_score": round(consensus_conf, 2),
        "recommendation": agreement["majority_rec"],
        "winner": best[0],
        "winner_confidence": float(best[1].confidence_score),
        "providers": list(provider_results.keys()),
        "agreement_pct": round(agreement["pct"], 1),
        "method": "weighted_average_with_boost",
    }


def _check_field_agreement(recommendations: list[str], tam_values: list[float]) -> dict:
    from collections import Counter
    cnt = Counter(recommendations)
    top_rec, top_count = cnt.most_common(1)[0]
    pct = round(top_count / len(recommendations) * 100, 1) if recommendations else 0

    tam_agree = False
    if len(tam_values) >= 2:
        tam_agree = max(tam_values) <= min(tam_values) * 1.10

    return {
        "recommendation_match": len(set(recommendations)) == 1,
        "majority_rec": top_rec,
        "tam_within_10pct": tam_agree,
        "pct": pct,
    }
