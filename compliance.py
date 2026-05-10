import aiosqlite
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from models import InvestmentMemo
from data.eodhd_connector import EODHDConnector

logger = logging.getLogger(__name__)

DISCLAIMER_EU = (
    "MiFID II/GDPR: Diese Analyse dient ausschliesslich Informationszwecken "
    "und stellt keine Anlageberatung dar. Investitionen bergen Risiken bis "
    "hin zum Totalverlust. Past performance is not indicative of future results."
)


def sanitize_input(text: str, max_len: int = 32000) -> str:
    """Remove potential prompt-injection patterns and limit length."""
    text = re.sub(r"(?i)(system|ignore|override|new\s*instruction|act\s*as|you\s*are\s*now)\s*[:\]\-]", "", text)
    return text.strip()[:max_len]


class ComplianceEngine:
    def __init__(self):
        self.disclaimer = DISCLAIMER_EU
        self.db_path = "audit.db"
        self.eodhd = EODHDConnector()

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    idea TEXT NOT NULL,
                    model_used TEXT,
                    cost_usd REAL DEFAULT 0,
                    tokens_used INTEGER DEFAULT 0,
                    input_hash TEXT,
                    output_hash TEXT,
                    prev_hash TEXT,
                    chain_hash TEXT,
                    disclaimer_accepted INTEGER DEFAULT 1,
                    jurisdiction TEXT DEFAULT 'EU',
                    timestamp TEXT NOT NULL
                )
            """)
            await db.commit()

    def get_market_context(self, idea: str) -> dict:
        return {
            "status": "EODHD placeholder - async fetch in run_analysis",
            "source": "EODHD Financial Data API",
            "sanitized_idea": sanitize_input(idea)
        }

    async def fetch_market_data(self, ticker: str) -> dict:
        """Async EODHD fetch - non-blocking. Returns empty data for private companies."""
        if not ticker:
            return {"ticker": "", "source": "none", "note": "Private company – no market data available"}
        data = await self.eodhd.get_financials(ticker)
        return data.model_dump()

    TICKER_BLOCKLIST = {"GH", "GMBH", "UG", "SAAS", "KI", "DACH", "SME", "RTL", "SOM",
        "ARR", "MRR", "LTV", "CAC", "TAM", "SAM", "SOM", "PWA", "API",
        "CRM", "ERP", "CEO", "CTO", "CFO", "MVP", "B2B", "B2C", "HTTP", "JSON",
        "D2C", "ROI", "KPI", "SEO", "DSGVO", "GDPR", "MIFID", "GmbH", "GDP",
        "UG", "EV", "EBIT", "EBITDA", "USA", "EU", "UK", "SWOT", "AG",
        "INC", "CORP", "LTD", "LLC", "WAIT", "CLV", "LTV"}

    PRIVATE_KEYWORDS = [
        "pre-seed", "seed", "pre revenue", "pre-revenue",
        "early stage", "startup", "private company",
        "pre seed", "friends and family"
    ]

    def _is_private_company(self, text: str) -> bool:
        lower = text.lower()
        # GmbH/UG/AG im Text → Privatunternehmen (DACH)
        if re.search(r'\b(gmbh|ug|ag|limited|llc|pte\.?\s*ltd)\b', lower):
            return True
        for kw in self.PRIVATE_KEYWORDS:
            if kw in lower:
                return True
        return False

    def extract_ticker(self, idea: str) -> str:
        """Extract ticker from investment idea text. Returns empty string for private companies."""
        if self._is_private_company(idea):
            logger.debug("Private company detected, skipping ticker extraction")
            return ""

        patterns = [
            r"\(([A-Z]{1,5})\)",
            r"ticker[:\s]+([A-Z]{1,5})",
            r"symbol[:\s]+([A-Z]{1,5})",
        ]
        for pattern in patterns:
            match = re.search(pattern, idea)
            if match:
                ticker = match.group(1).upper()
                if ticker not in self.TICKER_BLOCKLIST:
                    return ticker

        # Fallback: Nur nach bekannten Ticker-Format suchen (z.B. "TSLA" in "...Tesla (TSLA)...")
        # aber Blocklist-False-Positives wie "GmbH" → "GH" ignorieren
        words = idea.split()
        for word in words:
            cleaned = re.sub(r"[^A-Z]", "", word)
            if 2 <= len(cleaned) <= 5 and cleaned not in self.TICKER_BLOCKLIST:
                return cleaned
        return ""

    async def save_audit(self, user_id: str, llm_result: dict, idea: str) -> int:
        await self.init_db()
        input_hash = hashlib.sha256(idea.encode()).hexdigest()[:16]
        output_hash = hashlib.sha256(
            json.dumps(llm_result.get("content", ""), default=str).encode()
        ).hexdigest()[:16]

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT chain_hash FROM audits ORDER BY id DESC LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
                prev_hash = row[0] if row else "0" * 64

            chain_payload = f"{user_id}|{llm_result.get('cost_usd', 0)}|{llm_result.get('tokens', 0)}|{prev_hash}|{input_hash}"
            chain_hash = hashlib.sha256(chain_payload.encode()).hexdigest()

            cursor = await db.execute(
                """INSERT INTO audits
                   (user_id, idea, model_used, cost_usd, tokens_used,
                    input_hash, output_hash, prev_hash, chain_hash,
                    disclaimer_accepted, jurisdiction, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'EU', ?)""",
                (
                    f"beta-{user_id}",
                    idea[:500],
                    llm_result.get("model", "unknown"),
                    llm_result.get("cost_usd", 0.0),
                    llm_result.get("tokens", 0),
                    input_hash,
                    output_hash,
                    prev_hash,
                    chain_hash,
                    datetime.now(timezone.utc).isoformat()
                )
            )
            await db.commit()
            return cursor.lastrowid

    async def get_audit_trail(self, user_id: str) -> list[dict]:
        await self.init_db()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM audits WHERE user_id = ? ORDER BY id DESC",
                (f"beta-{user_id}",)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    def check_budget(self, cumulative_cost: float) -> bool:
        from config import settings
        return cumulative_cost <= settings.LLM_COST_BUDGET

    @staticmethod
    def safe_parse_memo(content: str) -> InvestmentMemo:
        from data.json_parser import parse_with_recovery
        result = parse_with_recovery(content, InvestmentMemo)
        if result is not None:
            return result
        logger.error("Failed to parse memo JSON with all strategies")
        return InvestmentMemo(
            company_name="Unknown",
            sector="Unknown",
            investment_thesis="Could not parse LLM response.",
            financial_highlights={},
            market_opportunity="N/A",
            competitive_advantages=[],
            key_risks=[],
            recommended_action="NEED_MORE_INFO",
            confidence_score=0.0
        )

    async def close(self):
        await self.eodhd.close()
