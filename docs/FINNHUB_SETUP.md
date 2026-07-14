# Finnhub setup — the default data source

Finnhub is the **default** data source. This account is **yours (Kevin's)**, a pure data-vendor
signup — email/password only, no SSN, no KYC, no brokerage relationship, nothing tied to Paul.
This replaced Alpaca (see ALPACA_SETUP.md) after Alpaca began requiring identity verification
even for its free paper/market-data tier.

---

## Step 1 — Sign up

1. Go to **https://finnhub.io** → **Sign Up** (email + password, or Google login).
2. No funding, no personal/financial info, no verification steps.

## Step 2 — Get your API key

Your **API Key** is shown immediately on the dashboard after signup — no waiting.

## Step 3 — Add it to Streamlit Secrets

1. Go to your app on **share.streamlit.io** → **Manage app** → **⋮ → Settings → Secrets**.
2. Add/update:

```toml
DATA_SOURCE = "finnhub"
FINNHUB_API_KEY = "PASTE_KEY_HERE"
```

3. **Save.** The app reboots automatically.

## What the app does with it

- **Finnhub is the default** shown to every visitor — real-time trade data, no login required.
- A **sidebar toggle** lets the user switch to **Schwab** instead, if they want Paul's
  real-time account data — Paul authorizes it himself via the existing "Connect to Schwab"
  button; his credentials never pass through this app's code or its operator.
- If `FINNHUB_API_KEY` is missing, the app falls back to mock demo data with a warning, so the
  UI never breaks.

## Known limits (free tier)

- **60 API calls/minute.** The adapter uses ~2 calls per symbol per refresh (quote + today's
  volume), plus one memoized call per symbol for slow-changing fundamentals (avg volume,
  shares outstanding) that isn't repeated every refresh. For the default ~20-symbol universe
  that's comfortably under the limit at a 60-second refresh cadence.
- **Not a single-call whole-market snapshot** — unlike Massive/Polygon's paid tier, Finnhub's
  free tier is queried per-symbol, so scanning stays limited to the configured universe list
  (`FINNHUB_UNIVERSE` secret, comma-separated) rather than literally every U.S. ticker.
- Real-time trade data, not the full consolidated SIP tape — good enough for prototyping and
  a working live scanner, not identical to Schwab's institutional-grade feed.
