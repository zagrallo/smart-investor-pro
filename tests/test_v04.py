"""Regression test for v0.4: Consensus + Visuals + PDF + Dashboard."""
import asyncio
import json
import sys

sys.path.insert(0, r"C:\Users\hlifc\OneDrive\Desktop\markt geschäft\smart-investor-mvp")

from startup_dd.consensus import calculate_consensus
from startup_dd.visuals import compute_visuals
from startup_dd.dashboard_html import generate_dashboard
from startup_dd.reports import generate_startup_pdf
from startup_dd.startup_schema import StartupInvestmentMemo

MOCK_MEMO = {
    "company_name": "Generic Startup",
    "sector": "Technology / SaaS",
    "stage": "pre_seed",
    "investment_thesis": "DSGVO-konforme All-in-One-Plattform.",
    "recommendation": "CONDITIONAL_INVEST",
    "confidence_score": 0.76,
    "metrics": {
        "tam_eur": 2_400_000_000,
        "sam_eur": 480_000_000,
        "pricing_tiers": [{"plan": "Starter", "price_eur": 29}],
        "projected_arr_year1": 148_000,
        "projected_arr_year3": 2_167_000,
        "cac_target": 52,
        "ltv_target": 2_028,
        "ltv_cac_ratio": 39,
        "payback_weeks": 6,
        "gross_margin_pct": 78,
        "churn_rate_monthly": 2.5,
        "funding_ask_max": 200_000,
        "burn_rate_monthly": 7_500,
        "target_customers_year1": 190,
        "target_customers_year3": 2_200,
    },
    "key_strengths": ["All-in-One Plattform", "DSGVO-nativ", "7 Sprachen", "WhatsApp KI-Chatbot", "Starke Unit Economics", "MVP fertig"],
    "key_risks": [
        {"category": "Team", "severity": "HIGH", "description": "Platzhalter im Dokument", "mitigation": "Founder-Calls vor Investment"},
        {"category": "Traction", "severity": "MEDIUM", "description": "Keine zahlenden Kunden", "mitigation": "Pilot-Meilenstein"},
    ],
    "dd_checklist": {"financials_verified": False, "team_background_checked": False, "legal_dsgvo_audited": True},
    "requested_documents": ["Cap Table", "Financial Model", "Gruender-Lebenslaeufe"],
    "critical_questions": ["Wie wird Kundenakquise umgesetzt?", "Was passiert bei Timify-Nachzug?", "Equity fuer CTO-Hire?"],
}

MOCK_PROVIDER_RESULTS = {
    "deepseek": {"success": True, "parsed": StartupInvestmentMemo(**{**MOCK_MEMO, "confidence_score": 0.76, "recommendation": "CONDITIONAL_INVEST"})},
    "gemini": {"success": True, "parsed": StartupInvestmentMemo(**{**MOCK_MEMO, "confidence_score": 0.81, "recommendation": "INVEST"})},
}


def test_consensus():
    result = calculate_consensus(MOCK_PROVIDER_RESULTS)
    assert result["confidence_score"] > 0.75
    assert result["agreement_pct"] > 0
    assert result["winner"] in ("deepseek", "gemini")
    assert result["method"] == "weighted_average_with_boost"
    print(f"  Consensus: conf={result['confidence_score']} rec={result['recommendation']} agree={result['agreement_pct']}% winner={result['winner']}")


def test_visuals():
    vm = compute_visuals(MOCK_MEMO)
    assert "scorecard_total" in vm
    assert "radar_scores" in vm
    assert "unit_economics" in vm
    assert "projections" in vm
    assert 0 <= vm["scorecard_total"] <= 100
    print(f"  Scorecard: {vm['scorecard_total']}/100")
    print(f"  Radar: {vm['radar_scores']}")
    print(f"  Unit Economics: LTV/CAC {vm['unit_economics']['ltv_cac_ratio']}:1")


def test_dashboard():
    vm = compute_visuals(MOCK_MEMO)
    memo = {**MOCK_MEMO, "visual_metrics": vm}
    html = generate_dashboard(memo)
    assert "<!DOCTYPE html>" in html
    assert "Generic Startup" in html
    assert "chart.js" in html.lower() or "Chart.js" in html
    assert "canvas" in html
    print(f"  Dashboard HTML: {len(html)} chars")


def test_pdf():
    vm = compute_visuals(MOCK_MEMO)
    memo = {**MOCK_MEMO, "visual_metrics": vm}
    pdf = generate_startup_pdf(memo)
    assert len(pdf) > 500
    print(f"  PDF: {len(pdf)} bytes")


def test_schema_extension():
    memo = StartupInvestmentMemo(**MOCK_MEMO)
    assert hasattr(memo, "visual_metrics")
    assert memo.visual_metrics is None
    vm = compute_visuals(memo.model_dump(mode="json"))
    memo.visual_metrics = vm
    dumped = memo.model_dump(mode="json")
    assert "visual_metrics" in dumped
    assert dumped["visual_metrics"]["scorecard_total"] > 0
    print(f"  Schema extension: visual_metrics in model_dump OK")


if __name__ == "__main__":
    print("=== v0.4 Regression Tests ===")
    test_consensus()
    test_visuals()
    test_dashboard()
    test_pdf()
    test_schema_extension()
    print("\nALL TESTS PASSED")
