# Massive setup — whole-market data (free, End-of-Day)

Massive (formerly Polygon.io — confirmed via redirect: polygon.io now forwards to massive.com)
is a pure data vendor: email/password signup only, no SSN, no KYC, no brokerage relationship.
This is the **third data source**, alongside Finnhub (default, live/curated) and Schwab
(optional, Paul's real-time account).

## What it actually gives you for free — read this first

Massive's marketing pricing page lists "100% Market Coverage" and "Snapshot" on the free
**Stocks Basic** tier, which reads like real-time whole-market data. **It is not.** Checking
the actual per-endpoint docs:

- ❌ **Full Market Snapshot** (`/v2/snapshot/locale/us/markets/stocks/tickers`) — real-time,
  whole market — explicitly **"Not included"** on Stocks Basic. Requires $29/mo Starter+.
- ✅ **Daily Market Summary** (`/v2/aggs/grouped/locale/us/market/stocks/{date}`) — OHLC +
  volume + VWAP for **every U.S. ticker on a given past trading day**, one call — **"Included"**
  on the free Stocks Basic plan. This is what the adapter uses.

**Net result: genuine whole-market coverage, but End-of-Day only.** It refreshes once per
trading day (Massive posts it starting ~4am ET), not intraday. There is no free path to
whole-market *intraday* data anywhere — Massive included.

## Setup

1. You already have a Massive account and a **default API key** from earlier exploration —
   no new signup needed. If you ever need a fresh one: massive.com → Dashboard → Keys →
   Manage keys.
2. Add it to Streamlit Secrets:

```toml
MASSIVE_API_KEY = "PASTE_YOUR_KEY_HERE"
```

3. Save — the app reboots. Select **"Massive (whole market, EOD)"** in the sidebar toggle.

## How the adapter works (`mp_terminal/massive_provider.py`)

1. Calls the Daily Market Summary endpoint for **yesterday**; if no data (weekend/holiday),
   walks backward a few days until it finds one.
2. Does the same for the day before that, to get a previous-close reference.
3. Matches every ticker across both days, filters to the $2–$20 band, and computes real
   day-over-day change % and volume — for the **entire U.S. market**, not a curated list.
4. Caches the result (`st.cache_resource`) so the two-call fetch happens once per app run,
   not on every click — appropriate since the data only changes once a day anyway.

## Known limits

- **Not intraday.** The sidebar shows the exact dates the data is "as of" so this is never
  ambiguous in the UI.
- **RVOL and Float are not available** from this endpoint (it has no rolling-average-volume
  or shares-outstanding fields), so those columns are blank for Massive-sourced quotes —
  same kind of gap as Finnhub's free tier, different cause.
- **Rate limit:** free tier is 5 calls/minute; this adapter uses 2 calls per refresh, so it's
  comfortably within budget even with the backward-search for trading days.
