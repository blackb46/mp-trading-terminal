"""M&P Trading Terminal — Streamlit app entrypoint.

Runs on Streamlit Community Cloud at https://mp-trading-terminal.streamlit.app.

Data source is controlled by the DATA_SOURCE secret:
  - "mock"   : built-in demo data (no keys needed) — good for UI work.
  - "schwab" : live Schwab Trader API. Requires a one-time OAuth login (button in the sidebar).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from mp_terminal import scanners, scoring
from mp_terminal.config import load_settings
from mp_terminal.models import CategoryScores, ScoredStock
from mp_terminal.providers import MockMarketData

st.set_page_config(page_title="M&P Trading Terminal", page_icon="📈", layout="wide")

try:
    settings = load_settings(st.secrets)
except Exception:
    settings = load_settings()

PRICE_BANDS = [("$2–3", 2, 3), ("$3–5", 3, 5), ("$5–10", 5, 10), ("$10–20", 10, 20)]


# --- token store: survives reruns/sessions until the app reboots (Community Cloud is ephemeral,
#     so a reboot means Paul re-authorizes; Schwab also forces re-auth every ~7 days anyway). ---
@st.cache_resource
def token_store() -> dict:
    return {}


def build_schwab_provider():
    """Return a live Schwab provider, or None if not yet authorized (shows Connect UI)."""
    from mp_terminal.schwab import (
        SchwabError,
        SchwabMarketData,
        build_authorize_url,
        exchange_code_for_token,
    )

    key, secret = settings.schwab_app_key, settings.schwab_app_secret
    redirect = settings.schwab_redirect_uri
    if not key or not secret:
        st.error("DATA_SOURCE is 'schwab' but SCHWAB_APP_KEY / SCHWAB_APP_SECRET are missing "
                 "from Streamlit Secrets.")
        st.stop()

    store = token_store()

    # Handle the OAuth redirect: Schwab sends us back with ?code=...
    code = st.query_params.get("code")
    if code and "token" not in store:
        try:
            store["token"] = exchange_code_for_token(key, secret, redirect, code)
            st.query_params.clear()  # code is single-use; drop it from the URL
        except SchwabError as e:
            st.error(f"Schwab authorization failed: {e}")
            st.query_params.clear()

    if "token" not in store:
        with st.sidebar:
            st.link_button("🔗 Connect to Schwab", build_authorize_url(key, redirect),
                           use_container_width=True)
            st.caption("Paul logs in once on Schwab to authorize live data.")
        return None

    universe = None
    raw_uni = st.secrets.get("SCHWAB_UNIVERSE") if hasattr(st, "secrets") else None
    if raw_uni:
        universe = [s.strip().upper() for s in str(raw_uni).split(",") if s.strip()]

    return SchwabMarketData(
        key, secret, store["token"], universe=universe,
        on_token_update=lambda t: store.__setitem__("token", t),
    )


# --- resolve the data provider ---
if settings.data_source == "schwab":
    provider = build_schwab_provider()
    live = provider is not None
else:
    provider = MockMarketData()
    live = False


def load_quotes():
    if provider is None:
        return []
    try:
        return provider.all_quotes()
    except Exception as e:
        st.error(f"Failed to load quotes from Schwab: {e}")
        return []


def demo_scores(seed: float) -> CategoryScores:
    """Placeholder sub-scores until the Schwab-fed analysis layer lands (Phase 3)."""
    return CategoryScores(
        technical=min(100, seed * 6), momentum=min(100, seed * 5.5),
        volume=min(100, seed * 7), premarket=min(100, seed * 4),
        risk=max(0, 100 - seed * 4),
    )


# ------------------------------- Header / sidebar -------------------------------
st.title("📈 M&P Trading Terminal")
st.caption("AI-powered short-term stock discovery · Schwab-only scope · $2–$20 universe")

with st.sidebar:
    st.header("Status")
    if settings.data_source == "schwab" and live:
        st.success("Data source: Schwab (LIVE)")
    elif settings.data_source == "schwab":
        st.info("Data source: Schwab — awaiting authorization")
    else:
        st.warning("Data source: MOCK (demo data)")
        st.caption("Set the `data_source` secret to `schwab` to go live.")
    st.metric("Order entry", "ON" if settings.enable_order_entry else "OFF (read-only)")
    st.divider()
    st.caption("Callback URL registered with Schwab:")
    st.code(settings.schwab_redirect_uri, language=None)

quotes = load_quotes()

if settings.data_source == "schwab" and not live:
    st.info("👈 Click **Connect to Schwab** in the sidebar to authorize live data.")
    st.stop()

if not quotes:
    st.warning("No quotes returned. Check the universe list or Schwab connection.")
    st.stop()

# ------------------------------- Tabs -------------------------------
tab_reco, tab_gainers, tab_pillars, tab_detail = st.tabs(
    ["⭐ Recommendations", "🚀 Top Gainers", "🏛 Pillars Scanner", "🔍 Stock Detail"]
)

with tab_reco:
    st.subheader("Recommendations by price band")
    scored: list[ScoredStock] = []
    for q in quotes:
        s = ScoredStock(quote=q, scores=demo_scores(abs(q.daily_change_pct or 0)))
        scoring.finalize(s)
        scored.append(s)
    cols = st.columns(len(PRICE_BANDS))
    for col, (label, lo, hi) in zip(cols, PRICE_BANDS):
        with col:
            st.markdown(f"**{label}**")
            band = sorted([s for s in scored if lo <= s.quote.price < hi],
                          key=lambda s: s.overall_score, reverse=True)[:5]
            if not band:
                st.caption("—")
            for s in band:
                st.metric(s.quote.symbol, f"{s.overall_score:.0f}/100",
                          f"{s.recommendation.value} · {s.risk_level.value} risk")

with tab_gainers:
    st.subheader("Top Gainers")
    ranked = scanners.top_gainers(quotes)
    st.dataframe(pd.DataFrame([{
        "Symbol": q.symbol, "Price": round(q.price, 2),
        "Change %": round(q.daily_change_pct or 0, 2), "Volume": q.volume,
        "RVOL": round(q.rvol, 2) if q.rvol else None, "Float": q.float_shares,
    } for q in ranked]), use_container_width=True, hide_index=True)

with tab_pillars:
    st.subheader("Pillars Scanner")
    st.caption("Price $2–20 · Day gain ≥10% · Float ≤20M · RVOL ≥5x  "
               "(news-catalyst pillar removed in Schwab-only scope)")
    rows = []
    for q in quotes:
        p = scanners.pillars_match(q)
        rows.append({
            "Symbol": q.symbol, "Price": round(q.price, 2),
            "$2–20": "✅" if p["price_band"] else "—",
            "Gain ≥10%": "✅" if p["gain_10pct"] else "—",
            "Float ≤20M": "✅" if p["low_float"] else "—",
            "RVOL ≥5x": "✅" if p["rvol_5x"] else "—",
            "All Pillars": "🟢" if scanners.is_all_pillars(q) else "",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with tab_detail:
    st.subheader("Stock Detail")
    symbol = st.selectbox("Symbol", [q.symbol for q in quotes])
    q = next(x for x in quotes if x.symbol == symbol)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Price", f"${q.price:.2f}")
    c2.metric("Change", f"{q.daily_change_pct or 0:.2f}%")
    c3.metric("RVOL", f"{q.rvol:.2f}" if q.rvol else "—")
    c4.metric("Float", f"{q.float_shares:,}" if q.float_shares else "—")

    # Placeholder OHLC candles. TODO: replace with Schwab /pricehistory (1m/5m) in Phase 3.
    base = q.price
    candles = [(base * (1 + 0.01 * (i % 3 - 1)), base * (1 + 0.02),
                base * (1 - 0.015), base * (1 + 0.005 * (i % 4 - 1))) for i in range(20)]
    fig = go.Figure(data=[go.Candlestick(
        x=list(range(len(candles))),
        open=[o for o, h, l, c in candles], high=[h for o, h, l, c in candles],
        low=[l for o, h, l, c in candles], close=[c for o, h, l, c in candles],
    )])
    fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0),
                      xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Demo candles — replaced by Schwab /pricehistory (1m/5m) once the analysis layer lands.")
