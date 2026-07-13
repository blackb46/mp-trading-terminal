# Architecture

## System overview

```
                        ┌─────────────────────────────────────────────┐
                        │                 Frontend (React)             │
                        │  Dashboard shell · collapsible panes         │
                        │  Scanners · Recommendations · Detail/Charts  │
                        └───────────────▲─────────────────────────────┘
                                        │ REST + WebSocket
                        ┌───────────────┴─────────────────────────────┐
                        │              Backend (FastAPI)               │
                        │                                              │
                        │  API layer  ── Scanner engine ── Scoring     │
                        │      │              │              engine    │
                        │      │              │                │       │
                        │  ┌───┴──────────────┴────────────────┴────┐  │
                        │  │        Provider adapter layer          │  │
                        │  └───┬───────┬────────┬────────┬─────────┘   │
                        └──────┼───────┼────────┼────────┼─────────────┘
                               │       │        │        │
                          Market    News/     SEC      Schwab
                          data      NLP       EDGAR    (OAuth 2.0)
                        (Polygon/  (Benzinga) (Form4/  quotes,
                         Alpaca)               13F)    positions,
                                                       orders
```

## Backend components

### Provider adapter layer (`app/services/providers/`)
Every external dependency is behind a small interface so providers can be swapped and so the
whole system can run against mock data during development.

| Adapter        | Responsibility                                              | Candidate provider     |
|----------------|-------------------------------------------------------------|------------------------|
| `MarketData`   | Live price/volume (WebSocket), snapshots, OHLCV history     | Polygon.io, Alpaca     |
| `NewsFeed`     | Headlines + NLP catalyst tagging                            | Benzinga, Briefing.com |
| `Sentiment`    | Social/forum sentiment aggregation → bull/neutral/bear %    | (aggregator TBD)       |
| `Institutional`| SEC Form 4 (insider) and 13F filings                        | SEC EDGAR (free)       |
| `Brokerage`    | Quotes, watchlists, positions, orders, historical           | Schwab Trader API      |

### Scanner engine (`app/scanners/`)
Consumes the live market-data stream and evaluates each symbol against scanner criteria,
pushing matches to the frontend over WebSocket.

- **Premarket** — ranks by premarket volume, gap %, VWAP, momentum.
- **5 Pillars** — price $2–20, day gain ≥ 10%, float ≤ 20M, RVOL ≥ 5x, recent news catalyst.
- **Top Gainers** — highest % gain over trailing 1 hour.

### Scoring engine (`app/services/scoring.py`)
Combines category sub-scores into a 0–100 overall score with the configured weights
(Technical 25 / Momentum 20 / Volume 15 / News 10 / Sentiment 10 / Institutional 10 /
Premarket 5 / Risk 5) and derives a Buy/Hold/Avoid rating plus a Low/Moderate/High risk level.

### API layer (`app/api/`)
- REST: `/scanners/*`, `/recommendations`, `/stocks/{symbol}`, `/institutional/*`.
- WebSocket: `/ws/stream` pushes scanner matches and live quote updates (~1s / 1m cadence).

## Frontend components

- **Dashboard shell** — CSS Grid layout; each pane has an `isExpanded` boolean, collapse/expand
  (▼/▲) and fullscreen/restore controls in its header.
- **Panes** — `ScannerPane`, `RecommendationsPane`, `ChartPane`, `InstitutionalPane`, `DetailPane`.
- **Charts** — TradingView Lightweight Charts (candlesticks, 1m/5m); high-velocity tickers get
  neon-green (`#39FF14`) emphasis and a pinned "Top Watch" banner.

## Data flow (scanner → recommendation)

1. Market-data WebSocket streams ticks → scanner engine updates per-symbol rolling metrics.
2. A symbol crossing scanner thresholds is pushed live to the relevant scanner pane.
3. On an interval, candidates are enriched (news, sentiment, institutional, fundamentals)
   and passed to the scoring engine.
4. Top-scored names populate the Recommendation tabs by price band.
5. Selecting a symbol opens the detail view: chart + AI News Analysis + risk breakdown.

## Key technical decisions to confirm

See [docs/ROADMAP.md](docs/ROADMAP.md) and the open questions in the project kickoff notes.
Chief among them: **which market-data provider** (drives cost and the entire real-time layer),
and **whether order entry is in scope at all** vs. read-only analytics.
