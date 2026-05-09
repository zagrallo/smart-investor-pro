from startup_dd.router import MultiLLMRouter
from compliance import ComplianceEngine, sanitize_input
from config import settings
from models import InvestmentMemo
import logging

logger = logging.getLogger(__name__)


class InvestmentAgent:
    SYSTEM_PROMPT = (
        "You are a senior financial analyst performing institutional-grade due diligence. "
        "Output strictly JSON conforming to the provided InvestmentMemo schema. "
        "All analysis must comply with MiFID II informational standards. "
        "Include realistic risk factors, financial metrics, and a clear recommendation."
    )

    def __init__(self):
        self.llm = MultiLLMRouter()
        self.compliance = ComplianceEngine()

    async def run_analysis(self, idea: str, user_id: str) -> dict:
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
            )

        result = await self.llm.analyze(
            prompt, self.SYSTEM_PROMPT,
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
