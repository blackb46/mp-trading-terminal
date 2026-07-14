"""M&P Trading Terminal — Streamlit app entrypoint.

Runs on Streamlit Community Cloud at https://mp-trading-terminal.streamlit.app.

Data source is a user-facing toggle in the sidebar:
  - Massive (default): free, every U.S. ticker in the price band, but End-of-Day only —
                       refreshes once per trading day, not intraday. No personal account.
  - Finnhub:           free, live/intraday, but a curated ~20-symbol list (no whole-market
                       call on the free tier). No personal account, no login.
  - Schwab (optional): Paul's own account, real-time. Paul clicks "Connect to Schwab" and
                       logs in himself — his credentials never pass through this app's code.
The price range is also user-adjustable in the sidebar. Falls back to mock data if no source
is configured, so the UI always renders.
"""
from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from mp_terminal import indicators, scanners, scoring
from mp_terminal.config import load_settings
from mp_terminal.models import ScoredStock
from mp_terminal.providers import MockMarketData

st.set_page_config(page_title="M&P Trading Terminal", page_icon="📈", layout="wide")

try:
    settings = load_settings(st.secrets)
except Exception:
    settings = load_settings()


# ------------------------------- styling -------------------------------
st.markdown("""
<style>
.block-container { padding-top: 3.4rem; padding-bottom: 3rem; max-width: 1320px; }
h1, h2, h3 { font-weight: 600; color: #0F172A; }

/* App header */
.mp-header { display:flex; align-items:center; gap:14px; margin-bottom:18px; }
.mp-logo { background:#0E9F6E; color:#fff; font-weight:700; font-size:15px; width:46px;
           height:46px; border-radius:11px; display:flex; align-items:center;
           justify-content:center; letter-spacing:.5px; box-shadow:0 2px 6px rgba(14,159,110,.25); }
.mp-title { font-size:23px; font-weight:700; color:#0F172A; line-height:1.1; }
.mp-subtitle { font-size:13px; color:#64748B; margin-top:3px; }

/* Section + band headers */
.mp-band-head { font-size:13px; font-weight:600; color:#475569; margin:0 0 10px;
                padding-bottom:7px; border-bottom:2px solid #E2E8F0; }

/* Recommendation cards */
.mp-card { background:#fff; border:1px solid #E7ECF2; border-radius:12px; padding:12px 14px;
           margin-bottom:11px; box-shadow:0 1px 2px rgba(15,23,42,.05); }
.mp-card-top { display:flex; justify-content:space-between; align-items:center; }
.mp-ticker { font-size:15px; font-weight:700; color:#0F172A; letter-spacing:.3px; }
.mp-company { font-size:11.5px; color:#94A3B8; margin:3px 0 9px; white-space:nowrap;
              overflow:hidden; text-overflow:ellipsis; }
.mp-row { display:flex; justify-content:space-between; align-items:baseline; }
.mp-price { font-size:15px; font-weight:600; color:#0F172A; }
.mp-change { font-size:13px; font-weight:600; }
.up { color:#0E9F6E; } .down { color:#E02424; } .flat { color:#94A3B8; }
.mp-foot { display:flex; justify-content:space-between; align-items:center; margin-top:9px;
           padding-top:9px; border-top:1px solid #F1F5F9; }
.mp-score { font-size:11.5px; color:#64748B; }
.mp-badge { font-size:11px; font-weight:600; padding:2px 9px; border-radius:999px; }
.mp-buy { background:#DEF7EC; color:#046C4E; }
.mp-hold { background:#FDF6B2; color:#8E4B10; }
.mp-avoid { background:#F1F3F5; color:#6B7280; }
.mp-risk { font-size:11px; padding:2px 9px; border-radius:999px; background:#F1F5F9; color:#475569; }

/* Tame metric + tab typography for consistency */
[data-testid="stMetricValue"] { font-size:20px; font-weight:600; }
[data-testid="stMetricLabel"] p { font-size:12px; color:#64748B; }
.stTabs [data-baseweb="tab-list"] { gap:2px; }
.stTabs [data-baseweb="tab"] { font-size:14px; padding:8px 16px; }
section[data-testid="stSidebar"] h2 { font-size:14px; text-transform:uppercase;
    letter-spacing:.4px; color:#64748B; }
</style>
""", unsafe_allow_html=True)


