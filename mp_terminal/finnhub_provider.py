"""Finnhub market-data adapter — the DEFAULT data source.

Finnhub is a pure data vendor: signup is email/password only, an API key is issued
immediately, and there is no brokerage relationship, no KYC, and no personal account
involved. This is why it's the default, versus Schwab (optional, Paul's account, see
schwab.py) which requires his own OAuth login for real-time data.

Free tier: real-time quotes, 60 API calls/minute. Price/change/high/low come from /quote,
which is available on the free tier. Volume (via /stock/candle) and fundamentals (via
/stock/metric) are BEST-EFFORT enrichment — Finnhub gates some of these behind paid plans,
and a 403 there must not take down the quote itself. Any enrichment call that fails is
swallowed and the corresponding field is left None rather than dropping the whole symbol.

The Streamlit app additionally wraps all_quotes() in st.cache_data(ttl=...) so repeated
reruns (e.g. clicking a different tab) don't burn extra API calls within the refresh window.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx

from mp_terminal.models import Quote
from mp_terminal.providers import DEFAULT_UNIVERSE, MarketDataProvider

BASE_URL = "https://finnhub.io/api/v1"


class FinnhubError(Exception):
    pass


def _today_start_epoch() -> int:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(start.timestamp())


class FinnhubMarketData(MarketDataProvider):
    def __init__(self, api_key: str, universe: list[str] | None = None):
        self.api_key = api_key
        self._universe = universe or DEFAULT_UNIVERSE
        self._financials_cache: dict[str, dict] = {}
        self._name_cache: dict[str, str | None] = {}

    def _get(self, path: str, **params) -> dict:
        params["token"] = self.api_key
        r = httpx.get(f"{BASE_URL}{path}", params=params, timeout=30)
        if r.status_code != 200:
            raise FinnhubError(f"Finnhub request failed ({r.status_code}): {r.text}")
        return r.json()

    def _get_safe(self, path: str, **params) -> dict | None:
        """Like _get, but swallows failures — for optional enrichment data only.

        Finnhub's free tier doesn't include every endpoint (e.g. stock candles can be
        plan-gated); a failure here must never take down the underlying quote.
        """
        try:
            return self._get(path, **params)
        except Exception:
            return None

    def debug_symbol(self, symbol: str) -> dict:
        """Raw request/response info for /quote, /stock/candle, /stock/metric — for
        diagnosing which endpoint(s) the current API key/plan can't access. Never raises.
        """
        out: dict = {}
        for label, path, params in [
            ("quote", "/quote", {"symbol": symbol}),
            ("candle", "/stock/candle", {
                "symbol": symbol, "resolution": "D",
                "from": _today_start_epoch(), "to": int(time.time()),
            }),
            ("metric", "/stock/metric", {"symbol": symbol, "metric": "all"}),
        ]:
            try:
                params_with_token = dict(params, token=self.api_key)
                r = httpx.get(f"{BASE_URL}{path}", params=params_with_token, timeout=30)
                out[label] = {"status": r.status_code, "body": r.json() if r.status_code == 200 else r.text}
            except Exception as e:
                out[label] = {"status": "exception", "body": str(e)}
        return out

    def _today_volume(self, symbol: str) -> int | None:
        data = self._get_safe(
            "/stock/candle", symbol=symbol, resolution="D",
            **{"from": _today_start_epoch(), "to": int(time.time())},
        )
        if not data or data.get("s") != "ok" or not data.get("v"):
            return None
        return int(data["v"][-1])

    def _financials(self, symbol: str) -> dict:
        if symbol not in self._financials_cache:
            data = self._get_safe("/stock/metric", symbol=symbol, metric="all")
            self._financials_cache[symbol] = (data or {}).get("metric", {}) or {}
        return self._financials_cache[symbol]

    def _company_name(self, symbol: str) -> str | None:
        if symbol not in self._name_cache:
            data = self._get_safe("/stock/profile2", symbol=symbol)
            self._name_cache[symbol] = (data or {}).get("name")
        return self._name_cache[symbol]

    def snapshot(self, symbol: str) -> Quote:
        q = self._get("/quote", symbol=symbol)  # required — let failures propagate
        return self._build_quote(symbol, q)

    def all_quotes(self) -> list[Quote]:
        out = []
        for sym in self._universe:
            try:
                out.append(self.snapshot(sym))
            except FinnhubError:
                continue
        return out

    def universe(self) -> list[str]:
        return list(self._universe)

    def _build_quote(self, symbol: str, q: dict) -> Quote:
        f = self._financials(symbol)
        # Finnhub reports these two metrics in millions of shares.
        avg_vol_10d = f.get("10DayAverageTradingVolume")
        shares_out = f.get("shareOutstanding")
        return Quote(
            symbol=symbol,
            company_name=self._company_name(symbol),
            price=q.get("c") or 0.0,
            prev_close=q.get("pc"),
            volume=self._today_volume(symbol),
            avg_volume_30d=int(avg_vol_10d * 1_000_000) if avg_vol_10d else None,
            float_shares=int(shares_out * 1_000_000) if shares_out else None,
            day_low=q.get("l"),
            day_high=q.get("h"),
        )
