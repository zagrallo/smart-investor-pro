def generate_dashboard(memo: dict) -> str:
    vm = memo.get("visual_metrics", {})
    radar = vm.get("radar_scores", {})
    unit = vm.get("unit_economics", {})
    proj = vm.get("projections", {})
    metrics = memo.get("metrics", {})
    company = memo.get("company_name", "Startup")
    rec = memo.get("recommendation", "N/A")
    conf = memo.get("confidence_score", 0)
    scorecard = vm.get("scorecard_total", 0)
    risks = memo.get("key_risks", [])
    strengths = memo.get("key_strengths", [])
    questions = memo.get("critical_questions", [])

    risk_rows = "".join(
        f'<tr><td class="risk-{r.get("severity","LOW").lower()}">{r.get("severity","?")}</td>'
        f"<td>{r.get('category','?')}</td>"
        f"<td>{r.get('description','')[:80]}...</td>"
        f"<td>{r.get('mitigation','')[:60]}...</td></tr>"
        for r in risks[:5]
    )
    radar_bars = "".join(
        f"<div class='bar-row'><span class='bar-label'>{k.title()}</span>"
        f"<div class='bar-track'><div class='bar-fill' style='width:{v*10}%'>{v}</div></div></div>"
        for k, v in sorted(radar.items(), key=lambda x: -x[1])
    )
    strengths_html = "".join(f"<li>{s}</li>" for s in strengths[:6])
    questions_html = "".join(f"<li>{q}</li>" for q in questions[:5])

    arr_y1 = proj.get("arr_year1", 0)
    arr_y3 = proj.get("arr_year3", 0)
    cagr = proj.get("cagr_pct", 0)
    churn = proj.get("monthly_churn_pct", 0)
    runway = proj.get("runway_months", "N/A")
    ltv_cac = unit.get("ltv_cac_ratio", 0)
    payback = unit.get("payback_months", 0)
    gm = unit.get("gross_margin_pct", 0)

    rec_color = {"STRONG_INVEST": "#00c853", "INVEST": "#64dd17", "CONDITIONAL_INVEST": "#ffd600", "NEED_MORE_INFO": "#ff9100", "PASS": "#d50000"}.get(rec, "#888")

    return f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{company} – DD Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#f5f5f5; color:#222; }}
