from openai import AsyncOpenAI
from config import settings
from models import InvestmentMemo
from data.json_parser import parse_with_recovery
import json
import logging
from typing import Type, TypeVar
from pydantic import BaseModel

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

MOCK_MEMO = json.dumps({
    "company_name": "MockCorp AG",
    "sector": "Technology - Enterprise SaaS",
    "investment_thesis": "Scalable SaaS model with 25% YoY growth, strong DACH presence, and expanding ARR base.",
    "financial_highlights": {
        "revenue": "EUR 10M ARR",
        "growth": "25% YoY",
        "gross_margin": "78%",
        "net_margin": "18%",
        "debt_to_equity": 0.45
    },
    "market_opportunity": "EUR 2.5B TAM in DACH region; regulatory tailwinds from AI Act compliance demand.",
    "competitive_advantages": [
        "Proprietary AI engine with 3-year head start",
        "High switching costs (avg. 18-month integration)",
        "Certified under ISO 27001 and SOC 2 Type II"
    ],
    "key_risks": [
        {
            "category": "Regulatory",
            "level": "MEDIUM",
            "description": "EU AI Act compliance requirements pending final guidance.",
            "mitigation": "Legal review initiated; budget allocated for Q3 compliance audit."
        },
        {
            "category": "Market",
            "level": "LOW",
            "description": "Competitive pressure from US-based SaaS providers entering EU market.",
            "mitigation": "Strengthen local partnerships and data-sovereignty positioning."
        }
    ],
    "recommended_action": "BUY",
    "confidence_score": 0.82
})


class LLMRouter:
    def __init__(self):
        has_key = bool(settings.LLM_API_KEY or settings.DEEPSEEK_API_KEY)
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY or settings.DEEPSEEK_API_KEY or "sk-mock-key",
            base_url=settings.LLM_BASE_URL or settings.DEEPSEEK_BASE_URL,
            timeout=30.0,
            max_retries=0,
        ) if has_key else None
        self.model = settings.LLM_MODEL or settings.DEEPSEEK_MODEL
        self._is_mock = not has_key

    async def analyze(self, prompt: str, system_prompt: str, response_format: Type[T] | None = None) -> dict:
        if self._is_mock:
            logger.warning("No DeepSeek API key configured. Returning structured mock response.")
            return self._mock_result()
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 4000
            }
            if response_format:
                schema_name = response_format.__name__
                if schema_name == "StartupInvestmentMemo":
                    messages[-1]["content"] += (
                        "\n\nRespond ONLY with valid JSON matching the StartupInvestmentMemo schema. "
                        "Use exactly these fields: company_name, sector, stage, location, "
                        "recommendation (STRONG_INVEST/INVEST/CONDITIONAL_INVEST/NEED_MORE_INFO/PASS), "
                        "confidence_score (0.0-1.0), investment_thesis, key_strengths (array), "
                        "key_risks (array of {category, severity, description, mitigation}), "
                        "metrics (object with: tam_eur, sam_eur, som_eur_year3, pricing_tiers, "
                        "projected_arr_year1, projected_mrr_year1, target_customers_year1, "
                        "gross_margin_target, cac_target, ltv_target, ltv_cac_ratio, "
                        "payback_months, churn_rate_monthly, funding_ask_min, funding_ask_max, "
                        "founder_count), "
                        "requested_documents (array), critical_questions (array). "
                        "Use null for missing values, NEVER invent numbers."
                    )
                else:
                    messages[-1]["content"] += (
                        "\n\nRespond ONLY with a single JSON object. "
                        "Fields: company_name, sector, investment_thesis, "
                        "financial_highlights (object), market_opportunity, "
                        "competitive_advantages (array), "
                        "key_risks (array of {category, level, description, mitigation}), "
                        "recommended_action (BUY/HOLD/PASS/NEED_MORE_INFO), "
                        "confidence_score (0.0-1.0)."
                    )

            response = await self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            usage = response.usage
            cost = (usage.prompt_tokens * 0.00014 + usage.completion_tokens * 0.00028) / 1000

            parsed = None
            if response_format:
                parsed = parse_with_recovery(content, response_format)
                if parsed is None:
                    preview = content[:500] if content else "EMPTY"
                    logger.error("All JSON parse strategies failed for %s. Preview: %s", response_format.__name__, preview)
                    try:
                        parsed = response_format.model_validate({})
                    except Exception as e:
                        logger.warning("Empty model_validate also failed: %s", e)
                        parsed = None

            return {
                "success": True,
                "content": content,
                "parsed": parsed,
                "cost_usd": round(cost, 6),
                "tokens": usage.total_tokens,
                "model": self.model
            }
        except Exception as e:
            logger.error("LLM API error: %s", e)
            return {
                "success": False,
                "content": MOCK_MEMO,
                "parsed": None,
                "cost_usd": 0.0,
                "tokens": 0,
                "model": "fallback",
                "error": str(e)
            }

    def _mock_result(self) -> dict:
        parsed = InvestmentMemo.model_validate_json(MOCK_MEMO)
        return {
            "success": True,
            "content": MOCK_MEMO,
            "parsed": parsed,
            "cost_usd": 0.0,
            "tokens": 0,
            "model": "mock"
        }
