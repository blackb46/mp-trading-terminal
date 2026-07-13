"""M&P Trading Terminal — Streamlit app entrypoint.

Runs on Streamlit Community Cloud at https://mp-trading-terminal.streamlit.app.
Currently powered by the mock data source so the dashboard is fully navigable before the
Schwab app is approved. Flip the `data_source` secret to "schwab" once keys are in place.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from mp_terminal import scanners, scoring
from mp_terminal.config import load_settings
from mp_terminal.models import CategoryScores, ScoredStock
from mp_terminal.providers import MockMarketData, get_provider

st.set_page_config(page_title="M&P Trading Terminal", page_icon="📈", layout="wide")

# --- Settings (st.secrets on Cloud, env fallback locally) ---
try:
    settings = load_settings(st.secrets)
except Exception:
    settings = load_settings()

provider = get_provider(settings.data_source)

PRICE_BANDS = [("$2–3", 2, 3), ("$3–5", 3, 5), ("$5–10", 5, 10), ("$10–20", 10, 20)]


def load_quotes():
    if isinstance(provider, MockMarketData):
        return provider.all_quotes()
    return [provider.snapshot(s) for s in provider.universe()]


def demo_scores(seed: float) -> CategoryScores:
    """Placeholder sub-scores until the Schwab-fed analysis layer lands (Phase 3)."""
    return CategoryScores(
        technical=min(100, seed * 6),
        momentum=min(100, seed * 5.5),
        volume=min(100, seed * 7),
        premarket=min(100, seed * 4),
        risk=max(0, 100 - seed * 4),
    )


# ------------------------------- Header / sidebar -------------------------------
st.title("📈 M&P Trading Terminal")
st.caption("AI-powered short-term stock discovery · Schwab-only scope · $2–$20 universe")

with st.sidebar:
    st.header("Status")
    if settings.data_source == "schwab":
        st.success("Data source: Schwab (live)")
    else:
        st.warning("Data source: MOCK (demo data)")
        st.caption("Flip the `data_source` secret to `schwab` once the app is approved.")
    st.metric("Order entry", "ON" if settings.enable_order_entry else "OFF (read-only)")
    st.divider()
    st.caption("Callback URL registered with Schwab:")
    st.code(settings.schwab_redirect_uri, language=None)

quotes = load_quotes()

# ------------------------------- Tabs -------------------------------
tab_reco, tab_gainers, tab_pillars, tab_detail = st.tabs(
    ["⭐ Recommendations", "🚀 Top Gainers", "🏛 Pillars Scanner", "🔍 Stock Detail"]
)

# --- Recommendations: Top 5 per price band ---
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
            band = sorted(
                [s for s in scored if lo <= s.quote.price < hi],
                key=lambda s: s.overall_score, reverse=True,
            )[:5]
            if not band:
                st.caption("—")
            for s in band:
                st.metric(
                    s.quote.symbol,
                    f"{s.overall_score:.0f}/100",
                    f"{s.recommendation.value} · {s.risk_level.value} risk",
                )

# --- Top Gainers ---
with tab_gainers:
    st.subheader("Top Gainers")
    ranked = scanners.top_gainers(quotes)
    df = pd.DataFrame([{
        "Symbol": q.symbol,
        "Price": round(q.price, 2),
        "Change %": round(q.daily_change_pct or 0, 2),
        "Volume": q.volume,
        "RVOL": round(q.rvol, 2) if q.rvol else None,
        "Float": q.float_shares,
    } for q in ranked])
    st.dataframe(df, use_container_width=True, hide_index=True)

# --- Pillars Scanner ---
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

# --- Stock Detail with candlestick ---
with tab_detail:
    st.subheader("Stock Detail")
    symbol = st.selectbox("Symbol", [q.symbol for q in quotes])
    q = next(x for x in quotes if x.symbol == symbol)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Price", f"${q.price:.2f}")
    c2.metric("Change", f"{q.daily_change_pct or 0:.2f}%")
    c3.metric("RVOL", f"{q.rvol:.2f}" if q.rvol else "—")
    c4.metric("Float", f"{q.float_shares:,}" if q.float_shares else "—")

    # Placeholder OHLC candles (Schwab /pricehistory will supply real 1m/5m candles).
    base = q.price
    candles = [(base * (1 + 0.01 * (i % 3 - 1)), base * (1 + 0.02),
                base * (1 - 0.015), base * (1 + 0.005 * (i % 4 - 1))) for i in range(20)]
    fig = go.Figure(data=[go.Candlestick(
        x=list(range(len(candles))),
        open=[o for o, h, l, c in candles],
        high=[h for o, h, l, c in candles],
        low=[l for o, h, l, c in candles],
        close=[c for o, h, l, c in candles],
    )])
    fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0),
                      xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Demo candles — replaced by Schwab /pricehistory (1m/5m) once live.")
