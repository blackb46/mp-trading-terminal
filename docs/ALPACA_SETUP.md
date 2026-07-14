# Alpaca setup — SUPERSEDED

> **This path was abandoned.** Alpaca began requiring identity verification (name, DOB,
> address, SSN/Tax ID) even to activate the free paper/market-data tier — not just to fund a
> live account. That's incompatible with the "no personal identity exposure" requirement for
> this project. **Finnhub is now the default data source instead — see FINNHUB_SETUP.md.**
> This file is kept only as a record of what was tried and why it didn't work.

---

Alpaca is the **default data source**. This account is **yours (Kevin's)**, not Paul's — it's
a free developer signup, no funding required, and has nothing to do with his Schwab account.

---

## Step 1 — Create a free Alpaca account

1. Go to **https://alpaca.markets** → click **Sign Up**.
2. Sign up with your own email (`blackb46@purdue.edu` or whichever you prefer).
3. Choose the **individual / self-directed** option if asked what kind of account.
4. **Skip/decline funding.** You do not need to link a bank account or deposit money — market
   data API keys work on an unfunded account. If it pushes a "fund your account" flow, look
   for "skip for now" / "I'll do this later."
5. Verify your email if prompted.

## Step 2 — Generate API keys

1. Once logged in, you land on the **Alpaca Dashboard**.
2. Make sure you're in **Paper Trading** mode (top-left toggle) — paper/unfunded mode is
   exactly what we want; it still gives full free market-data access.
3. Find **"API Keys"** in the left sidebar (or under account settings).
4. Click **Generate New Key** (or "View" if one already exists).
5. Copy both values immediately — **the secret is only shown once**:
   - **API Key ID**
   - **API Secret Key**

> Store these somewhere private (password manager) as a backup. Paste them into Streamlit
> Secrets (next step) — never into a chat message, code file, or the GitHub repo.

## Step 3 — Add the keys to Streamlit Secrets

1. Go to your app on **share.streamlit.io** → **Manage app** → **⋮ → Settings → Secrets**.
2. Add these two new lines (keep everything else already there):

```toml
ALPACA_API_KEY = "PASTE_API_KEY_ID_HERE"
ALPACA_API_SECRET = "PASTE_API_SECRET_KEY_HERE"
```

3. **Save.** The app reboots automatically.

## Step 4 — I wire up the code

Once you confirm the keys are saved, I'll:
- Build an `AlpacaMarketData` adapter (IEX real-time feed, free tier).
- Add a **data-source toggle** in the UI sidebar: **Alpaca (default)** vs **Schwab (optional)**.
- Wire the existing Schwab "Connect to Schwab" button behind that toggle, so if Paul ever
  wants Schwab's data, *he* clicks it and logs in himself — his credentials never pass through
  you, me, or this codebase.
- Push the update; Streamlit auto-redeploys.

## What "done" looks like

- App loads with **Alpaca IEX data by default** — no login needed, works immediately.
- A toggle/dropdown lets Paul switch to **Schwab** if he wants his account's data — he
  authenticates himself via the existing OAuth "Connect to Schwab" button.
- Nothing in this flow touches Paul's brokerage login unless *he* chooses to use it.

---

## Quick reference

| Value | Where it goes |
|---|---|
| API Key ID | Streamlit Secrets → `ALPACA_API_KEY` |
| API Secret Key | Streamlit Secrets → `ALPACA_API_SECRET` |
| Account type | Paper/unfunded — do not fund it |
| Whose account | **Yours** (Kevin), unrelated to Paul |
