import json
import logging
from typing import Optional
from .router import MultiLLMRouter
from compliance import ComplianceEngine
from .startup_schema import StartupInvestmentMemo, Recommendation
from .vc_prompt import get_vc_prompt
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

    async def analyze(self, company_name: str, document_content: str, session_id: str | None = None, lang: str = "de") -> dict:
        system_prompt = get_vc_prompt(lang)
        prompt = self._build_prompt(company_name, [{"name": "Dokument", "content": document_content}], lang=lang)
        result = await self.llm.analyze(
            prompt, system_prompt,
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

    async def analyze_multi(self, company_name: str, documents: list, session_id: str | None = None, lang: str = "de") -> dict:
        system_prompt = get_vc_prompt(lang)
        prompt = self._build_prompt(company_name, documents, lang=lang)
        combined_raw = "\n\n".join(d["content"][:32000] for d in documents)
        result = await self.llm.analyze(
            prompt, system_prompt,
            response_format=StartupInvestmentMemo,
            session_id=session_id,
        )

        parsed = result.get("parsed")
        if parsed is None:
            parsed = self._fallback_parse(result.get("content", "{}"))
        elif isinstance(parsed, StartupInvestmentMemo):
            parsed = self._enrich_with_regex(parsed, combined_raw)

        if not isinstance(parsed, StartupInvestmentMemo):
            reason = "API nicht erreichbar" if result.get("error") or not result.get("success") else "Dokumente konnten nicht verarbeitet werden"
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
            "document_count": len(documents),
        }

    def _build_prompt(self, company_name: str, documents: list, lang: str = "de") -> str:
        parts = []
        total = 0
        max_total = 60000
        doc_label = "Document" if lang != "de" else "Dokument"
        for i, doc in enumerate(documents):
            name = doc.get("name", f"{doc_label} {i+1}")
            content = doc.get("content", "")
            truncated = content[:32000]
            block = f"--- {doc_label} {i+1}: {name} ---\n{truncated}"
            if total + len(block) > max_total and parts:
                remaining = len(documents) - i
                msg_en = f"\n[{remaining} more documents truncated due to token limit]"
                msg_de = f"\n[Weitere {remaining} Dokumente gekuerzt wegen Token-Limit]"
                parts.append(msg_en if lang != "de" else msg_de)
                break
            parts.append(block)
            total += len(block)

        combined = "\n\n".join(parts)

        doc_count = len(documents)
        prompts = {
            "de": (
                f"Analysiere die folgenden {doc_count} Startup-Dokumente und erstelle eine vollstaendige InvestmentMemo.\n\n"
                f"**Company:** {company_name}\n\n"
                f"**Eingereichte Dokumente ({doc_count} Stueck):**\n\n"
                f"{combined}\n\n"
                f"Extrahiere ALLE Metriken aus ALLEN Dokumenten. "
                f"Nutze konkrete Zahlen aus den Texten. "
                f"Die Dokumente koennen sich ergaenzen oder ueberschneiden – "
                f"trotzdem eine kohaerente Analyse erstellen."
            ),
        }
        default_en = (
            f"Analyze the following {doc_count} startup documents and create a complete InvestmentMemo.\n\n"
            f"**Company:** {company_name}\n\n"
            f"**Submitted Documents ({doc_count}):**\n\n"
            f"{combined}\n\n"
            f"Extract ALL metrics from ALL documents. "
            f"Use concrete numbers from the texts. "
            f"The documents may complement or overlap – "
            f"still create a coherent analysis."
        )
        return prompts.get(lang, default_en)

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

    def _empty_memo(self, company_name: str, reason: str = "Unbekannter Fehler", lang: str = "de") -> StartupInvestmentMemo:
        thesis = {
            "de": f"Analyse fehlgeschlagen: {reason}. Bitte pruefen: Server-API-Key gueltig? Internetverbindung? Dokument im MD-Format?",
            "en": f"Analysis failed: {reason}. Please check: Server API key valid? Internet connection? Document in MD format?",
            "fr": f"Analyse échouée : {reason}. Veuillez vérifier : clé API valide ? Connexion Internet ? Document au format MD ?",
            "ar": f"فشل التحليل: {reason}. يرجى التحقق: مفتاح API صالح؟ اتصال بالإنترنت؟ المستند بتنسيق MD؟",
            "tr": f"Analiz başarısız: {reason}. Lütfen kontrol edin: Sunucu API anahtarı geçerli mi? İnternet bağlantısı? Belge MD formatında mı?",
        }.get(lang, f"Analysis failed: {reason}.")
        return StartupInvestmentMemo(
            company_name=company_name,
            sector="Unknown",
            investment_thesis=thesis,
        )
