# Scope — Schwab-only (trimmed)

**Decision: Schwab is the sole data source.** Features that Schwab's API cannot provide are
cut. This document is the authoritative feature list; it overrides anything broader in the
original UI spec.

## In scope (Schwab supports it)

- **Quotes** — real-time/delayed per Paul's account entitlements (bid/ask, last, volume, OHLC).
- **Price history / candlesticks** — 1m and 5m charts in the detail view.
- **Watchlist-based scanning** — see the universe note below.
- **Scanners:** Top Gainers, "Pillars" (adapted — see below), Premarket (limited — see below).
- **Technical & momentum analysis** — EMAs (9/20/200), MACD, RSI, VWAP, ATR/ADR, computed by
  us from Schwab price history.
- **Volume metrics** — RVOL, average daily volume, relative volume.
- **Fundamentals (basic)** — float / shares outstanding where Schwab's instruments endpoint
  provides it.
- **AI Recommendation score** — 0–100 from the categories Schwab can feed (reweighted below).
- **Recommendation tabs** — Top 5 per price band ($2–3, $3–5, $5–10, $10–20).
- **Brokerage read views** — positions, watchlists (order entry: separate decision).

## Cut (Schwab's API does not provide it)

- ❌ News feed / catalyst detection / "AI News Analysis"
- ❌ Social sentiment (Reddit, X, StockTwits, forums) and the sentiment score
- ❌ SEC Form 4 (insider) and 13F (institutional) scanners
- ❌ True full-market screening of *every* US stock (Schwab has no whole-market screener)

> These can be re-added later by plugging a second data source into the adapter layer, but
> they are out of scope for the Schwab-only build.

## Universe: important constraint

Schwab has **no endpoint that scans all US equities**. So the app scans a **configurable
symbol universe** rather than literally the entire market:

- A curated/imported symbol list (CSV of tickers in the $2–20 band, refreshable), and/or
- Schwab **Movers** for supported indexes as a discovery feed.

The $2–20 price band and $3–5 priority still apply — as a filter over that configured universe.

## Reweighted AI score (was 8 categories, now 5)

Removing News (10), Sentiment (10), and Institutional (10) frees 30 points, redistributed
proportionally across the remaining categories:

| Category   | Old | New |
|------------|-----|-----|
| Technical  | 25% | **35%** |
| Momentum   | 20% | **28%** |
| Volume     | 15% | **22%** |
| Premarket  | 5%  | **8%**  |
| Risk       | 5%  | **7%**  |
| ~~News~~        | 10% | — |
| ~~Sentiment~~   | 10% | — |
| ~~Institutional~~| 10% | — |
| **Total**  |100% | **100%** |

## Adapted scanners

- **"Pillars" scanner** — the original 5th pillar was "recent news catalyst," which Schwab
  can't supply. It becomes a **4-pillar** scanner: price $2–20, day gain ≥ 10%, float ≤ 20M,
  RVOL ≥ 5x.
- **Premarket scanner** — depends on Schwab providing extended-hours quotes; premarket VWAP/
  volume/gap coverage is limited. Build against what Schwab returns; flag fields it can't fill.
