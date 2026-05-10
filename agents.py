from startup_dd.router import MultiLLMRouter
from compliance import ComplianceEngine, sanitize_input
from config import settings
from models import InvestmentMemo
import logging

logger = logging.getLogger(__name__)


SYSTEM_PROMPTS = {
    "de": (
        "Du bist ein Senior Financial Analyst, der institutionelle Due Diligence durchfuehrt. "
        "Output strikt als JSON gemaess InvestmentMemo-Schema. "
        "Alle Analysen muessen MiFID II Informationsstandards entsprechen. "
        "Beruecksichtige realistische Risikofaktoren, finanzielle Kennzahlen und eine klare Empfehlung. "
        "JSON-Feldnamen muessen auf ENGLISCH bleiben (company_name, sector, etc.). "
        "Nur die Textwerte (investment_thesis, market_opportunity, description, etc.) auf Deutsch schreiben. "
        "Risikostufen: severity/level muss LOW, MEDIUM, HIGH oder CRITICAL sein (nicht uebersetzt)."
    ),
    "en": (
        "You are a senior financial analyst performing institutional-grade due diligence. "
        "Output strictly JSON conforming to the provided InvestmentMemo schema. "
        "All analysis must comply with MiFID II informational standards. "
        "Include realistic risk factors, financial metrics, and a clear recommendation."
    ),
    "fr": (
        "Vous eates un analyste financier senior effectuant une due diligence de niveau institutionnel. "
        "Sortie strictement en JSON conforme au schema InvestmentMemo. "
        "Toutes les analyses doivent respecter les normes d'information MiFID II. "
        "Incluez des facteurs de risque realistes, des indicateurs financiers et une recommandation claire. "
        "Les noms de champs JSON doivent rester en ANGLAIS (company_name, sector, etc.). "
        "Seules les valeurs textuelles (investment_thesis, description, etc.) en francais. "
        "Niveaux de risque : severity/level doit etre LOW, MEDIUM, HIGH ou CRITICAL (pas traduit)."
    ),
    "ar": (
        "أنت محلل مالي أول يقوم بإجراء العناية الواجبة على المستوى المؤسسي. "
        "الإخراج بدقة بتنسيق JSON وفقاً لمخطط InvestmentMemo. "
        "يجب أن تلتزم جميع التحليلات بمعايير MiFID II للمعلومات. "
        "قم بتضمين عوامل خطر واقعية ومقاييس مالية وتوصية واضحة. "
        "يجب أن تبقى أسماء حقول JSON بالإنجليزية (company_name, sector, إلخ). "
        "فقط القيم النصية (investment_thesis, description, إلخ) بالعربية. "
        "مستويات المخاطرة: severity/level يجب أن تكون LOW أو MEDIUM أو HIGH أو CRITICAL (غير مترجمة)."
    ),
    "tr": (
        "Kurumsal d\u00fczeyde durum tespiti yapan k\u0131demli bir finans analistisiniz. "
        "InvestmentMemo \u015femas\u0131na uygun olarak kesinlikle JSON \u00e7\u0131kt\u0131s\u0131 verin. "
        "T\u00fcm analizler MiFID II bilgi standartlar\u0131na uygun olmal\u0131d\u0131r. "
        "Ger\u00e7ek\u00e7i risk fakt\u00f6rlerini, finansal metrikleri ve net bir tavsiyeyi dahil edin. "
        "JSON alan adlar\u0131 \u0130ngilizce kalmal\u0131d\u0131r (company_name, sector, vb.). "
        "Sadece metin de\u011ferleri (investment_thesis, description, vb.) T\u00fcrk\u00e7e yaz\u0131n. "
        "Risk seviyeleri: severity/level LOW, MEDIUM, HIGH veya CRITICAL olmal\u0131d\u0131r (\u00e7evrilmemi\u015f)."
    ),
}

def get_system_prompt(lang: str = "de") -> str:
    return SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS["en"])