.header {{ background:linear-gradient(135deg,#1a1a2e,#16213e); color:#fff; padding:32px 24px; }}
.header h1 {{ font-size:1.8em; }}
.header .meta {{ color:#aaa; font-size:0.9em; margin-top:6px; }}
.scorecard {{ display:inline-block; background:{rec_color}; color:#000; padding:4px 16px; border-radius:20px; font-weight:700; font-size:1.1em; margin-left:12px; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; padding:16px; max-width:1200px; margin:0 auto; }}
.card {{ background:#fff; border-radius:12px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
.card h2 {{ font-size:1.1em; margin-bottom:12px; color:#1a1a2e; border-bottom:2px solid #e94560; padding-bottom:6px; }}
.card.full {{ grid-column:1/-1; }}
.bar-row {{ display:flex; align-items:center; margin:6px 0; }}
.bar-label {{ width:100px; font-size:0.85em; color:#555; }}
.bar-track {{ flex:1; height:22px; background:#eee; border-radius:4px; overflow:hidden; }}
.bar-fill {{ height:100%; background:linear-gradient(90deg,#2E86AB,#e94560); color:#fff; font-size:0.75em; line-height:22px; padding:0 6px; border-radius:4px; text-align:right; }}
table {{ width:100%; border-collapse:collapse; font-size:0.85em; }}
th {{ background:#1a1a2e; color:#fff; padding:8px 6px; text-align:left; }}
td {{ padding:6px; border-bottom:1px solid #eee; }}
.risk-critical {{ color:#d50000; font-weight:700; }}
.risk-high {{ color:#ff6d00; font-weight:700; }}
.risk-medium {{ color:#ffab00; }}
.risk-low {{ color:#558b2f; }}
.kpi-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; text-align:center; }}
.kpi {{ background:#f8f9fa; border-radius:8px; padding:12px; }}
.kpi .value {{ font-size:1.5em; font-weight:700; color:#1a1a2e; }}
.kpi .label {{ font-size:0.75em; color:#888; margin-top:4px; }}
ul {{ padding-left:18px; font-size:0.9em; }}
li {{ margin:6px 0; }}
.chart-container {{ position:relative; height:260px; }}
@media (max-width:768px){{ .grid {{ grid-template-columns:1fr; }} .kpi-grid {{ grid-template-columns:repeat(2,1fr); }} }}
</style></head>
<body>
<div class="header">
<h1>{company} <span class="scorecard">{scorecard}/100</span></h1>
<div class="meta">{rec} | Confidence: {conf:.0%} | {memo.get("sector","?")} | {memo.get("stage","?")}</div>
</div>
<div class="grid">
<div class="card"><h2>Scorecard</h2>{radar_bars}</div>
<div class="card">
<h2>KPIs</h2>
<div class="kpi-grid">
<div class="kpi"><div class="value">{ltv_cac}x</div><div class="label">LTV/CAC</div></div>
<div class="kpi"><div class="value">{payback}</div><div class="label">Payback (mo)</div></div>
<div class="kpi"><div class="value">{gm:.0f}%</div><div class="label">Gross Margin</div></div>
<div class="kpi"><div class="value">{runway}</div><div class="label">Runway (mo)</div></div>
<div class="kpi"><div class="value">&euro;{arr_y1/1000:.0f}k</div><div class="label">ARR Y1</div></div>
<div class="kpi"><div class="value">&euro;{arr_y3/1000:.0f}k</div><div class="label">ARR Y3</div></div>
<div class="kpi"><div class="value">{cagr:.0f}%</div><div class="label">CAGR</div></div>
<div class="kpi"><div class="value">{churn:.1f}%</div><div class="label">Churn/mo</div></div>
</div>
</div>
<div class="card"><h2>Key Strengths</h2><ul>{strengths_html}</ul></div>
<div class="card">
<h2>ARR Projection</h2>
<div class="chart-container"><canvas id="arrChart"></canvas></div>
</div>
<div class="card full">
<h2>Key Risks ({len(risks)})</h2>
<table><tr><th>Severity</th><th>Category</th><th>Description</th><th>Mitigation</th></tr>{risk_rows}</table>
</div>
<div class="card"><h2>Critical Questions</h2><ul>{questions_html}</ul></div>
<div class="card">
<h2>Unit Economics Radar</h2>
<div class="chart-container"><canvas id="unitChart"></canvas></div>
</div>
</div>
<script>
new Chart(document.getElementById('arrChart'),{{type:'bar',data:{{
labels:['Y1','Y2','Y3'],
datasets:[{{
label:'ARR (€)',
data:[{arr_y1},{proj.get("arr_year2",0)},{arr_y3}],
backgroundColor:'#2E86AB',
borderColor:'#1a1a2e',
borderWidth:1
}}]
}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true,ticks:{{callback:v=>'€'+(v/1000).toFixed(0)+'k'}}}}}}}}}});
new Chart(document.getElementById('unitChart'),{{type:'radar',data:{{
labels:['Market','Product','Team','Financials','Competition','Execution'],
datasets:[{{
label:'{company}',
data:[{radar.get("market",5)},{radar.get("product",5)},{radar.get("team",5)},{radar.get("financials",5)},{radar.get("competition",5)},{radar.get("execution",5)}],
backgroundColor:'rgba(46,134,171,0.2)',
borderColor:'#2E86AB',
pointBackgroundColor:'#2E86AB',
pointRadius:4
}}]
}},options:{{responsive:true,maintainAspectRatio:false,scales:{{r:{{beginAtZero:true,max:10}}}}}}}});
</script>
</body></html>"""
