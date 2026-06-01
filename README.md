# 📈 Automated portfolio tracker

A self-updating stock portfolio dashboard built with Streamlit. A scheduled
pipeline fetches market data every morning, computes indicators, writes a
plain-English digest, and commits a fresh snapshot — so the dashboard is always
up to date without anyone pressing a button.

> **Demo data included.** Clone, install, and run with zero configuration — it
> uses built-in synthetic data out of the box and switches to live market data
> the moment you add a free Finnhub API key.

```bash
pip install -r requirements.txt
streamlit run app.py
```

<!-- Replace with a real screenshot/GIF once deployed -->
<!-- ![dashboard](docs/screenshot.png) -->

---

## What it does

Tracks a portfolio's value, day-over-day P&L, total return, and allocation, with
candlestick charts and technical indicators per holding — and an automated daily
digest that summarizes overnight moves in plain English.

## Automation (the point of the project)

The thing that makes this more than another dashboard is that **fetching is
decoupled from display**. A scheduled [GitHub Actions](.github/workflows/daily-pipeline.yml)
job runs every weekday before the US market open and:

1. fetches quotes for every holding,
2. computes indicators and portfolio metrics,
3. generates the daily digest,
4. writes `data/snapshot.json` + `data/digest.md`,
5. commits the snapshot back to the repo.

The Streamlit app then just renders that snapshot. This is the same separation a
production system uses — a worker does the heavy lifting on a schedule, the UI
stays fast and dumb. Run it yourself anytime with `make pipeline`.

## Architecture

```
                    ┌─────────────────────┐
   cron (8:30 ET)──▶│  pipeline.py        │──▶ data/snapshot.json
                    │  fetch → compute →  │──▶ data/digest.md
                    │  digest → write     │        │
                    └─────────────────────┘        │  commit
                              │                     ▼
                       Finnhub / yfinance     ┌───────────┐
                              │               │  app.py   │  reads snapshot,
                              └──────────────▶│ Streamlit │  renders the UI
                                              └───────────┘
```

| Layer | File | Responsibility |
|-------|------|----------------|
| Config | `src/config.py` | Holdings, settings, env / secrets handling |
| Data | `src/data.py` | Live quotes (Finnhub) + history (yfinance) + demo fallback |
| Indicators | `src/indicators.py` | SMA, EMA, RSI (pure functions) |
| Portfolio | `src/portfolio.py` | Value, P&L, allocation, summary |
| Digest | `src/digest.py` | Template-based daily summary |
| Pipeline | `pipeline.py` | Headless job the scheduler runs |
| UI | `app.py` | Streamlit dashboard |

## Key decisions

- **Finnhub over yfinance for live quotes.** yfinance scrapes an undocumented
  Yahoo endpoint that breaks periodically and is 15–20 min delayed. Finnhub is a
  real API with a free key (60 req/min, no daily cap) and real-time US quotes.
  yfinance is kept only as a *fallback for historical candles*, where freshness
  doesn't matter — so a yfinance outage degrades a chart instead of crashing the app.
- **Graceful demo mode.** No API key? The app generates deterministic synthetic
  data so anyone can run it instantly. This makes the repo trivially reviewable.
- **Aggressive caching** (`st.cache_data`, 60s quotes / 1h candles) keeps usage
  far under the free-tier rate limit even with multiple viewers.
- **Template digest, not an LLM (yet).** v1 builds the summary from a template:
  zero cost, deterministic, testable. The function signature is LLM-ready, so
  swapping in a Claude-API-written summary later is a one-line change. *(future work)*
- **Skipped on purpose:** ML price prediction (looks impressive, misleads users),
  user accounts (scope creep), and supporting every asset class (dilutes focus).

## Run it locally

```bash
make install      # install dependencies
make run          # launch the dashboard
make pipeline     # run the data pipeline once (writes data/snapshot.json)
make test         # run the unit tests
```

To use live data, get a free key at [finnhub.io](https://finnhub.io), then:

```bash
cp .env.example .env      # add your key
# or, for Streamlit Cloud, add FINNHUB_API_KEY to the app's secrets
```

## Tests

`pytest -q` covers the parts that must be correct — portfolio P&L math and the
indicators — with hand-checked numbers rather than live data.

## Future work

- LLM-written digest via the Claude API for more natural summaries
- News + sentiment tab (Finnhub `/company-news` → VADER)
- CSV import of real brokerage positions
- Price-threshold alerts in the digest

---

*For informational purposes only — not investment advice.*
# stock-dashboard
# stock-dashboard
