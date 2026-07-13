# M&P Trading Terminal

An AI-powered stock discovery and short-term trading analysis platform. It continuously
scans U.S.-listed stocks priced **$2.00–$20.00** (prioritizing **$3–$5**) and surfaces the
highest-probability short-term long setups using technical analysis, momentum, volume,
news, sentiment, and institutional activity — presented in a dark, Bloomberg/TradingView-style
dashboard.

> Status: **Scaffold / planning stage.** This repository currently contains the architecture,
> project structure, and skeleton code. External data providers and the scoring engine are
> stubbed and clearly marked `TODO`.

---

## Scope: Schwab-only (trimmed)

**Schwab is the sole data source.** Features Schwab's API can't supply are cut. See
[docs/SCOPE.md](docs/SCOPE.md) for the authoritative feature list.

### What it does
- **Universe scan** — a configurable symbol list filtered to $2–$20 (priority $3–$5). Schwab has
  no whole-market screener, so scanning runs over a curated list / Schwab Movers, not every ticker.
- **Scanners** — Top Gainers, "Pillars" (price $2–20, gain ≥10%, float ≤20M, RVOL ≥5x), and a
  Premarket scanner limited to Schwab's extended-hours fields. Per-column sort/filter toggles.
- **AI Recommendation Engine** — weighted 0–100 score across Technical (35%), Momentum (28%),
  Volume (22%), Premarket (8%), Risk (7%).
- **Recommendation tabs** — Top 5 by price band ($2–3, $3–5, $5–10, $10–20).
- **Stock detail** — interactive candlestick chart (1m / 5m) + risk rating, from Schwab price history.
- **Brokerage** — Schwab quotes, watchlists, positions, historical data, and (optionally) order entry.

### Cut (no Schwab data source)
- ❌ News / catalyst detection / "AI News Analysis"  ❌ Social sentiment score
- ❌ SEC Form 4 (insider) & 13F (institutional) scanners  ❌ True full-market screening

## Architecture at a glance

Single **Streamlit** Python app, hosted on **Streamlit Community Cloud** at
`https://mp-trading-terminal.streamlit.app`.

- **`streamlit_app.py`** — the dashboard UI (Recommendations, Top Gainers, Pillars, Detail).
- **`mp_terminal/`** — pure logic: `models`, `scanners`, `scoring`, `providers`, `schwab` adapter.
- **Data source:** Schwab Trader API only (OAuth 2.0). A `mock` provider runs the whole app
  with no keys so the UI is developable before Schwab approval.

See [ARCHITECTURE.md](ARCHITECTURE.md), [docs/SCOPE.md](docs/SCOPE.md) (what's in/out), and
[docs/ROADMAP.md](docs/ROADMAP.md) (phased plan).

## Project structure

```
streamlit_app.py          # Streamlit UI entrypoint
requirements.txt          # deps (installed by Streamlit Cloud)
.streamlit/
  config.toml             # dark theme
  secrets.toml.example    # template for Schwab keys (real secrets set in Cloud UI)
mp_terminal/
  models.py  scanners.py  scoring.py  providers.py  schwab.py  config.py
docs/                     # SCOPE, ROADMAP, DEPLOYMENT, SECURITY, SCHWAB_API_SETUP
```

## Run locally (optional)

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py       # opens on http://localhost:8501, uses mock data
```

## Deploy

Push to GitHub → deploy on [share.streamlit.io](https://share.streamlit.io) with subdomain
`mp-trading-terminal`. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Security & credentials

**No secrets live in this repo.** Keys are set in Streamlit Cloud's Secrets UI (template:
[.streamlit/secrets.toml.example](.streamlit/secrets.toml.example)). The Schwab API uses
**OAuth 2.0**, not a username/password. See [docs/SECURITY.md](docs/SECURITY.md).

## Important disclaimer

This is an analytical/research tool, not investment advice. Automated order placement is
**off by default** and gated behind explicit configuration and human confirmation. Trading
low-priced, low-float stocks carries substantial risk of loss.
