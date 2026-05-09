import re
import json
import logging
from typing import Dict, Any, Optional, List
from .startup_schema import StartupMetrics

logger = logging.getLogger(__name__)


class StartupDocumentParser:
    """Extrahiert strukturierte Daten aus Startup-Dokumenten mittels Regex + Heuristiken."""

    def parse_pricing(self, content: str) -> List[Dict[str, Any]]:
        tiers = []
        patterns = [
            r'(Starter|Basic|Standard|Professional|Enterprise|Premium)\D*?(\d+[\.\d]*)\s*(?:EUR|Euro|\?|€)',
            r'(\d+)\s*(?:EUR|Euro|\?|€)\s*/?\s*(?:Monat|month)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, content, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    name, price = match[0], match[1]
                else:
                    name, price = f"Tier {len(tiers)+1}", match
                try:
                    price_val = float(price.replace(".", "").replace(",", "."))
                    if 5 <= price_val <= 5000:
                        tiers.append({"plan": name.strip(), "price_eur": price_val})
                except ValueError:
                    continue
        return tiers

    def parse_tam_sam_som(self, content: str) -> Dict[str, Optional[float]]:
        result = {"tam_eur": None, "sam_eur": None, "som_eur_year3": None}
        patterns = [
            (r'TAM\D*?~?\s*([\d,]+\.?\d*)\s*(?:Mrd\.?|Milliarden|Billion)', 1_000_000_000),
            (r'TAM\D*?~?\s*([\d,]+\.?\d*)\s*(?:Mio\.?|Millionen|Million)', 1_000_000),
            (r'SAM\D*?~?\s*([\d,]+\.?\d*)\s*(?:Mrd\.?|Milliarden|Billion)', 1_000_000_000),
            (r'SAM\D*?~?\s*([\d,]+\.?\d*)\s*(?:Mio\.?|Millionen|Million)', 1_000_000),
            (r'SOM\D*?~?\s*([\d,]+\.?\d*)\s*(?:Mrd\.?|Milliarden|Billion)', 1_000_000_000),
            (r'SOM\D*?~?\s*([\d,]+\.?\d*)\s*(?:Mio\.?|Millionen|Million)', 1_000_000),
        ]
        for pattern, multiplier in patterns:
            m = re.search(pattern, content, re.I)
            if m:
                val = float(m.group(1).replace(",", ""))
                key = "tam_eur" if "TAM" in m.group().upper() else \
                      "sam_eur" if "SAM" in m.group().upper() else "som_eur_year3"
                if result[key] is None:
                    result[key] = val * multiplier
        return result

    def parse_funding(self, content: str) -> Dict[str, Optional[float]]:
        result = {"funding_ask_min": None, "funding_ask_max": None, "total_raised_to_date": None}
        patterns = [
            (r'(?:Pre-Seed|Seed|Funding|Investment).{0,40}?(\d[\d.]{2,6})\s*(?:–|-|to|bis)\s*(\d[\d.]{2,6})\s*(?:EUR|Euro|\?|€)', 2),
            (r'(?:Pre-Seed|Seed|Funding|Investment).{0,40}?(\d[\d.]{2,6})\s*(?:EUR|Euro|\?|€)', 1),
            (r'(\d[\d.]{2,6})\s*(?:EUR|Euro|\?|€).{0,30}(?:Pre-Seed|Seed|Funding)', 1),
        ]
        for pattern, groups in patterns:
            m = re.search(pattern, content, re.I)
            if m:
                if groups == 2:
                    result["funding_ask_min"] = float(m.group(1).replace(".", ""))
                    result["funding_ask_max"] = float(m.group(2).replace(".", ""))
                else:
                    val = float(m.group(1).replace(".", ""))
                    if result["funding_ask_min"] is None:
                        result["funding_ask_min"] = val * 0.8
                        result["funding_ask_max"] = val * 1.2
                break
        return result

    def parse_metrics(self, content: str) -> Dict[str, Any]:
        metrics = {}
        patterns = [
            (r'(?:target_)?mrr[_\s]?year[_\s]?1\D*?(\d[\d.,]*)', "projected_mrr_year1"),
            (r'(?:target_)?arr[_\s]?year[_\s]?1\D*?(\d[\d.,]*)', "projected_arr_year1"),
            (r'(?:target_)?arr[_\s]?year[_\s]?3\D*?(\d[\d.,]*)', "projected_arr_year3"),
            (r'(?:target_)?(?:paying_)?customers[_\s]?year[_\s]?1\D*?(\d+)', "target_customers_year1"),
            (r'(?:target_)?(?:paying_)?customers[_\s]?year[_\s]?3\D*?(\d+)', "target_customers_year3"),
            (r'gross[_\s]?margin\D*?(\d+)%?', "gross_margin_target"),
            (r'cac\D*?(\d[\d.,]*)\s*(?:EUR|Euro|\?|€)', "cac_target"),
            (r'ltv\D*?(\d[\d.,]*)\s*(?:EUR|Euro|\?|€)', "ltv_target"),
            (r'(?:ltv[/_])?cac[\s_]?ratio\D*?(\d+[\d.,]*)', "ltv_cac_ratio"),
            (r'payback\D*?(\d+[\d.,]*)\s*(?:months|Monate|Wochen|weeks)', "payback_months"),
            (r'churn\D*?(\d+[\d.,]*)%?', "churn_rate_monthly"),
            (r'(?:monthly_)?churn[_\s]?rate\D*?(\d+[\d.,]*)%?', "churn_rate_monthly"),
        ]
        for pattern, key in patterns:
            m = re.search(pattern, content, re.I)
            if m:
                try:
                    val = float(m.group(1).replace(",", "."))
                    if "payback" in key and "Wochen" in m.group() or "weeks" in m.group():
                        val = val / 4.33
                    if "churn" in key and val > 1:
                        val = val / 100
                    metrics[key] = val
                except ValueError:
                    continue
        return metrics

    def parse_all(self, content: str) -> StartupMetrics:
        data = {}
        data.update(self.parse_tam_sam_som(content))
        data.update(self.parse_funding(content))
        data.update(self.parse_metrics(content))
        data["pricing_tiers"] = self.parse_pricing(content)
        return StartupMetrics(**{k: v for k, v in data.items() if v is not None})