def money(v) -> str:
    # &#36; avoids Streamlit's markdown/LaTeX interpretation of a bare "$".
    return f"&#36;{v:,.2f}" if v is not None else "—"


# ------------------------------- providers -------------------------------
@st.cache_resource
def token_store() -> dict:
    return {}


def build_schwab_provider():
    from mp_terminal.schwab import (SchwabError, SchwabMarketData,
                                    build_authorize_url, exchange_code_for_token)
    key, secret = settings.schwab_app_key, settings.schwab_app_secret
    redirect = settings.schwab_redirect_uri
    if not key or not secret:
        st.error("Schwab selected but SCHWAB_APP_KEY / SCHWAB_APP_SECRET are missing from Secrets.")
        st.stop()
    store = token_store()
    code = st.query_params.get("code")
    if code and "token" not in store:
        try:
            store["token"] = exchange_code_for_token(key, secret, redirect, code)
            st.query_params.clear()
        except SchwabError as e:
            st.error(f"Schwab authorization failed: {e}")
            st.query_params.clear()
    if "token" not in store:
        with st.sidebar:
            st.link_button("🔗 Connect to Schwab", build_authorize_url(key, redirect),
                           width="stretch")
            st.caption("Paul logs in on Schwab to authorize — credentials never touch this app.")
        return None
    universe = None
    raw_uni = st.secrets.get("SCHWAB_UNIVERSE") if hasattr(st, "secrets") else None
    if raw_uni:
        universe = [s.strip().upper() for s in str(raw_uni).split(",") if s.strip()]
    return SchwabMarketData(key, secret, store["token"], universe=universe,
                            on_token_update=lambda t: store.__setitem__("token", t))


def build_finnhub_provider():
    from mp_terminal.finnhub_provider import FinnhubMarketData
    if not settings.finnhub_api_key:
        return None
    universe = None
    raw_uni = st.secrets.get("FINNHUB_UNIVERSE") if hasattr(st, "secrets") else None
    if raw_uni:
        universe = [s.strip().upper() for s in str(raw_uni).split(",") if s.strip()]
    return FinnhubMarketData(settings.finnhub_api_key, universe=universe)


# Bump when the Massive adapter changes, to force st.cache_resource to build a fresh provider
# on deploy (the cache otherwise survives script hot-reloads and can serve a stale object).
_MASSIVE_CACHE_VERSION = "v4"


@st.cache_resource
def _cached_massive_provider(api_key: str, price_min: float, price_max: float, version: str):
    from mp_terminal.massive_provider import MassiveMarketData
    return MassiveMarketData(api_key, price_min=price_min, price_max=price_max)


def build_massive_provider(price_min: float, price_max: float):
    if not settings.massive_api_key:
        return None
    # Cache key includes the range + version so the slider or a deploy rebuilds the provider.
    return _cached_massive_provider(settings.massive_api_key, price_min, price_max,
                                    _MASSIVE_CACHE_VERSION)


def compute_bands(pmin: float, pmax: float):
    """Split the selected range into readable sub-bands using canonical breakpoints."""
    breaks = [pmin] + [b for b in (3, 5, 10, 20, 50) if pmin < b < pmax] + [pmax]
    return [(f"&#36;{lo:g}–{hi:g}", lo, hi) for lo, hi in zip(breaks, breaks[1:])]


# ------------------------------- sidebar controls -------------------------------
_SOURCE_OPTIONS = ["Massive (whole market, EOD)", "Finnhub (live, curated)", "Schwab (your account)"]
_DEFAULT_INDEX = {"massive": 0, "finnhub": 1, "schwab": 2}.get(settings.data_source, 0)
with st.sidebar:
    st.header("Data Source")
    choice = st.radio("Choose a source", _SOURCE_OPTIONS, index=_DEFAULT_INDEX,
                       label_visibility="collapsed")

    st.header("Price Range")
    price_min, price_max = st.slider(
        "Price range", min_value=0.0, max_value=100.0,
        value=(float(settings.price_min), float(settings.price_max)), step=0.5,
        label_visibility="collapsed",
    )
    st.caption(f"Scanning **\\${price_min:g} – \\${price_max:g}**  ·  "
               f"priority \\${settings.priority_min:g}–{settings.priority_max:g}")
    if st.button("🔄 Refresh data", width="stretch"):
        st.cache_resource.clear()
        st.cache_data.clear()
        st.rerun()

