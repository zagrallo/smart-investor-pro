<p align="center">
  <img src="dy/demo/01-dashboard-start.png" alt="Smart Investor Pro Dashboard" width="800">
</p>

<h1 align="center">🚀 Smart Investor Pro</h1>

<p align="center">
  <strong>AI-Powered Due Diligence & Investment Analysis Platform</strong><br>
  <em>Equity Analysis · Startup DD · Multi-LLM · Multilingual (DE/EN/FR/AR/TR)</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.14+-blue?logo=python">
  <img src="https://img.shields.io/badge/FastAPI-0.136+-green?logo=fastapi">
  <img src="https://img.shields.io/badge/DeepSeek-Gemini-purple">
  <img src="https://img.shields.io/badge/MiFID_II-Compliant-yellow">
  <img src="https://img.shields.io/badge/Status-Active-success">
</p>

---

## 📋 Table of Contents

- [EN – English](#english)
- [DE – Deutsch](#deutsch)
- [AR – العربية](#arabic)

---

<a name="english"></a>

## 🇬🇧 English — Overview

**Smart Investor Pro** is a full-stack investment analysis platform that performs AI-powered due diligence for both **public equities** and **private startups** — in one unified dashboard.

### ✨ Features

| Feature | Description |
|---------|-------------|
| **🔹 Equity Analysis** | Analyze any publicly traded company by ticker. Gets live market data (P/E, D/E, revenue growth, market cap) and generates a structured InvestmentMemo with risk assessment, competitive analysis, and recommendation. |
| **🔹 Startup DD** | Paste a business plan or upload `.md` files for AI-powered venture capital due diligence. Calculates scorecards, radar charts, unit economics, and projections. Supports multi-file sessions. |
| **🔹 Multi-LLM Engine** | Runs **DeepSeek** and **Gemini 2.0 Flash** in parallel. Combines results via weighted consensus scoring with agreement checks. Automatic fallback if one provider fails. |
| **🔹 PDF Reports** | Generates professional 9-section PDF reports for both equities and startups. MiFID II compliant. |
| **🔹 Multilingual UI** | Full i18n support: **Deutsch · English · Français · العربية · Türkçe**. UI language and output language are independently selectable. |
| **🔹 Session Management** | Sessions persist to disk (`data/sessions/*.json`). Upload multiple documents, run analysis, and come back later. |
| **🔹 Audit Trail** | Immutable audit chain with SHA-256 hashing for compliance tracking. |
| **🔹 Security** | JWT authentication, rate limiting (20 req/min), input sanitization against prompt injection, file upload validation. |

### 🖼️ Screenshots

| View | Screenshot |
|------|-----------|
| **Dashboard Start** – Mode selector, equity input | ![Dashboard](dy/demo/01-dashboard-start.png) |
| **Startup Mode** – Paste business plan | ![Startup Mode](dy/demo/02-startup-mode.png) |
| **Startup Analysis Result** – Investment memo with risks, strengths, scorecard | ![Analysis Result](dy/demo/04-analysis-result.png) |
| **German UI** – Full German interface | ![German UI](dy/demo/05-german-ui.png) |
| **Arabic UI** – Full Arabic interface (RTL) | ![Arabic UI](dy/demo/06-arabic-ui.png) |
| **UI=English, Output=German** – Independent language selection | ![Output DE](dy/demo/07-output-lang-de.png) |
| **Equity Mode** – Stock analysis with ticker | ![Equity Mode](dy/demo/08-equity-mode.png) |

### 🧠 How It Works

```
User Input ──► Frontend (Dashboard)
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   Equity       Startup    Session
   Analysis     DD         Manager
        │          │          │
        ▼          ▼          │
   ┌────────────────────┐     │
   │  Multi-LLM Router  │◄────┘
   │  (DeepSeek/Gemini) │
   └────────┬───────────┘
            ▼
   ┌────────────────┐
   │  Parser +      │
   │  Compliance    │
   └────────┬───────┘
            ▼
   ┌──────────────────────────┐
   │  PDF Report / Dashboard  │
   │  Display / Audit Log     │
   └──────────────────────────┘
```

### 🏗️ Architecture

```
smart-investor-mvp/
├── main.py                     # FastAPI app entrypoint
├── agents.py                   # InvestmentAgent orchestrator
├── models.py                   # Pydantic schemas (InvestmentMemo, RiskAssessment)
├── compliance.py               # Audit chain, input sanitization, market data
├── reports.py                  # PDF generation (ReportLab)
├── llm_router.py               # LLM routing (deprecated → startup_dd/router.py)
├── dashboard.html              # Full single-page application UI
├── config/                     # Environment-aware settings
├── locales/                    # i18n: de.json, en.json, fr.json, ar.json, tr.json
├── data/
│   └── json_parser.py          # JSON recovery & field remapping
├── startup_dd/
│   ├── startup_schema.py       # Startup-specific Pydantic models
│   ├── startup_agent.py        # Startup analysis orchestrator
│   ├── router.py               # MultiLLMRouter (parallel execution)
│   ├── consensus.py            # Weighted consensus scoring
│   ├── vc_prompt.py            # VC system prompts (5 languages)
│   ├── document_parser.py      # Regex metric extraction
│   ├── evaluator.py            # Weighted startup scoring
│   ├── visuals.py              # Scorecard/radar/unit economics
│   ├── dashboard_html.py       # HTML dashboard generator
│   ├── cache.py                # Redis/in-memory cache
│   ├── session_store.py        # Session persistence
│   └── reports.py              # Startup PDF generation
└── tests/
    ├── test_api.py             # API endpoint tests (11)
    ├── test_security.py        # Security tests (JWT, injection, CORS) (56)
    └── test_v04.py             # Visual/consensus tests (5)
```

### 🚀 Quick Start

```bash
# Clone & enter
git clone https://github.com/zagrallo/smart-investor-pro.git
cd smart-investor-mvp

# Install dependencies
pip install -r requirements.txt

# Configure API keys + Neon DB (.env)
# DEEPSEEK_API_KEY=sk-...
# GEMINI_API_KEY=...
# DATABASE_URL=postgresql://... (Neon)

# Run locally
uvicorn main:app --host 0.0.0.0 --port 8000

# Deploy to Vercel
# 1. Push to GitHub
# 2. Import repo in Vercel
# 3. Set env vars in Vercel dashboard:
#    DEEPSEEK_API_KEY, GEMINI_API_KEY, DATABASE_URL, SECRET_KEY, APP_ENV=production
# 4. Deploy – Vercel auto-detects Python
```

### 🧪 Tests

```bash
# All tests
pytest tests/ --ignore=tests/load_test.py

# Individual suites
pytest tests/test_api.py -v         # 11 endpoint tests
pytest tests/test_security.py -v    # 56 security tests
pytest tests/test_v04.py -v         # 5 visual/consensus tests
```

**Results: 71/71 tests passing** ✅

### 🔧 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.14+, FastAPI, Uvicorn |
| **LLM** | DeepSeek V3 + Gemini 2.0 Flash (parallel) |
| **Frontend** | Vanilla JS, CSS custom properties, i18n |
| **PDF** | ReportLab |
| **Auth** | JWT (python-jose), HTTPBearer |
| **Database** | PostgreSQL (Neon via asyncpg) |
| **Session** | PostgreSQL (Neon via asyncpg) |
| **Cache** | Redis (optional, in-memory fallback) |

---

<a name="deutsch"></a>

## 🇩🇪 Deutsch — Überblick

**Smart Investor Pro** ist eine Full-Stack-Plattform für KI-gestützte Investment-Analysen — sowohl für **börsennotierte Aktien** als auch für **private Startups** — in einem einheitlichen Dashboard.

### ✨ Funktionen

| Funktion | Beschreibung |
|----------|-------------|
| **🔹 Aktienanalyse** | Analysiere jedes börsennotierte Unternehmen per Ticker. Live-Marktdaten (KGV, VK, Umsatzwachstum, Marktkap.) + strukturiertes InvestmentMemo mit Risikobewertung, Wettbewerbsanalyse und Empfehlung. |
| **🔹 Startup DD** | Businessplan einfügen oder `.md`-Dateien hochladen für KI-gestützte Venture-Capital-Due-Diligence. Scorecard, Radar-Chart, Unit Economics und Projektionen. |
| **🔹 Multi-LLM Engine** | **DeepSeek** und **Gemini 2.0 Flash** parallel. Ergebnisse via Weighted-Consensus-Scoring kombiniert. Automatischer Fallback bei Ausfall. |
| **🔹 PDF-Reports** | Professionelle 9-seitige PDF-Reports für Aktien und Startups. MiFID II-konform. |
| **🔹 Mehrsprachig** | Vollständige i18n: **Deutsch · English · Français · العربية · Türkçe**. UI- und Ausgabesprache unabhängig wählbar. |
| **🔹 Session-Management** | Sessions persistent auf Disk (`data/sessions/*.json`). Mehrere Dokumente hochladen, analysieren, später fortsetzen. |
| **🔹 Audit-Trail** | Unveränderliche Audit-Kette mit SHA-256-Hashing für Compliance. |
| **🔹 Sicherheit** | JWT-Authentifizierung, Rate-Limiting (20 Anfragen/min), Input-Sanitisierung gegen Prompt-Injection, Datei-Validierung. |

### 🖼️ Screenshots

| Ansicht | Screenshot |
|---------|-----------|
| **Dashboard Start** – Modusauswahl, Aktieneingabe | ![Dashboard](dy/demo/01-dashboard-start.png) |
| **Startup-Modus** – Businessplan einfügen | ![Startup Modus](dy/demo/02-startup-mode.png) |
| **Analyse-Ergebnis** – Memo mit Risiken, Stärken, Scorecard | ![Analyse Ergebnis](dy/demo/04-analysis-result.png) |
| **Deutsches UI** – Komplette deutsche Oberfläche | ![Deutsches UI](dy/demo/05-german-ui.png) |
| **Arabisches UI** – Komplette arabische Oberfläche (RTL) | ![Arabisches UI](dy/demo/06-arabic-ui.png) |
| **UI=Englisch, Ausgabe=Deutsch** – Getrennte Sprachwahl | ![Ausgabe DE](dy/demo/07-output-lang-de.png) |
| **Aktien-Modus** – Aktienanalyse mit Ticker | ![Aktien Modus](dy/demo/08-equity-mode.png) |

### 🚀 Schnellstart

```bash
git clone https://github.com/zagrallo/smart-investor-pro.git
cd smart-investor-mvp
pip install -r requirements.txt

# .env anlegen mit: DEEPSEEK_API_KEY=... und/oder GEMINI_API_KEY=...
uvicorn main:app --host 0.0.0.0 --port 8000
# http://localhost:8000
```

### 🧪 Tests

```bash
pytest tests/ --ignore=tests/load_test.py   # 71 Tests, alle ✅
```

---

<a name="arabic"></a>

## 🇸🇦 العربية — نظرة عامة

**Smart Investor Pro** منصة متكاملة للتحليل الاستثماري تعمل بالذكاء الاصطناعي، وتُجري العناية الواجبة للأسهم المدرجة في البورصة والشركات الناشئة على حد سواء، كل ذلك عبر لوحة تحكم موحدة.

### ✨ الميزات

| الميزة | الشرح |
|--------|-------|
| **🔹 تحليل الأسهم** | حلّل أي شركة مدرجة في البورصة باستخدام رمزها. تسحب المنصة بيانات السوق الحية (مكرر الربحية، الرفع المالي، نمو الإيرادات، القيمة السوقية) وتُنتج مذكرة استثمارية متكاملة تتضمن تقييم المخاطر وتحليل المنافسة وتوصية واضحة. |
| **🔹 العناية بالشركات الناشئة** | ألصق خطة العمل أو حمّل ملفات `.md` للتحليل الاستثماري. تحسب المنصة بطاقة أداء شاملة ورسوماً رادارية واقتصاديات الوحدة والتوقعات المالية. تدعم جلسات متعددة الملفات. |
| **🔹 محرك ذكاء متعدد** | تشغّل **DeepSeek** و **Gemini 2.0 Flash** بالتوازي، ثم تدمج النتائج عبر الترجيح التوافقي. تعمل تلقائياً حتى لو تعطل أحد المزوّدين. |
| **🔹 تقارير PDF** | تُولّد تقارير PDF احترافية من 9 أقسام للأسهم والشركات الناشئة، متوافقة مع معايير MiFID II الأوروبية. |
| **🔹 تعدد اللغات** | دعم كامل لـ: **Deutsch · English · Français · العربية · Türkçe**. يمكنك اختيار لغة الواجهة ولغة المخرجات بشكل منفصل. |
| **🔹 إدارة الجلسات** | الجلسات محفوظة على القرص (`data/sessions/*.json`). حمّل مستندات متعددة، حلّل البيانات، ثم عد إليها لاحقاً. |
| **🔹 سجل التدقيق** | سجل تدقيق غير قابل للتعديل مع تشفير SHA-256 لمتطلبات الامتثال التنظيمي. |
| **🔹 الأمان** | توثيق JWT، تحديد عدد الطلبات (20/دقيقة)، تنقية المدخلات ضد هجمات الحقن، والتحقق من صحة الملفات المرفوعة. |

### 🖼️ لقطات الشاشة

| المنظر | الصورة |
|--------|--------|
| **الصفحة الرئيسية** | ![الشاشة الرئيسية](dy/demo/01-dashboard-start.png) |
| **وضع الشركة الناشئة** | ![وضع الناشئة](dy/demo/02-startup-mode.png) |
| **نتيجة التحليل** | ![النتيجة](dy/demo/04-analysis-result.png) |
| **الواجهة بالألمانية** | ![الألمانية](dy/demo/05-german-ui.png) |
| **الواجهة بالعربية** | ![العربية](dy/demo/06-arabic-ui.png) |
| **الواجهة بالإنجليزية والمخرجات بالألمانية** | ![فصل اللغات](dy/demo/07-output-lang-de.png) |
| **وضع الأسهم** | ![الأسهم](dy/demo/08-equity-mode.png) |

### 🚀 بداية سريعة

```bash
git clone https://github.com/zagrallo/smart-investor-pro.git
cd smart-investor-mvp
pip install -r requirements.txt

# أضف مفاتيح API في ملف .env: DEEPSEEK_API_KEY=...  GEMINI_API_KEY=...
uvicorn main:app --host 0.0.0.0 --port 8000
# افتح المتصفح على: http://localhost:8000
```

### 🧪 الاختبارات

```bash
pytest tests/ --ignore=tests/load_test.py   # 71 اختباراً، جميعها ناجحة ✅
```

---

## 📄 License

MIT

## 🙏 Acknowledgements

- [DeepSeek](https://deepseek.com/) for LLM API
- [Google Gemini](https://deepmind.google/gemini/) for LLM API
- [ReportLab](https://www.reportlab.com/) for PDF generation
- [FastAPI](https://fastapi.tiangolo.com/) for the backend framework