class InvestmentAgent:
    def __init__(self):
        self.llm = MultiLLMRouter()
        self.compliance = ComplianceEngine()

    async def run_analysis(self, idea: str, user_id: str, lang: str = "de") -> dict:
        system_prompt = get_system_prompt(lang)
        lang_instruction_en = f"\n\nIMPORTANT: Write ALL text fields in {lang.upper()}."
        lang_instruction_de = f"\n\nWICHTIG: Schreibe ALLE Textfelder auf {lang.upper()}."

        lang_prompts = {
            "de": lang_instruction_de,
            "en": lang_instruction_en,
            "fr": "\n\nIMPORTANT : Redigez TOUS les champs de texte en {lang_upper}.",
            "ar": "\n\nهام: اكتب جميع الحقول النصية بـ {lang_upper}.",
            "tr": "\n\nÖNEMLİ: Tüm metin alanlarını {lang_upper} olarak yazın.",
        }
        lang_suffix = lang_prompts.get(lang, lang_instruction_en).format(lang=lang, lang_upper=lang.upper())

        clean_idea = sanitize_input(idea)
        ticker = self.compliance.extract_ticker(clean_idea)

        market_data = await self.compliance.fetch_market_data(ticker)

        if ticker:
            context_str = (
                f"Listed company ticker: {ticker}. "
                f"Market data: P/E={market_data.get('pe_ratio', 'N/A')}, "
                f"D/E={market_data.get('debt_to_equity', 'N/A')}, "
                f"Revenue Growth={market_data.get('revenue_growth_yoy', 'N/A')}, "
                f"Market Cap=${market_data.get('market_cap_usd', 'N/A')}"
            )
            prompt = (
                f"Perform a structured due diligence analysis for the following investment idea:\n\n"
                f"**Idea:** {clean_idea}\n\n"
                f"**Market Context:** {context_str}\n\n"
                f"Provide a comprehensive InvestmentMemo with financial highlights, "
                f"risk assessment, competitive analysis, and a clear recommendation "
                f"(BUY/HOLD/PASS/NEED_MORE_INFO). Incorporate the provided financial metrics."
                f"{lang_suffix}"
            )
        else:
            prompt = (
                f"Perform a structured due diligence analysis for the following private company:\n\n"
                f"**Idea:** {clean_idea}\n\n"
                f"IMPORTANT: This is a PRIVATE company with NO public stock market data. "
                f"Extract ALL financial data from the investment document above "
                f"(pricing, revenue targets, customer numbers, funding ask, margins, "
                f"churn, LTV, CAC, TAM, SAM, SOM etc.) and put it in financial_highlights. "
                f"Use the document's own competitor names (not generic ones). "
                f"Base competitive advantages and risks on what the document says. "
                f"Do NOT invent financial figures that are not in the document. "
                f"Provide a comprehensive InvestmentMemo with a clear recommendation "
                f"(BUY/HOLD/PASS/NEED_MORE_INFO)."
                f"{lang_suffix}"
            )

        result = await self.llm.analyze(
            prompt, system_prompt,
            response_format=InvestmentMemo,
            session_id=user_id,
        )

        if not result["success"]:
            logger.error("Analysis failed: %s", result.get("error", "unknown"))

        parsed = result.get("parsed")
        if parsed is None:
            parsed = self.compliance.safe_parse_memo(result.get("content", "{}"))

        audit_id = await self.compliance.save_audit(
            user_id=user_id,
            llm_result=result,
            idea=clean_idea
        )

        return {
            "memo": parsed.model_dump(mode="json"),
            "audit_id": audit_id,
            "cost_usd": result["cost_usd"],
            "tokens_used": result["tokens"],
            "model_used": result["model"],
            "provider_status": "mock" if result["model"] == "mock" else "live",
            "provider_health": self.llm.health(),
            "consensus": result.get("consensus"),
            "ticker": ticker,
            "market_data": market_data
        }
