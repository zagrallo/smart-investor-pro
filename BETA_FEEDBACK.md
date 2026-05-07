# Beta-Feedback Template

Use this template to report issues, suggestions, or observations during the beta.

---

## Feedback

**User-ID:** `beta-XXX`
**Timestamp:** `2026-MM-DD HH:MM`
**Correlation-ID:** `...` (from `X-Correlation-ID` response header)

### Input

```
Investment idea or ticker used:
```

### Expected

```
What did you expect to happen?
```

### Actual

```
What actually happened?
```

### Environment

- **Browser/Client:** Chrome 124 / curl / Postman
- **API Base URL:** http://localhost:8000
- **Provider:** mock / deepseek (live)
- **Dashboard:** dashboard.html (DE / FR)

### Support Info (if error)

```
Response status code:
Response body:
```

### Suggestion

```
How could we improve this?
```

---

## Known Quirks (Beta v0.2.0)

| Issue | Status |
|-------|--------|
| Rate limit: 5 req/min per IP | By design (configurable via `MAX_REQUESTS_PER_MINUTE`) |
| Mock mode: returns static `MockCorp AG` | Expected when `DEEPSEEK_API_KEY` is empty |
| EODHD: ticker data is mock | Until `EODHD_API_KEY` is configured |
| PDF: 9 sections always generated | Section content depends on LLM output quality |
