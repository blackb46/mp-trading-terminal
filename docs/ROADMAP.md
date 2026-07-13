# Build roadmap

Phased so each stage produces something runnable and de-risks the biggest unknowns early
(data provider + cost) before investing in breadth.

## Phase 0 — Foundation (done: scaffold)
- [x] Repo structure, config via env vars, mock provider, scoring engine skeleton.
- [x] Two scanners (Top Gainers, 5 Pillars) running against mock data.
- [x] Security model documented (OAuth, no secrets in repo).

## Phase 1 — Schwab data integration (the critical path)
- [ ] Schwab OAuth 2.0 flow (app key/secret from Paul; one-time authorization; token refresh).
- [ ] Implement the Schwab adapter: quotes, price history (candles), movers, fundamentals.
- [ ] Universe builder: configurable symbol list filtered to $2–$20 (no full-market screener —
      see docs/SCOPE.md). Optionally seed from Schwab Movers.
- [ ] Wire scanners to Schwab data; Premarket scanner limited to Schwab's extended-hours fields.

## Phase 2 — Frontend dashboard
- [ ] React app shell: CSS Grid layout, collapsible/expandable/fullscreen panes (`isExpanded`).
- [ ] Scanner panes with per-column sort/filter toggles.
- [ ] Candlestick chart pane (TradingView Lightweight Charts), 1m/5m, neon-green high-velocity emphasis.
- [ ] REST + WebSocket client; live updates every ~1 min.

## Phase 2.5 — Hosting & accounts (app is a hosted website — see docs/DEPLOYMENT.md)
- [ ] User accounts / auth (login, sessions, per-user watchlists & preferences).
- [ ] HTTPS + secure WebSocket (WSS); custom domain.
- [ ] Server-side market-data socket that fans out to all browsers (keys stay server-side).
- [ ] Managed Postgres (users, watchlists, audit) + Redis (quote/scan cache).
- [ ] Deploy: static frontend on a CDN, always-on backend service, host secret store.

## Phase 3 — Analysis & scoring (Schwab-only categories)
- [ ] Technical indicators from Schwab price history (9/20/200 EMA alignment, MACD, RSI, VWAP, ATR, ADR).
- [ ] Momentum, volume, premarket, and risk sub-scores.
- [ ] Reweighted 0–100 score (Technical 35 / Momentum 28 / Volume 22 / Premarket 8 / Risk 7).
- [ ] Populate Recommendation tabs (Top 5 by price band) with Buy/Hold/Avoid + risk level.
- ~~News/NLP, sentiment, SEC Form 4 / 13F~~ — CUT (no Schwab source). See docs/SCOPE.md.

## Phase 4 — Brokerage read views
- [ ] Positions and watchlists from Schwab.
- [ ] Order entry LAST, behind `ENABLE_ORDER_ENTRY` + per-order human confirmation. Optional.

## Phase 5 — Hardening
- [ ] Tests for scanners/scoring, Schwab rate-limit handling, token-refresh, caching, deployment.

---

## Open decisions
1. ~~Data provider?~~ **DECIDED: Schwab only, trimmed scope.** See docs/SCOPE.md.
2. **Is live order entry actually wanted**, or is read-only analysis enough for v1?
3. ~~Where does this run?~~ **DECIDED: hosted website.** See docs/DEPLOYMENT.md.
   Follow-up: who can access it (Paul / team / public)?