# ------------------------------- resolve provider -------------------------------
live = False
if choice.startswith("Schwab"):
    provider = build_schwab_provider()
    live = provider is not None
elif choice.startswith("Massive"):
    provider = build_massive_provider(price_min, price_max)
    if provider is None:
        st.sidebar.warning("MASSIVE_API_KEY not set — showing mock data.")
        provider = MockMarketData()
    else:
        live = True
else:
    provider = build_finnhub_provider()
    if provider is None:
        st.sidebar.warning("FINNHUB_API_KEY not set — showing mock data.")
        provider = MockMarketData()
    else:
        live = True

with st.sidebar:
    st.divider()
    st.header("Status")
    if isinstance(provider, MockMarketData):
        st.warning("MOCK data (demo)")
    elif choice.startswith("Schwab") and live:
        st.success("Schwab — LIVE (your account)")
    elif choice.startswith("Schwab"):
        st.info("Schwab — awaiting authorization")
    elif choice.startswith("Massive"):
        st.success("Massive — whole market (EOD)")
    else:
        st.success("Finnhub — live (curated list)")
    st.caption("Order entry: **OFF** (read-only)" if not settings.enable_order_entry
               else "Order entry: **ON**")

# Capability flags used to gate/annotate features across the UI.
is_schwab_live = choice.startswith("Schwab") and live
has_history = hasattr(provider, "daily_bars")   # Massive + Mock; not Finnhub free
SCHWAB_ONLY = "🔒 Schwab (your account) is the only source that provides this."

with st.sidebar:
    with st.expander("ℹ️ What each source provides"):
        st.markdown(
            "- **Massive** — whole market, EOD prices + **historical indicators**\n"
            "- **Finnhub** — live prices, curated list (no free history for indicators)\n"
            "- **Schwab** — real-time, **bid/ask spread, 1m/5m intraday, premarket, "
            "watchlists & positions**\n\n"
            "Features that need Schwab are greyed out or hidden on the other sources.")


@st.cache_data(show_spinner=False, ttl=1800)
def cached_daily_bars(_provider, source_key: str, symbol: str) -> list[dict]:
    """Historical bars for one symbol, cached (the underscore tells Streamlit not to hash the
    provider object; source_key + symbol are the real cache key)."""
    try:
        return _provider.daily_bars(symbol)
    except Exception:
        return []


def load_quotes():
    if provider is None:
        return []
    try:
        return provider.all_quotes()
    except Exception as e:
        st.error(f"Failed to load quotes: {e}")
        return []


# ------------------------------- header -------------------------------
st.markdown(
    '<div class="mp-header"><div class="mp-logo">M&amp;P</div>'
    '<div><div class="mp-title">M&amp;P Trading Terminal</div>'
    '<div class="mp-subtitle">AI-powered short-term stock discovery</div></div></div>',
    unsafe_allow_html=True,
)

# Apply the sidebar price range on top of whatever the provider returned.
quotes = [q for q in load_quotes() if price_min <= q.price <= price_max]

if choice.startswith("Massive") and live and hasattr(provider, "as_of_dates"):
    dates = provider.as_of_dates
    if dates:
        st.info(f"📅 Whole-market data as of **{dates[0]}** (previous close {dates[1]}). "
                "Refreshes once per trading day — not intraday.")

if choice.startswith("Schwab") and not live:
    st.info("👈 Click **Connect to Schwab** in the sidebar to authorize your account's live data.")
    st.stop()

if not quotes:
    st.warning("No stocks in the selected price range. Widen the range in the sidebar.")
    if choice.startswith("Massive") and hasattr(provider, "diagnostics"):
        with st.expander("🔧 Massive data diagnostics (why no stocks loaded)", expanded=True):
            diag = provider.diagnostics
            if diag:
                for line in diag:
                    st.text(line)
            else:
                st.text("No diagnostics captured — the price band may simply have no matches. "
                        "Try widening the range.")
    st.stop()

