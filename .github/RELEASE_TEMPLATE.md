name: Release v0.2.0
about: Smart Investor Pro MVP – production-ready release
title: "v0.2.0 – Smart Investor Pro MVP"
labels: release
assignees: zagrallo

---

## v0.2.0 – Smart Investor Pro MVP

### Highlights
- **Kostenlose Datenquellen** – yfinance (global) + SEC EDGAR (US) ersetzen EODHD. Keine API-Keys nötig.
- **Dual-LLM Support** – DeepSeek oder ChatGPT via `.env` umschaltbar, kein Code-Change.
- **FreeDataProvider** – 3-stufige Fallback-Kette: yfinance → SEC EDGAR → Mock.
- **PDF-Report Engine** – 9-Sektion Investment Memo, MiFID II-konform, ReportLab.
- **Audit-Trail** – SHA-256 Hash-Chain, manipulationssichere Logs in SQLite.
- **Rate-Limiting** – 5 req/min + Input-Sanitization gegen Prompt-Injection.

### Neu seit v0.1.0
| Änderung | Details |
|----------|---------|
| `data/eodhd_connector.py` | Vollständig auf FreeDataProvider umgestellt |
| `llm_router.py` | `LLM_*` Env-Vars mit Fallback zu `DEEPSEEK_*` |
| `reports.py` | EODHD-Referenzen entfernt, FreeDataProvider-Doku |
| `config/base.py` | Generische LLM-Konfiguration hinzugefügt |
| `.env.example` | Dual-LLM (DeepSeek/ChatGPT) dokumentiert |

### Technische Daten
- **Stack**: Python 3.14, FastAPI, SQLite, ReportLab, yfinance
- **Tests**: 11/11 pytest, alle grün
- **Deployment**: Docker + docker-compose
- **Dokumentation**: OpenAPI unter `/docs`

### Quick-Start
```bash
cp .env.example .env
# LLM_API_KEY setzen (DeepSeek oder ChatGPT)
docker compose up --build -d
curl http://localhost:8000/health
```

### Dateien (8 Core Files)
`main.py` `compliance.py` `llm_router.py` `models.py` `reports.py`
`data/eodhd_connector.py` `config/` `tests/test_api.py`
