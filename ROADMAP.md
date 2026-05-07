# Roadmap v0.3 – Smart Investor Pro MVP

## Vision
Vom Einzelplatz-Investment-Tool zur kollaborativen Analyse-Plattform mit Multi-LLM-Unterstützung, Echtzeitdaten und Team-Features.

---

## Phased Plan

### 🚩 Phase 1: Multi-LLM Engine (2 Wochen)
**Ziel:** Parallel-Analyse mit mehreren LLMs + automatischem Vergleich

- [ ] **Multi-LLM Router** – Gleichzeitige Anfrage an DeepSeek + ChatGPT + Claude
- [ ] **Consensus Scoring** – Gewichtete Aggregation der Ergebnisse
- [ ] **Cost Optimization** – Günstigeres Modell für Pre-Screening, teures für Finale
- [ ] **LLM Health Checks** – Automatische Erkennung von API-Timeouts/Degradation

**Config-Beispiel:**
```yaml
llms:
  - provider: deepseek
    model: deepseek-chat
    cost_per_1k: 0.00014
    role: screening
  - provider: openai
    model: gpt-4o-mini
    cost_per_1k: 0.00015
    role: final
```

---

### 🚩 Phase 2: Redis-Cache Layer (1 Woche)
**Ziel:** Antwortzeiten < 2s für häufige Ticker, weniger API-Calls

- [ ] **yfinance-Response-Cache** – 24h TTL für Fundamental-Daten
- [ ] **LLM-Response-Cache** – Identische Prompts werden gecached (Hash-basiert)
- [ ] **Rate-Limiter 2.0** – Token-Bucket statt Fixed-Window
- [ ] **Health-Dashboard** – Cache-Hit-Rate, API-Latenzen, Cost-Tracking

**Flow:**
```
Request → Redis Cache (Hit?) → LLM (Miss?) → Response → Cache Save
```

---

### 🚩 Phase 3: Portfolio & Watchlists (2 Wochen)
**Ziel:** Mehrere Ticker gleichzeitig verwalten und überwachen

- [ ] **Watchlist-Manager** – CRUD für Watchlists mit bis zu 20 Ticker
- [ ] **Batch-Analyse** – Ein Prompt für N Ticker (Cost-Sharing)
- [ ] **Portfolio-Snapshot** – Aktuelle Bewertung aller Positionen
- [ ] **Change-Detection** – Automatischer Re-Check bei Kursbewegungen >5%

**UI (Dashboard):**
```
┌─────────────────────────────────────┐
│ Portfolio: 8 Positionen            │
│ Gesamtwert: $124.500               │
│ Letzte Aktualisierung: 2min ago    │
├─────────────────────────────────────┤
│ AAPL ▲ +2.3%  |  TSLA ▼ -1.1%     │
│ MSFT ▲ +0.8%  |  SAP  ▲ +3.2%     │
└─────────────────────────────────────┘
```

---

### 🚩 Phase 4: PDF 2.0 & Reporting (1 Woche)
**Ziel:** Investment-Grade PDFs mit Charts und Internationalisierung

- [ ] **Chart.js Integration** – Kursverlauf, PEG-Ratio, Margen-Entwicklung
- [ ] **Multi-Sprache** – DE/EN PDF-Vorlagen
- [ ] **Export-Formate** – JSON, CSV, PDF, DOCX
- [ ] **Scheduled Reports** – Wöchentliches PDF per E-Mail (via Mailgun/SendGrid)

---

### 🚩 Phase 5: Auth & Multi-User (2 Wochen)
**Ziel:** Team-fähig mit geteilten Analysen und Rollen

- [ ] **User-Registration** – Signup/Login mit E-Mail
- [ ] **Team-Räume** – Shared Workspace für 2-5 Nutzer
- [ ] **Rollensystem** – Admin / Analyst / Viewer
- [ ] **Shared Audit-Log** – Transparente Nachvollziehbarkeit

---

## Technische Schulden (parallel)
- [x] **Done:** FreeDataProvider statt EODHD
- [x] **Done:** Generische LLM-Konfiguration
- [ ] Python-Typen konsolidieren (Optional[str] vs str | None)
- [ ] Pydantic v2 Migration abschliessen
- [ ] Logging-Struktur vereinheitlichen
- [ ] Rate-Limiter auf aiocache umstellen

---

## Release-Plan

| Version | Fokus | Zieltermin |
|---------|-------|------------|
| v0.2.0  | Free Data + Dual-LLM | ✅ LIVE |
| v0.3.0  | Multi-LLM + Redis-Cache | Q3 2026 |
| v0.4.0  | Portfolio + Watchlists | Q4 2026 |
| v0.5.0  | PDF 2.0 + Reporting | Q1 2027 |
| v1.0.0  | Multi-User + Production | Q2 2027 |

---

## Mitmachen?
Issues und PRs willkommen! Bei Fragen: hlifchic@gmail.com
