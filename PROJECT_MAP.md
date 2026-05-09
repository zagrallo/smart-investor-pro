# PROJECT_MAP.md – Smart Investor Pro v0.4.0

> Generated: 2026-05-08 | Status: VISUAL + MULTI-LLM ENHANCED

---

## [TECH_STACK]

### Core Dependencies (Pinned – Mai 2026)

| Paket | Version | Status |
|-------|---------|--------|
| `fastapi` | `>=0.136.1` | ✅ |
| `pydantic` | `>=2.13.4` | ✅ |
| `openai` | `>=2.35.0` | ✅ (DeepSeek) |
| `reportlab` | `>=4.4.10` | ✅ |
| `python-jose[cryptography]` | `>=3.5.0` | ✅ |
| `aiosqlite` | `>=0.20.0` | ✅ |
| `httpx` | `>=0.28.1` | ✅ |
| `tenacity` | `>=9.1.4` | ✅ |
| `pytest` / `pytest-asyncio` | latest | ✅ |

**Python:** >=3.10 (target 3.12-slim in Docker)

---

## [ARCHITECTURE]

```
smart-investor-mvp/
├── main.py                  # FastAPI app, v1 Router, JSON Logging, Rate Limit
├── config/                  # Environment-aware settings (dev/prod)
│   ├── __init__.py          # Exports settings based on APP_ENV
│   └── base.py             # Settings + ProductionSettings
├── models.py               # InvestmentMemo, RiskAssessment, AuditEntry
├── llm_router.py           # DeepSeek + mock fallback + JSON parser
├── agents.py               # Analysis orchestrator
├── compliance.py           # Audit chain, sanitization, EODHD connector
├── reports.py              # 9-section PDF generation
├── startup_dd/
│   ├── startup_schema.py     # StartupInvestmentMemo, StartupMetrics, Recommendation, VisualMetrics
│   ├── startup_agent.py      # StartupAgent (Analysen + Visuals)
│   ├── vc_prompt.py          # VC-System-Prompt (DE)
│   ├── document_parser.py    # Regex-Metrik-Extraktion
│   ├── evaluator.py          # Gewichtete Startup-Bewertung
│   ├── router.py             # MultiLLMRouter (DeepSeek + Gemini + Cache)
│   ├── consensus.py          # Weighted Consensus Scoring + Agreement Check
│   ├── visuals.py            # Scorecard/Radar/Unit Economics Calculator
│   ├── dashboard_html.py     # Interactive HTML Dashboard Generator
│   ├── cache.py              # Redis/In-Memory Cache Layer
│   ├── reports.py            # Startup PDF Generation (mit Scorecard)
│   └── __init__.py
├── data/
│   ├── eodhd_connector.py  # Async EODHD API + ticker mocks
│   └── json_parser.py      # 3-strategy JSON extraction
├── tests/
│   ├── test_api.py         # 11 tests (v1 routes, rate-limit, JSON logging)
│   └── load_test.py        # CLI load test (argparse)
├── dashboard.html          # DE/FR frontend, API key placeholder
├── BETA_FEEDBACK.md        # Beta test template
├── Dockerfile              # Multi-stage, non-root
├── docker-compose.yml      # Healthcheck, volume
└── .env.example            # All config keys documented
```

---

## [SYSTEM_FLOW]

```
User → dashboard.html (DE/FR)
    │ POST /auth/token → JWT
    │ POST /v1/analyze  → Due Diligence
    │   ├── Sanitize input
    │   ├── Extract ticker → EODHD fundamentals
    │   ├── LLM DeepSeek (or mock fallback)
    │   └── Pydantic validation → InvestmentMemo
    │ GET /v1/report/pdf → PDF download
    │ GET /v1/audit     → Chain-hashed audit trail
    │ GET /health       → JSON status (incl. env)
```

**Rate Limiting:** 5 req/min per IP (configurable via `MAX_REQUESTS_PER_MINUTE`)
**Logging:** JSON-structured with correlation ID, ELK-compatible
**Shutdown:** Graceful DB + HTTP client close via FastAPI lifespan

---

## [ORPHANS & PENDING]

| Feature | Status | Notes |
|---------|--------|-------|
| Live Dashboard (Streamlit) | Pending v0.5 | Interactive scenario exploration |
| Competitor Live-Feed | Pending v0.5 | Web-scraping competitor pricing |
| Founder Q&A Generator | Pending v0.5 | KI-generierte Fragen für DD-Calls |
| Pitch-Deck Auto-Export | Pending v0.5 | 10-Folien PPTX aus Memo |
| PostgreSQL | Pending Phase 3 | SQLite adequate for beta |
| E2E Playwright tests | Pending Phase 2 | API coverage is sufficient |
| OAuth2/SSO | Pending Phase 2 | JWT sufficient for beta |
| Stripe billing | Pending Phase 2 | Manual onboarding for beta |

---

## [v0.2.0 CHANGES]

| Change | Files | Rationale |
|--------|-------|-----------|
| Config package | `config.py` → `config/` | Environment-specific dev/prod settings |
| JSON logging | `main.py` | ELK-compatible structured logs |
| API versioning | `main.py`, `tests/`, `dashboard.html` | `/v1/*` for backward-compatible evolution |
| Graceful shutdown | `main.py` (lifespan) | DB + HTTP connections closed safely |
| Load test | `tests/load_test.py` | Performance baseline with CLI args |
| Beta feedback | `BETA_FEEDBACK.md` | Structured bug reporting template |
| Env config | `.env.example` | Added `APP_ENV`, `LOG_LEVEL`, `LOG_FORMAT`, `MAX_REQUESTS_PER_MINUTE` |

## [v0.4.0 CHANGES]

| Change | Files | Rationale |
|--------|-------|-----------|
| Weighted Consensus Engine | `startup_dd/consensus.py` (new) | Weighted scoring + field agreement boost |
| Visual Metrics Calculator | `startup_dd/visuals.py` (new) | Scorecard, Radar, Unit Economics, Projections |
| Interactive HTML Dashboard | `startup_dd/dashboard_html.py` (new) | Chart.js-based investor dashboard |
| Scorecard in PDF | `startup_dd/reports.py` | Enhanced PDF with visual metrics section |
| Schema extended | `startup_dd/startup_schema.py` | Added `visual_metrics: Optional[Dict]` |
| Consensus v2 in Router | `startup_dd/router.py` | Uses `calculate_consensus` with provider agreement |
| Visuals in StartupAgent | `startup_dd/startup_agent.py` | Auto-computes visuals on every analysis |

### API Map

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Service status |
| POST | `/auth/token` | No | JWT token |
| POST | `/v1/analyze` | JWT | Due diligence analysis |
| GET | `/v1/report/pdf` | JWT | PDF report download |
| GET | `/v1/audit` | JWT | Audit trail (chain-hashed) |
| GET | `/docs` | No | OpenAPI UI |