# Score everything once (cheap — pure arithmetic, no API calls) so Recommendations and the
# Stock Detail default both use it. Whole-market data is heterogeneous (thousands of tickers),
# so score each quote defensively: a single pathological row must not crash the whole app.
scored = []
_score_errors = []
for _q in quotes:
    try:
        scored.append(scoring.score_quote(_q))
    except Exception as _e:  # noqa: BLE001 — surface, don't crash
        if len(_score_errors) < 3:
            _score_errors.append(f"{_q.symbol}: {type(_e).__name__}: {_e}")
if _score_errors:
    st.caption("⚠️ Some tickers were skipped while scoring: " + " | ".join(_score_errors))
if not scored:
    st.warning("Could not score any of the loaded stocks. See details above.")
    st.stop()
top_symbol = max(scored, key=lambda s: s.overall_score).quote.symbol

# ------------------------------- tabs -------------------------------
tab_reco, tab_gainers, tab_pillars, tab_premarket, tab_detail = st.tabs(
    ["⭐ Recommendations", "🚀 Top Gainers", "🏛 Pillars Scanner", "🌅 Premarket", "🔍 Stock Detail"]
)


def reco_card_html(s: ScoredStock) -> str:
    q = s.quote
    ch = q.daily_change_pct
    ch_cls = "up" if (ch or 0) > 0 else "down" if (ch or 0) < 0 else "flat"
    ch_txt = f"{ch:+.2f}%" if ch is not None else "—"
    badge = {"Buy": "mp-buy", "Hold": "mp-hold", "Avoid": "mp-avoid"}[s.recommendation.value]
    company = html.escape(q.company_name) if q.company_name else "&nbsp;"
    return (
        f'<div class="mp-card"><div class="mp-card-top">'
        f'<span class="mp-ticker">{html.escape(q.symbol)}</span>'
        f'<span class="mp-badge {badge}">{s.recommendation.value}</span></div>'
        f'<div class="mp-company">{company}</div>'
        f'<div class="mp-row"><span class="mp-price">{money(q.price)}</span>'
        f'<span class="mp-change {ch_cls}">{ch_txt}</span></div>'
        f'<div class="mp-foot"><span class="mp-score">Score {s.overall_score:.0f}/100</span>'
        f'<span class="mp-risk">{s.risk_level.value} risk</span></div></div>'
    )


with tab_reco:
    st.caption("Top 5 per price band, ranked by a real signal score (day strength, gap, range, "
               "volume). Open a stock in **Stock Detail** for the full multi-day indicator breakdown.")
    bands = compute_bands(price_min, price_max)
    cols = st.columns(len(bands))
    for col, (label, lo, hi) in zip(cols, bands):
        with col:
            st.markdown(f'<div class="mp-band-head">{label}</div>', unsafe_allow_html=True)
            band = sorted([s for s in scored if lo <= s.quote.price < hi],
                          key=lambda s: s.overall_score, reverse=True)[:5]
            if not band:
                st.markdown('<div class="mp-company">No matches</div>', unsafe_allow_html=True)
            else:
                st.markdown("".join(reco_card_html(s) for s in band), unsafe_allow_html=True)


_NUM_CONFIG = {
    "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
    "Change %": st.column_config.NumberColumn("Change %", format="%+.2f%%"),
    "Gap %": st.column_config.NumberColumn("Gap %", format="%+.2f%%"),
    "Range %": st.column_config.NumberColumn("Range %", format="%.2f%%"),
    "Volume": st.column_config.NumberColumn("Volume", format="%d"),
    "RVOL": st.column_config.NumberColumn("RVOL", format="%.2f"),
    "Float": st.column_config.NumberColumn("Float", format="%d"),
}

with tab_gainers:
    st.subheader("Top Gainers")
    st.caption("Ranked by daily % change. (True *past-1-hour* ranking needs intraday data — "
               f"{SCHWAB_ONLY.replace(chr(0x1F512)+' ', '')})")
    ranked = scanners.top_gainers(quotes)
    st.dataframe(pd.DataFrame([{
        "Symbol": q.symbol, "Company": q.company_name or "",
        "Price": round(q.price, 2), "Change %": round(q.daily_change_pct or 0, 2),
        "Gap %": round(q.gap_pct, 2) if q.gap_pct is not None else None,
        "Range %": round(q.range_pct, 2) if q.range_pct is not None else None,
        "Volume": q.volume, "RVOL": round(q.rvol, 2) if q.rvol else None, "Float": q.float_shares,
    } for q in ranked]), width="stretch", hide_index=True, column_config=_NUM_CONFIG)

