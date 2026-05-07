from llm_router import LLMRouter
from compliance import ComplianceEngine, sanitize_input
from config import settings
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
        self.llm = LLMRouter()
        self.compliance = ComplianceEngine()

    async def run_analysis(self, idea: str, user_id: str) -> dict:
        clean_idea = sanitize_input(idea)
        ticker = self.compliance.extract_ticker(clean_idea)

        market_data = await self.compliance.fetch_market_data(ticker)
        context_str = (
            f"Ticker: {ticker}. Live market data: P/E={market_data.get('pe_ratio', 'N/A')}, "
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

        result = await self.llm.analyze(prompt, self.SYSTEM_PROMPT)

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
            "ticker": ticker,
            "market_data": market_data
        }
