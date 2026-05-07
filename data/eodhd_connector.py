import httpx
import logging
import os
from pydantic import BaseModel
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)


class EODHDFinancials(BaseModel):
    ticker: str
    pe_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    market_cap_usd: Optional[float] = None
    gross_margin: Optional[float] = None
    net_margin: Optional[float] = None
    source: str = "mock"


class FreeDataProvider:
    """Kostenlose Finanzdaten via yfinance + SEC EDGAR (Fallback).

    Primär: yfinance (alle Märkte, konsistente Felder).
    Sekundär: SEC EDGAR (US-only, wenn yfinance fehlschlägt).
    Fallback: statische Mock-Daten (wenn beides fehlschlägt).
    """
    BASE_URL = "https://eodhd.com/api"

    SEC_HEADERS = {"User-Agent": "SmartInvestorPro/1.0 (research@example.com)"}
    SEC_CIKS = {
        "AAPL": "0000320193", "MSFT": "0000789019", "GOOGL": "0001652044",
        "AMZN": "0001018724", "TSLA": "0001318605", "META": "0001326801",
        "NVDA": "0001045810", "JPM": "0000019617", "V": "0001403167",
        "MA": "0001141391", "PG": "0000080424", "DIS": "0001744489",
        "ADBE": "0000796343", "CRM": "0001108524", "NFLX": "0001065280",
        "INTC": "0000050863", "AMD": "0000002488", "PYPL": "0001633917",
        "SAP": "0001003024", "BAYN": "0001145460", "SIEGY": "0000729792",
    }

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def get_financials(self, ticker: str) -> EODHDFinancials:
        base = ticker.upper()
        env_mock = os.environ.get("USE_MOCK_DATA", "").lower()
        use_mock = settings.USE_MOCK_DATA
        if env_mock in ("true", "1"):
            use_mock = True
        elif env_mock in ("false", "0"):
            use_mock = False
        if use_mock:
            logger.debug("Free mode: using mock data for %s", base)
            return self._mock_data(base)

        # Versuch 1: yfinance
        result = await self._try_yfinance(base)
        if result:
            return result

        # Versuch 2: SEC EDGAR (nur US-Ticker)
        result = await self._try_sec_edgar(base)
        if result:
            return result

        # Fallback: Mock
        logger.warning("All free providers failed for %s. Using mock.", base)
        return self._mock_data(base)

    async def _try_yfinance(self, ticker: str) -> Optional[EODHDFinancials]:
        try:
            import yfinance as yf
            loop = __import__("asyncio").get_event_loop()
            info = await loop.run_in_executor(None, lambda: yf.Ticker(ticker).info)
            if not info or info.get("regularMarketPrice") is None:
                logger.debug("yfinance: %s returned empty/invalid info", ticker)
                return None
            return EODHDFinancials(
                ticker=ticker,
                pe_ratio=info.get("trailingPE"),
                debt_to_equity=info.get("debtToEquity"),
                revenue_growth_yoy=info.get("revenueGrowth"),
                market_cap_usd=info.get("marketCap"),
                gross_margin=info.get("grossMargins"),
                net_margin=info.get("profitMargins"),
                source="yfinance"
            )
        except ImportError:
            logger.warning("yfinance not installed. Use: pip install yfinance")
            return None
        except Exception as e:
            logger.debug("yfinance error for %s: %s", ticker, e)
            return None

    async def _try_sec_edgar(self, ticker: str) -> Optional[EODHDFinancials]:
        cik = self.SEC_CIKS.get(ticker.upper())
        if not cik:
            logger.debug("SEC EDGAR: no CIK mapping for %s", ticker)
            return None
        try:
            client = self._get_client()
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            resp = await client.get(url, headers=self.SEC_HEADERS)
            resp.raise_for_status()
            data = resp.json()
            facts = data.get("facts", {}).get("us-gaap", {})

            pe = self._sec_latest(facts, "PriceEarningsRatio")
            d_e = self._sec_latest(facts, "DebtToEquity")
            rev_growth = self._sec_latest_usd(facts, "RevenueFromContractWithCustomerExcludingAssessedTax")
            mcap = self._sec_latest_usd(facts, "MarketCapitalization")
            gp = self._sec_latest_usd(facts, "GrossProfit")
            rev = self._sec_latest_usd(facts, "RevenueFromContractWithCustomerExcludingAssessedTax")
            ni = self._sec_latest_usd(facts, "NetIncomeLoss")

            gm = round(gp / rev, 4) if gp and rev else None
            nm = round(ni / rev, 4) if ni and rev else None

            result = EODHDFinancials(
                ticker=ticker,
                pe_ratio=float(pe) if pe else None,
                debt_to_equity=float(d_e) if d_e else None,
                revenue_growth_yoy=float(rev_growth) if rev_growth else None,
                market_cap_usd=float(mcap) if mcap else None,
                gross_margin=gm,
                net_margin=nm,
                source="sec_edgar"
            )
            return result if result.pe_ratio or result.market_cap_usd else None
        except Exception as e:
            logger.debug("SEC EDGAR error for %s: %s", ticker, e)
            return None

    @staticmethod
    def _sec_latest(facts: dict, key: str):
        units = facts.get(key, {}).get("units", {})
        for unit_key in ["USD", "pure", "shares"]:
            entries = units.get(unit_key, [])
            if entries:
                return entries[-1].get("val")
        return None

    @staticmethod
    def _sec_latest_usd(facts: dict, key: str) -> Optional[float]:
        units = facts.get(key, {}).get("units", {})
        entries = units.get("USD", [])
        if entries:
            val = entries[-1].get("val")
            return float(val) if val else None
        return None

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @staticmethod
    def _mock_data(ticker: str) -> EODHDFinancials:
        mocks = {
            "TSLA": EODHDFinancials(ticker="TSLA", pe_ratio=62.4, debt_to_equity=0.12,
                revenue_growth_yoy=0.19, market_cap_usd=800_000_000_000,
                gross_margin=0.19, net_margin=0.15, source="mock"),
            "AAPL": EODHDFinancials(ticker="AAPL", pe_ratio=29.8, debt_to_equity=1.81,
                revenue_growth_yoy=0.02, market_cap_usd=3_200_000_000_000,
                gross_margin=0.46, net_margin=0.26, source="mock"),
            "MSFT": EODHDFinancials(ticker="MSFT", pe_ratio=35.2, debt_to_equity=0.28,
                revenue_growth_yoy=0.16, market_cap_usd=3_100_000_000_000,
                gross_margin=0.70, net_margin=0.36, source="mock"),
        }
        return mocks.get(ticker.upper(), EODHDFinancials(
            ticker=ticker, pe_ratio=18.5, debt_to_equity=0.42,
            revenue_growth_yoy=0.25, market_cap_usd=850_000_000,
            gross_margin=0.78, net_margin=0.18, source="mock"))


# Alias for backward compatibility
EODHDConnector = FreeDataProvider
