# Setup runbook — do these in order

Three platforms, in this exact order: **GitHub → Streamlit → Schwab**. GitHub/Streamlit come
first so the `mp-trading-terminal` subdomain is claimed before you register it with Schwab.

---

## STEP 1 — GitHub: create the repo

At https://github.com → **New repository**:

| Field | Value |
|---|---|
| Repository name | `mp-trading-terminal` |
| Description | `M&P Trading Terminal — Schwab-powered stock discovery dashboard (Streamlit)` |
| Visibility | **Private** |
| Initialize with README / .gitignore / license | **Leave all UNCHECKED** (the project already has them) |

Click **Create repository**. Copy the repo URL shown (e.g. `https://github.com/<you>/mp-trading-terminal.git`).

## STEP 2 — Push the project code

From the project folder (`projects/MP_Trading_Terminal`). Kevin can run these — or ask me to:

```bash
git init -b main
git add .
git commit -m "Initial commit: M&P Trading Terminal (Streamlit, Schwab-only scope)"
git remote add origin https://github.com/<you>/mp-trading-terminal.git
git push -u origin main
```

Confirm the files show up on GitHub.

## STEP 3 — Streamlit Community Cloud: deploy + claim the subdomain

At https://share.streamlit.io → sign in **with GitHub** → **Create app** → **Deploy a public app from GitHub**:

| Field | Value |
|---|---|
| Repository | `<you>/mp-trading-terminal` |
| Branch | `main` |
| Main file path | `streamlit_app.py` |
| App URL (subdomain) | `mp-trading-terminal`  → gives `https://mp-trading-terminal.streamlit.app` |

Before clicking Deploy, open **Advanced settings → Secrets** and paste:

```toml
DATA_SOURCE = "mock"
SCHWAB_APP_KEY = ""
SCHWAB_APP_SECRET = ""
SCHWAB_REDIRECT_URI = "https://mp-trading-terminal.streamlit.app"
ENABLE_ORDER_ENTRY = "false"
SCAN_REFRESH_SECONDS = "60"
```

Click **Deploy**. In ~2 min the dashboard loads on mock data. **The subdomain is now yours.**

## STEP 4 — Schwab: Create App (Paul does this on his developer.schwab.com login)

Dashboard → **Create App**:

| Field | Value |
|---|---|
| Environment | `Production` |
| API Product | **Trader API - Individual** (covers Market Data + Accounts and Trading) |
| Order Limit | `120` |
| App Name | `M&P Trading Terminal` |
| App Description | `Internal stock discovery and analysis dashboard using Schwab market data and account information for short-term trading research.` |
| **Callback URL** | `https://mp-trading-terminal.streamlit.app` |

> Callback URL: **no path, no trailing slash** — exactly `https://mp-trading-terminal.streamlit.app`.

Click **Create**. The app goes to **Apps Pending Approval**. Approval usually takes a few days.

## STEP 5 — After Schwab approval: go live

1. Paul opens the approved app → copies the **App Key** and **App Secret**.
2. He sends them to Kevin **privately** (password-manager share / secure note — **not** email/chat).
   **Never send the Schwab account password — it is not used.**
3. In Streamlit Cloud → your app → **Settings → Secrets**, update:
   ```toml
   DATA_SOURCE = "schwab"
   SCHWAB_APP_KEY = "<paste app key>"
   SCHWAB_APP_SECRET = "<paste app secret>"
   SCHWAB_REDIRECT_URI = "https://mp-trading-terminal.streamlit.app"
   ENABLE_ORDER_ENTRY = "false"
   SCAN_REFRESH_SECONDS = "60"
   ```
4. Paul does the one-time Schwab OAuth login through the app to authorize it.
5. The dashboard switches from mock to live Schwab data.

---

## Who does what

- **Kevin:** Steps 1–3 (GitHub + Streamlit), Step 5.3 (secrets).
- **Paul:** Step 4 (Create App), Step 5.1–2 (send keys), Step 5.4 (one-time login).

## Values quick-reference

- GitHub repo: `mp-trading-terminal` (private)
- Streamlit subdomain: `mp-trading-terminal` → `https://mp-trading-terminal.streamlit.app`
- Streamlit main file: `streamlit_app.py`
- Schwab callback: `https://mp-trading-terminal.streamlit.app`
- Schwab app name: `M&P Trading Terminal` · Order Limit `120` · Product `Trader API - Individual`
