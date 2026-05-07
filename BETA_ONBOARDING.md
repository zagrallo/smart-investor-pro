# Smart Investor Pro – Beta-Tester Onboarding

Welcome to the **Smart Investor Pro MVP v0.2.0** closed beta!

## Quick Start (5 Minuten)

### 1. Voraussetzungen
- Docker & Docker Compose installiert
- Git-Client
- Terminal / PowerShell

### 2. Setup
```bash
git clone https://github.com/zagrallo/smart-investor-pro.git
cd smart-investor-pro
cp .env.example .env
```

### 3. LLM konfigurieren
In `.env` den gewünschten Provider eintragen:

**DeepSeek (empfohlen):**
```
LLM_API_KEY=sk-your-deepseek-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

**Oder ChatGPT:**
```
LLM_API_KEY=sk-proj-your-openai-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

### 4. Starten
```bash
docker compose up --build -d
curl http://localhost:8000/health
```

### 5. Erste Analyse
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/analyze?idea=Analyze+Apple+Inc+(AAPL)+for+a+long-term+value+investment" | python -m json.tool
```

## Testbereiche (Bitte fokussieren)
1. **Datenqualität** – Stimmen PE, MarketCap, Margen aus yfinance?
2. **LLM-Qualität** – Ist das Investment Memo brauchbar?
3. **PDF-Report** – Formatiert, lesbar, vollständig?
4. **Stabilität** – Gibt es Timeouts, Fehler, Abstürze?
5. **Mock-Modus** – Funktioniert auch ohne LLM-API-Key?

## Feedback-Kanäle
- **GitHub Issues**: Bug-Reports, Feature-Wünsche
- **E-Mail**: hlifchic@gmail.com
- **Bewertung**: Nach 1 Woche bitte kurzes Summary per E-Mail

## Bekannte Einschränkungen (v0.2.0)
- yfinance: keine Garantie für Echtzeitdaten (Reverse-Engineered API)
- SEC EDGAR: nur US-Ticker, CIK-Mapping manuell
- Aktuell Single-User (kein Multi-Tenant)
- Kein Caching (wird in v0.3 kommen)

## Sicherheit & Compliance
- Alle Audits in SQLite mit SHA-256 Hash-Chain
- MiFID II Disclaimer auf jedem PDF
- Rate-Limit: 5 Requests/Minute/IP
- Prompt-Injection Filter aktiv

---

**Vielen Dank fürs Testen! 🚀**