with tab_pillars:
    st.subheader("Pillars Scanner")
    st.caption("Price in range · Day gain ≥10% · Float ≤20M · RVOL ≥5x  "
               "(news-catalyst pillar not available from current data sources)")
    rows = []
    for q in quotes:
        p = scanners.pillars_match(q)
        rows.append({
            "Symbol": q.symbol, "Company": q.company_name or "", "Price": round(q.price, 2),
            "In range": "✅" if p["price_band"] else "—",
            "Gain ≥10%": "✅" if p["gain_10pct"] else "—",
            "Float ≤20M": "✅" if p["low_float"] else "—",
            "RVOL ≥5x": "✅" if p["rvol_5x"] else "—",
            "All": "🟢" if scanners.is_all_pillars(q) else "",
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True,
                 column_config={"Price": _NUM_CONFIG["Price"]})

with tab_premarket:
    st.subheader("Premarket Scanner")
    if is_schwab_live:
        st.info("Extended-hours ranking wiring is pending; below is the gap-based proxy meanwhile.")
    else:
        st.warning("The full premarket scanner (premarket volume, VWAP, momentum) needs "
                   f"extended-hours data. {SCHWAB_ONLY}")
    st.caption("Available proxy: **Gap %** (today's open vs previous close) from the current source.")
    gap_rows = [{
        "Symbol": q.symbol, "Company": q.company_name or "", "Price": round(q.price, 2),
        "Gap %": round(q.gap_pct, 2) if q.gap_pct is not None else None,
        "Change %": round(q.daily_change_pct or 0, 2), "Volume": q.volume,
    } for q in quotes if q.gap_pct is not None]
    gap_rows.sort(key=lambda r: r["Gap %"], reverse=True)
    if gap_rows:
        st.dataframe(pd.DataFrame(gap_rows), width="stretch", hide_index=True,
                     column_config=_NUM_CONFIG)
    else:
        st.caption("No gap data available from this source.")


def ema_line(closes: list[float], period: int):
    s = indicators.ema_series(closes, period)
    return [None] * (len(closes) - len(s)) + s


with tab_detail:
    st.subheader("Stock Detail")
    labels_to_symbol = {
        (f"{q.symbol} — {q.company_name}" if q.company_name else q.symbol): q.symbol
        for q in quotes
    }
    ordered_labels = sorted(labels_to_symbol)
    # Default to the top-ranked recommendation rather than the first-alphabetical symbol
    # (which is often a thin, newly-listed ticker with no indicator history).
    default_label = next((lbl for lbl in ordered_labels
                          if labels_to_symbol[lbl] == top_symbol), ordered_labels[0])
    # Whether names are searchable depends on the source: Massive whole-market carries names
    # lazily (rate limits), so its search matches tickers only.
    names_searchable = any(q.company_name for q in quotes[:50])
    search_label = ("Search by ticker or company name" if names_searchable
                    else "Search by ticker (company names load when you open a stock)")
    chosen_label = st.selectbox(search_label, ordered_labels,
                                index=ordered_labels.index(default_label))
    symbol = labels_to_symbol[chosen_label]
    q = next(x for x in quotes if x.symbol == symbol)
    # Massive carries no name on whole-market quotes (rate limits); resolve it lazily here.
    if not q.company_name and hasattr(provider, "company_name"):
        q.company_name = provider.company_name(symbol)
    if q.company_name:
        st.markdown(f"**{html.escape(q.company_name)}**")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Price", f"${q.price:.2f}")
    c2.metric("Change", f"{q.daily_change_pct or 0:.2f}%")
    c3.metric("Gap", f"{q.gap_pct:+.2f}%" if q.gap_pct is not None else "—")
    c4.metric("Day range", f"{q.range_pct:.2f}%" if q.range_pct is not None else "—")
    if q.bid is not None and q.ask is not None:
        c5.metric("Spread", f"${q.ask - q.bid:.3f}")
    else:
        c5.metric("Spread", "🔒")
        c5.caption("Schwab only")

    # Full technical breakdown from historical bars (Massive / Schwab / Mock).
    if has_history:
        bars = cached_daily_bars(provider, choice, symbol)
        if len(bars) >= 30:
            an = indicators.analyze(bars)
            full = scoring.score_quote(q, analysis=an)

            st.markdown("##### Technical indicators")
            i1, i2, i3, i4 = st.columns(4)
            align = an["alignment"]
            align_color = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}[align]
            i1.metric("EMA trend", f"{align_color} {align.title()}")
            i2.metric("RSI (14)", f"{an['rsi']:.0f}" if an["rsi"] is not None else "—")
            i3.metric("MACD hist", f"{an['macd_hist']:+.3f}" if an["macd_hist"] is not None else "—")
            atr_pct = (an["atr"] / an["last_close"] * 100) if an["atr"] and an["last_close"] else None
            i4.metric("ATR %", f"{atr_pct:.1f}%" if atr_pct is not None else "—")
            j1, j2, j3, j4 = st.columns(4)
            j1.metric("EMA 9", f"${an['ema9']:.2f}" if an["ema9"] else "—")
            j2.metric("EMA 20", f"${an['ema20']:.2f}" if an["ema20"] else "—")
            j3.metric("EMA 200", f"${an['ema200']:.2f}" if an["ema200"] else "—")
            rvol = (q.volume / an["avg_vol_20"]) if an["avg_vol_20"] and q.volume else None
            j4.metric("RVOL (20d)", f"{rvol:.2f}" if rvol else "—")

            # Score breakdown
            st.markdown("##### AI score breakdown")
            brk = pd.DataFrame([
                {"Category": cat.title(), "Score": round(getattr(full.scores, cat), 1),
                 "Weight": f"{int(w*100)}%",
                 "Contribution": round(getattr(full.scores, cat) * w, 1)}
                for cat, w in scoring.WEIGHTS.items()
            ])
            bc1, bc2 = st.columns([2, 1])
            bc1.dataframe(brk, width="stretch", hide_index=True)
            bc2.metric("Overall", f"{full.overall_score:.0f}/100",
                       f"{full.recommendation.value} · {full.risk_level.value} risk")

            # Real candlestick chart with EMA overlays
            st.markdown("##### Price (daily, with EMAs)")
            recent = bars[-120:]
            closes_all = [b["c"] for b in bars]
            e20 = ema_line(closes_all, 20)[-len(recent):]
            e200 = ema_line(closes_all, 200)[-len(recent):]
            x = list(range(len(recent)))
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=x, open=[b["o"] for b in recent], high=[b["h"] for b in recent],
                low=[b["l"] for b in recent], close=[b["c"] for b in recent],
                increasing_line_color="#0E9F6E", decreasing_line_color="#E02424", name="Price"))
            fig.add_trace(go.Scatter(x=x, y=e20, line=dict(color="#2563EB", width=1), name="EMA 20"))
            fig.add_trace(go.Scatter(x=x, y=e200, line=dict(color="#C2410C", width=1), name="EMA 200"))
            fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0),
                              xaxis_rangeslider_visible=False, template="plotly_white",
                              legend=dict(orientation="h", y=1.02, x=0))
            st.plotly_chart(fig, width="stretch")

            tf = st.radio("Chart timeframe", ["Daily (EOD)", "5 min", "1 min"], horizontal=True,
                          index=0, disabled=not is_schwab_live)
            if not is_schwab_live:
                st.caption(f"Intraday 1m/5m charts: {SCHWAB_ONLY}")
        else:
            st.info("Not enough historical data to compute indicators for this symbol.")
    else:
        st.warning("Historical technical indicators (EMA/MACD/RSI/ATR) and the price chart need "
                   "**Massive** (whole-market, has free history) or **Schwab**. Finnhub's free tier "
                   "doesn't include historical candles.")

    st.divider()
    st.caption(f"Watchlists & positions: {SCHWAB_ONLY}")

    if choice.startswith("Finnhub") and hasattr(provider, "debug_symbol"):
        with st.expander("🔧 Debug Finnhub response"):
            debug = provider.debug_symbol(symbol)
            for lbl in ("quote", "candle", "metric"):
                info = debug.get(lbl, {})
                st.markdown(f"**{lbl}** — status `{info.get('status')}`")
                st.json(info.get("body"), expanded=False)
