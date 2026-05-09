import json
import logging
from typing import Optional
from .router import MultiLLMRouter
from compliance import ComplianceEngine
from .startup_schema import StartupInvestmentMemo, Recommendation
from .vc_prompt import VC_SYSTEM_PROMPT
from .document_parser import StartupDocumentParser
from .evaluator import StartupEvaluator
from data.json_parser import parse_with_recovery

logger = logging.getLogger(__name__)


class StartupAgent:
    def __init__(self):
        self.llm = MultiLLMRouter()
        self.compliance = ComplianceEngine()
        self.parser = StartupDocumentParser()
        self.evaluator = StartupEvaluator()

    async def analyze(self, company_name: str, document_content: str, session_id: str | None = None) -> dict:
        prompt = self._build_prompt(company_name, document_content)
        result = await self.llm.analyze(
            prompt, VC_SYSTEM_PROMPT,
            response_format=StartupInvestmentMemo,
            session_id=session_id,
        )

        parsed = result.get("parsed")
        if parsed is None:
            parsed = self._fallback_parse(result.get("content", "{}"))
        elif isinstance(parsed, StartupInvestmentMemo):
            parsed = self._enrich_with_regex(parsed, document_content)

        if not isinstance(parsed, StartupInvestmentMemo):
            reason = "API nicht erreichbar" if result.get("error") or not result.get("success") else "Dokument konnte nicht verarbeitet werden"
            parsed = self._empty_memo(company_name, reason)

        parsed.confidence_score = self.evaluator.calculate_confidence(
            parsed.confidence_score, parsed.metrics
        )
        parsed.recommendation = self.evaluator.evaluate(
            parsed.metrics, parsed.confidence_score
        )

        from .visuals import compute_visuals
        parsed.visual_metrics = compute_visuals(parsed.model_dump(mode="json"))

        return {
            "memo": parsed.model_dump(mode="json"),
            "cost_usd": result["cost_usd"],
            "tokens_used": result["tokens"],
            "model_used": result["model"],
            "provider_status": "mock" if result["model"] == "mock" else "live",
            "provider_health": self.llm.health(),
            "consensus": result.get("consensus"),
        }

    def _build_prompt(self, company_name: str, document: str) -> str:
        return (
            f"Analysiere das folgende Startup-Dokument und erstelle eine InvestmentMemo:\n\n"
            f"**Company:** {company_name}\n\n"
            f"**Dokument:**\n{document[:32000]}\n\n"
            f"Extrahiere ALLE Metriken aus dem Dokument. "
            f"Nutze konkrete Zahlen aus dem Text."
        )

    def _enrich_with_regex(self, memo: StartupInvestmentMemo, raw: str) -> StartupInvestmentMemo:
        parsed_metrics = self.parser.parse_all(raw)
        existing = memo.metrics
        for field in parsed_metrics.model_fields_set:
            val = getattr(parsed_metrics, field)
            if val is not None and val != []:
                setattr(existing, field, val)
        if not memo.metrics.pricing_tiers and parsed_metrics.pricing_tiers:
            existing.pricing_tiers = parsed_metrics.pricing_tiers
        memo.metrics = existing
        return memo

    def _fallback_parse(self, content: str) -> Optional[StartupInvestmentMemo]:
        result = parse_with_recovery(content, StartupInvestmentMemo)
        if result is not None and isinstance(result, StartupInvestmentMemo):
            return result
        try:
            data = json.loads(content) if isinstance(content, str) else content
            return StartupInvestmentMemo.model_validate(data)
        except Exception as e:
            logger.warning("Fallback parse failed: %s", e)
            return None

    def _empty_memo(self, company_name: str, reason: str = "Unbekannter Fehler") -> StartupInvestmentMemo:
        return StartupInvestmentMemo(
            company_name=company_name,
            sector="Unknown",
            investment_thesis=f"Analyse fehlgeschlagen: {reason}. Bitte pruefen: Server-API-Key gueltig? Internetverbindung? Dokument im MD-Format?",
        )
