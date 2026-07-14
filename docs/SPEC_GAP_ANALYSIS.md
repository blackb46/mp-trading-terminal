# Spec gap analysis — Paul's UI.docx vs. what's built

A feature-by-feature comparison of Paul's original specification against the current app.
Status key: ✅ Done · 🟡 Partial · ❌ Not built · ⛔ Cut (data source can't supply it).

The headline: the app today is a **working data + UI shell** — it pulls real market data, filters
by price band, and presents scanners + recommendation cards cleanly. What's largely missing is
(1) the **real technical-analysis / scoring engine** (always planned as a later phase) and
(2) features that depend on **data no free source provides** (news, sentiment, institutional,
intraday whole-market).

---

## 1. Universe & core recommendation

| Spec item | Status | Notes |
|---|---|---|
| Scan U.S. stocks $2–$20, prioritize $3–$5 | ✅ | Whole market via Massive; range now user-adjustable in the sidebar |
| Default mode = short-term LONG | 🟡 | It's long-only in effect, but there's no explicit mode selector |
| Switch to Long Swing / Short Selling modes | ❌ | Not built |
| Weighted 0–100 AI score | 🟡 | **Placeholder** formula based on % change; real weighted model not built |
| AI Confidence / Overall Score / Buy·Hold·Avoid | 🟡 | Score + Buy/Hold/Avoid shown; "AI Confidence" not a distinct populated value |

## 2. Required stock filters (the analysis engine)

| Spec item | Status | Notes |
|---|---|---|
| Liquidity: Avg Daily Volume, RVOL, Float, Shares Outstanding | 🟡 | Source-dependent; Massive (default) has volume but **no float or avg-volume → no RVOL** |
| Volatility: ADR, ATR, Daily Low→High Swing, Gap %, Premarket Vol | ❌ | None computed yet |
| Spread: tight bid/ask filter | ❌ | Bid/ask only available from Schwab; not evaluated |
| Trend: 9/20/200 EMA + bull/bear/neutral alignment | ❌ | Not built — **needs historical price bars** |
| Momentum: MACD, RSI, VWAP, Volume Trend, Price Momentum | ❌ | Not built — needs historical bars |
| Technical levels: Support/Resistance/Breakout/Prev H-L/Gaps | ❌ | Not built |
| Relative strength vs SPY / Sector / Industry | ❌ | Not built |
| Catalysts (Earnings, FDA, upgrades, insider, filings, mergers…) | ⛔ | No free news/catalyst feed |
| Sentiment (Reddit, StockTwits, Yahoo, X) → bull/neutral/bear % | ⛔ | No free/ToS-compliant sentiment source |
| News analysis + "AI News Analysis" | ⛔ | No news feed |

> **This section is the single biggest gap.** Nearly the entire scoring model (EMAs, MACD, RSI,
> VWAP, ATR/ADR, support/resistance) is unbuilt. It's very buildable — it needs per-symbol
> **historical price bars**, which Massive (`/v2/aggs`), Finnhub, and Schwab all provide — but
> it's a substantial piece of work and is what would make the "AI" real instead of placeholder.

## 3. Scanners

| Spec item | Status | Notes |
|---|---|---|
| Premarket Scanner | ❌ | Not built (needs a premarket/extended-hours feed) |
| "5 Pillars" Scanner | 🟡 | 4 of 5 pillars built (price, gain ≥10%, float ≤20M, RVOL ≥5x); **news-catalyst pillar** ⛔ |
| Top Gainers Scanner | 🟡 | Built, but ranks by **daily** % change — spec wants **past 1 hour** (needs intraday bars) |
| Show columns: Today's Low, Avg Daily High/Low, Avg 5-Day Low, Daily Swing | ❌ | Not shown — these averages aren't sourced yet |
| Per-column low↔high filter buttons | 🟡 | Streamlit tables sort on header-click, but not the explicit toggle buttons described |
| Symbol as a link → popup candlestick, updated every minute | 🟡 | Stock Detail tab shows a chart, but it's placeholder candles, not a click-popup or per-minute live |

## 4. Brokerage integration (Schwab)

| Spec item | Status | Notes |
|---|---|---|
| Quotes | ✅ | Schwab adapter (optional toggle) |
| Historical price data | 🟡 | Endpoint known/coded, not yet wired into charts |
| Watchlists | ❌ | Not built (needs the Accounts & Trading API product added) |
| Positions | ❌ | Not built (same) |
| Orders / order entry | ⛔ | Intentionally off — read-only by design decision |
| Schwab scanner auto-refresh every 1 min | ❌ | No auto-refresh loop yet |

## 5. Institutional activity

| Spec item | Status | Notes |
|---|---|---|
| SEC Form 4 (insider) scanner | ⛔ | No source in current stack (Massive has it on **paid** tiers) |
| 13F institutional scanner | ⛔ | Same |

## 6. Recommendation tab fields

Spec lists 15 fields per recommendation. Current cards show 5.

| Field | Status | | Field | Status |
|---|---|---|---|---|
| Symbol | ✅ | | Avg Daily High | ❌ |
| Company Name | ✅ | | Avg Daily Low | ❌ |
| Current Price | ✅ | | Avg 5-Day Low | ❌ |
| Daily % Change | ✅ | | Volume | ❌ (not on card) |
| Recommendation | ✅ | | Daily Swing | ❌ |
| Risk Level | 🟡 (placeholder) | | AI Confidence | 🟡 |
| Bid-Ask price | ❌ | | Today's Low | ❌ |

## 7. Risk rating

| Spec item | Status | Notes |
|---|---|---|
| Low/Moderate/High rating | 🟡 | Shown, but derived from the placeholder score, not real inputs |
| Based on Volatility, Spread, Float, News Risk, Earnings Risk | ❌ | None of these real inputs are wired in |

## 8. Stock detail screen

| Spec item | Status | Notes |
|---|---|---|
| Candlestick chart | 🟡 | Placeholder candles (light-themed) |
| Interactive TradingView-style, 1-min / 5-min timeframes | ❌ | No timeframe toggle, not live/interactive yet |

## 9. Core UI architecture

| Spec item | Status | Notes |
|---|---|---|
| Grid dashboard, panes expand/collapse, fullscreen/minimize icons | ❌ | We use clean **tabs** instead — Streamlit doesn't natively do draggable/collapsible grid panes |
| Clean, modern, desktop + mobile | 🟡 | Polished light UI done; Streamlit is responsive but not hand-tuned for mobile |
| Bloomberg/TradingView **dark** theme + neon-green high-velocity highlighting | 🟡→changed | Deliberately switched to a **clean light theme** per your request; neon-green "Top Watch" highlighting not built |

## 10. Real-time scanner engine

| Spec item | Status | Notes |
|---|---|---|
| WebSocket live price/volume feed | ❌ | Current stack is REST polling; Massive default is **End-of-Day** |
| Low-float threshold | 🟡 | Spec is inconsistent: "5 Pillars" says ≤20M, scanner-logic section says <10M. Using ≤20M |
| "High-Velocity Alerts" / "Top Watch" banner | ❌ | Not built |

---

## Recommended priority order

Grouped by value vs. effort, and by what's actually achievable with the current (free) data:

**A. Achievable now, high value — build the real analysis engine (turns the "AI" real):**
1. Pull per-symbol **historical bars** (Massive `/v2/aggs`) and compute **EMA 9/20/200, MACD,
   RSI, VWAP, ATR, ADR** → real Technical + Momentum sub-scores.
2. Real **RVOL / average volume / daily swing / gap %** from those bars (fixes the blank columns).
3. Wire these into the weighted score so recommendations reflect real signals, not % change.
4. Add the missing recommendation-card fields (Volume, Daily Swing, Today's Low, bid/ask where available).

**B. Achievable, medium value:**
5. Real interactive candlestick chart with 1-min/5-min toggle (from historical bars).
6. Premarket scanner (where the data source exposes extended-hours bars).
7. Mode selector (Long / Swing / Short) affecting ranking direction.

**C. Needs a paid source or a decision:**
8. News/catalyst detection, sentiment, SEC Form 4/13F → require paid data (e.g. Massive paid
   add-ons or a news API). Restore only if the budget/decision supports it.
9. True real-time whole-market (WebSocket) → Massive/Polygon paid tier.
10. Schwab watchlists/positions → add the "Accounts and Trading" product to Paul's app.

**D. Larger UI rebuild (only if truly wanted):**
11. Draggable/collapsible grid panes + dark "terminal" theme with neon-green alerts → this is a
    genuine React rebuild; Streamlit isn't the right tool for that specific look. Worth an
    explicit conversation before investing, since it conflicts with the clean-light direction
    you just asked for.
