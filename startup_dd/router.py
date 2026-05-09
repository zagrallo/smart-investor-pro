import asyncio
import logging
import time
from typing import Any, TypeVar

import google.genai as genai

from config import settings
from data.json_parser import parse_with_recovery
from llm_router import LLMRouter
from pydantic import BaseModel
from .cache import get_cache, hash_key, cached

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class ProviderStatus:
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class MultiLLMRouter:
    def __init__(self):
        self.deepseek = LLMRouter()
        self.gemini = None
        self._init_gemini()
        self.session_costs: dict[str, float] = {}
        self.provider_health: dict[str, str] = {
            "deepseek": ProviderStatus.HEALTHY,
            "gemini": ProviderStatus.HEALTHY,
        }
        self.cost_cap = settings.LLM_COST_BUDGET
        self.parallel = settings.PARALLEL_ANALYSIS
        self.default = settings.DEFAULT_PROVIDER or "deepseek"
        self.cache_enabled = settings.CACHE_ENABLED

    def _init_gemini(self):
        key = settings.GEMINI_API_KEY
        if key:
            try:
                self._gemini_client = genai.Client(api_key=key)
                self.gemini = True
                logger.info("Gemini %s initialised", settings.GEMINI_MODEL)
            except Exception as e:
                logger.warning("Gemini init failed: %s", e)
                self.provider_health["gemini"] = ProviderStatus.DOWN

    async def analyze(
        self,
        prompt: str,
        system_prompt: str,
        response_format: type[T] | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        if self._budget_exceeded(session_id):
            return {
                "success": False,
                "error": "budget_exceeded",
                "cost_usd": self.session_costs.get(session_id or "", 0),
            }

        cache_key = hash_key(prompt, system_provider := self.default)
        if self.cache_enabled:
            cached_result, hit = await cached(cache_key, settings.REDIS_TTL_LLM, self._fetch, self.default, prompt, system_prompt, response_format)
            if hit:
                self._track_cost(session_id, cached_result.get("cost_usd", 0))
                cached_result["cache_hit"] = True
                return cached_result

        if self.parallel and self.gemini:
            return await self._analyze_parallel(prompt, system_prompt, response_format, session_id)

        result = await self._call_single(self.default, prompt, system_prompt, response_format)
        self._track_cost(session_id, result.get("cost_usd", 0))

        if self.cache_enabled:
            await get_cache().set(cache_key, result, settings.REDIS_TTL_LLM)

        if result.get("success") and self._confidence_ok(result):
            return result

        fallback = "gemini" if self.default == "deepseek" else "deepseek"
        if fallback == "gemini" and not self.gemini:
            fallback = "deepseek"
        if fallback != self.default:
            logger.info("Fallback %s -> %s (session=%s)", self.default, fallback, session_id)
            fb = await self._call_single(fallback, prompt, system_prompt, response_format)
            self._track_cost(session_id, fb.get("cost_usd", 0))
            if self.cache_enabled:
                fb_cache_key = hash_key(prompt, fallback)
                await get_cache().set(fb_cache_key, fb, settings.REDIS_TTL_LLM)
            return fb

        return result

    async def _fetch(self, provider: str, prompt: str, system_prompt: str, response_format: type[T] | None) -> dict | None:
        return await self._call_single(provider, prompt, system_prompt, response_format)

    async def _analyze_parallel(
        self,
        prompt: str,
        system_prompt: str,
        response_format: type[T] | None,
        session_id: str | None,
    ) -> dict[str, Any]:
        tasks = {
            "deepseek": self._call_single("deepseek", prompt, system_prompt, response_format),
        }
        if self.gemini:
            tasks["gemini"] = self._call_single("gemini", prompt, system_prompt, response_format)

        results = await asyncio.wait_for(
            asyncio.gather(*tasks.values(), return_exceptions=True),
            timeout=60.0,
        )
        provider_results = {}
        for name, r in zip(tasks, results):
            if isinstance(r, Exception):
                logger.error("%s failed: %s", name, r)
                self.provider_health[name] = ProviderStatus.DEGRADED
                continue
            provider_results[name] = r
            self._track_cost(session_id, r.get("cost_usd", 0))

        if not provider_results:
            return {"success": False, "error": "all_providers_failed", "cost_usd": self.session_costs.get(session_id or "", 0)}

        return self._consensus(provider_results, response_format)

    def _consensus(self, results: dict[str, dict], response_format: type[T] | None) -> dict[str, Any]:
        from .consensus import calculate_consensus

        best_name = max(results, key=lambda n: results[n].get("parsed", type("", (), {"confidence_score": 0})).confidence_score if hasattr(results[n].get("parsed"), "confidence_score") else 0)
        merged = results[best_name]
        merged["consensus"] = calculate_consensus(results)
        logger.info(
            "Consensus v2: conf=%.2f rec=%s agree=%.0f%% winner=%s",
            merged["consensus"].get("confidence_score", 0),
            merged["consensus"].get("recommendation", "?"),
            merged["consensus"].get("agreement_pct", 0),
            merged["consensus"].get("winner", "?"),
        )
        return merged

    async def _call_single(
        self,
        provider: str,
        prompt: str,
        system_prompt: str,
        response_format: type[T] | None,
    ) -> dict[str, Any]:
        try:
            if provider == "gemini" and self.gemini:
                return await self._call_gemini(prompt, system_prompt, response_format)
            return await self.deepseek.analyze(prompt, system_prompt, response_format)
        except Exception as e:
            logger.error("%s call error: %s", provider, e)
            self.provider_health[provider] = ProviderStatus.DEGRADED
            return {"success": False, "content": "", "parsed": None, "cost_usd": 0, "tokens": 0, "model": provider, "error": str(e)}

    async def _call_gemini(
        self,
        prompt: str,
        system_prompt: str,
        response_format: type[T] | None,
    ) -> dict[str, Any]:
        full_prompt = f"{system_prompt}\n\n{prompt}"
        if response_format:
            schema_name = response_format.__name__
            if schema_name == "StartupInvestmentMemo":
                full_prompt += (
                    "\n\nRespond ONLY with valid JSON. "
                    "Fields: company_name, sector, stage, location, "
                    "recommendation (STRONG_INVEST/INVEST/CONDITIONAL_INVEST/NEED_MORE_INFO/PASS), "
                    "confidence_score (0.0-1.0), investment_thesis, key_strengths (array), "
                    "key_risks (array of {category, severity, description, mitigation}), "
                    "metrics (object with tam_eur, sam_eur, som_eur_year3, pricing_tiers, "
                    "projected_arr_year1, projected_mrr_year1, target_customers_year1, "
                    "gross_margin_target, cac_target, ltv_target, ltv_cac_ratio, "
                    "payback_months, churn_rate_monthly, funding_ask_min, funding_ask_max, "
                    "founder_count), "
                    "requested_documents (array), critical_questions (array). "
                    "Use null for missing values, NEVER invent numbers. "
                    "NOTE: LTV (ltv_target) is typically 5-50x HIGHER than CAC (cac_target). "
                    "Do NOT set both to the same value - if you only know one, leave the other as null."
                )
            else:
                full_prompt += (
                    "\n\nRespond ONLY with valid JSON. "
                    "Fields: company_name, sector, investment_thesis, "
                    "financial_highlights (object), market_opportunity, "
                    "competitive_advantages (array), "
                    "key_risks (array of {category, level, description, mitigation}), "
                    "recommended_action (BUY/HOLD/PASS/NEED_MORE_INFO), "
                    "confidence_score (0.0-1.0)."
                )

        response = await asyncio.wait_for(
            asyncio.to_thread(
                self._gemini_client.models.generate_content,
                model=settings.GEMINI_MODEL,
                contents=full_prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=4000,
                ),
            ),
            timeout=30.0,
        )
        content = response.text

        cost_est = len(full_prompt.split()) * 0.00001
        tokens_est = len(full_prompt.split()) + len(content.split())

        parsed = None
        if response_format:
            parsed = parse_with_recovery(content, response_format)

        return {
            "success": True,
            "content": content,
            "parsed": parsed,
            "cost_usd": round(cost_est, 6),
            "tokens": tokens_est,
            "model": settings.GEMINI_MODEL,
        }

    def _confidence_ok(self, result: dict) -> bool:
        p = result.get("parsed")
        if p is None:
            return False
        cs = getattr(p, "confidence_score", None) if hasattr(p, "confidence_score") else getattr(p, "confidence_score", None)
        if cs is None:
            cs = getattr(p, "confidence_score", 0.5)
        return float(cs) >= 0.7

    def _track_cost(self, session_id: str | None, cost: float):
        if session_id:
            self.session_costs[session_id] = self.session_costs.get(session_id, 0) + cost

    def _budget_exceeded(self, session_id: str | None) -> bool:
        if not session_id:
            return False
        return self.session_costs.get(session_id, 0) > self.cost_cap

    def get_session_cost(self, session_id: str) -> float:
        return self.session_costs.get(session_id, 0.0)

    def health(self) -> dict:
        from .cache import get_cache
        return {
            "providers": {
                "deepseek": self.provider_health["deepseek"],
                "gemini": self.provider_health["gemini"],
                "gemini_configured": self.gemini is not None,
            },
            "mode": "parallel" if self.parallel else "single",
            "default": self.default,
            "cost_cap": self.cost_cap,
            "cache": get_cache().summary(),
        }

    async def clear_cache(self, pattern: str = ""):
        from .cache import get_cache
        await get_cache().clear(pattern)
