import json
import logging

logger = logging.getLogger(__name__)


def extract_json(text: str) -> str:
    """Extract valid JSON from LLM responses that may contain markdown or chatter."""
    match = __import__("re").search(r"```json\s*(.*?)\s*```", text, __import__("re").DOTALL)
    if match:
        return match.group(1)
    match = __import__("re").search(r"\{.*\}", text, __import__("re").DOTALL)
    return match.group(0) if match else text


FIELD_ALIASES = {
    "company_name": ["issuer", "company", "name", "ticker_name", "organization", "ticker", "unternehmen", "firma"],
    "recommended_action": ["recommendation", "action", "rating", "verdict", "signal", "empfehlung", "handlung"],
    "confidence_score": ["confidence", "score", "conviction", "konfidenz", "vertrauen"],
    "investment_thesis": ["thesis", "rationale", "investment_case", "brief", "these", "anlagethese"],
    "market_opportunity": ["market", "opportunity", "tam", "market_size", "marktchance", "markt"],
    "competitive_advantages": ["advantages", "moat", "edge", "strengths", "competitive_edge", "wettbewerbsvorteile", "staerken"],
    "financial_highlights": ["financials", "metrics", "highlights", "financial_metrics", "key_metrics", "finanzkennzahlen"],
    "key_risks": ["risks", "risk_factors", "risk_assessment", "concerns", "threats", "risiken"],
    "sector": ["industry", "sector_industry", "segment", "branche"],
}


def _remap_fields(data: dict) -> dict:
    """Map known alternative field names to canonical model fields."""
    for canon, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in data and canon not in data:
                data[canon] = data.pop(alias)
    # If financial_highlights is a string, wrap in a dict
    if "financial_highlights" in data and isinstance(data["financial_highlights"], str):
        data["financial_highlights"] = {"summary": data.pop("financial_highlights")}
    # Normalize stage: lowercase + "pre-seed" → "pre_seed", "series a" → "series_a"
    if "stage" in data and isinstance(data["stage"], str):
        data["stage"] = data["stage"].lower().replace("-", "_").replace(" ", "_")
    return data


def _remap_nested(data: dict) -> dict:
    """Remap fields inside nested structures like key_risks. Fix German severity values."""
    risk_aliases = {"category": ["type", "area", "risk_type", "name", "kategorie"],
                    "description": ["detail", "desc", "text", "explanation", "beschreibung"],
                    "mitigation": ["mitigate", "action", "countermeasure", "plan", "massnahme"]}
    SEVERITY_MAP = {
        "NIEDRIG": "LOW", "NIEDR": "LOW",
        "MITTEL": "MEDIUM",
        "HOCH": "HIGH",
        "KRITISCH": "CRITICAL", "KRIT": "CRITICAL",
    }
    risks = data.get("key_risks") or data.get("risks") or []
    if isinstance(risks, list):
        mapped_risks = []
        for r in risks:
            if isinstance(r, dict):
                for canon, aliases in risk_aliases.items():
                    for alias in aliases:
                        if alias in r and canon not in r:
                            r[canon] = r.pop(alias)
                # Normalize risk level values for both field name variants
                for key in ("severity", "level"):
                    if key in r and isinstance(r[key], str):
                        val = r[key].upper()
                        r[key] = SEVERITY_MAP.get(val, val)
                mapped_risks.append(r)
        data["key_risks"] = mapped_risks
    return data


def parse_with_recovery(content: str, model_class):
    """Try multiple strategies to parse JSON into a Pydantic model."""
    if not content or not isinstance(content, str):
        return None

    # Strategy 1: Direct parse
    try:
        return model_class.model_validate_json(content)
    except Exception:
        pass

    # Strategy 2: Extract JSON from markdown or wrapped text
    try:
        clean = extract_json(content)
        return model_class.model_validate_json(clean)
    except Exception:
        pass

    # Strategy 3: Find JSON in nested braces
    try:
        depth = 0
        start = end = -1
        for i, c in enumerate(content):
            if c == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0 and start >= 0:
                    end = i + 1
                    break
        if start >= 0 and end > start:
            return model_class.model_validate_json(content[start:end])
    except Exception:
        pass

    # Strategy 4: Parse JSON, then remap known field aliases
    try:
        clean = extract_json(content)
        data = json.loads(clean) if isinstance(clean, str) else clean
        if isinstance(data, dict):
            data = _remap_fields(data)
            data = _remap_nested(data)
            return model_class.model_validate(data)
    except Exception as e:
        logger.warning("Field remapping failed: %s", e) if "Field" in str(e) else logger.warning("JSON remap error: %s", e)

    return None
