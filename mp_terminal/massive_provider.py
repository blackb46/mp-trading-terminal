"""Massive (formerly Polygon.io) whole-market adapter — free, End-of-Day only.

Massive's free "Stocks Basic" plan does NOT include the real-time Full Market Snapshot
endpoint (confirmed via their docs — it's gated behind the $29/mo Starter plan). What IS
free is the "Daily Market Summary" endpoint, which returns OHLC + volume + VWAP for every
U.S. ticker on a specified past trading day, in a single call:

  GET /v2/aggs/grouped/locale/us/market/stocks/{date}

This adapter fetches the two most recent completed trading days (walking backward over
weekends/holidays), filters to the configured price band, and computes day-over-day change
and volume from real data — for literally every U.S. ticker, not a curated list. The
trade-off: this refreshes once per trading day (whenever Massive posts it, ~4am ET onward),
not intraday. There is no free path to intraday whole-market data anywhere, Massive included.

Free tier rate limit: 5 calls/minute. Two calls per full refresh is comfortably within that.
"""
from __future__ import annotations

import time
from datetime import date, timedelta

import httpx

from mp_terminal.models import Quote
from mp_terminal.providers import MarketDataProvider

BASE_URL = "https://api.massive.com"


class MassiveError(Exception):
    pass


class MassiveMarketData(MarketDataProvider):
    def __init__(self, api_key: str, price_min: float = 2.0, price_max: float = 20.0):
        self.api_key = api_key
        self.price_min = price_min
        self.price_max = price_max
        self._quotes_cache: list[Quote] | None = None
        self._dates_used: tuple[str, str] | None = None

    def _load_name_index(self, tickers_needed: set[str]) -> dict[str, str]:
        """Ticker -> company name, via the free '/v3/reference/tickers' endpoint.

        Paginates (up to a cap) until every ticker we actually need is resolved or the cap
        is hit, pacing calls to stay under the free tier's 5 calls/minute. This only runs
        once per cached provider instance (see streamlit_app.py's st.cache_resource wrapper),
        so the one-time cost doesn't repeat on every page load.
        """
        names: dict[str, str] = {}
        url = f"{BASE_URL}/v3/reference/tickers"
        params = {"apiKey": self.api_key, "market": "stocks", "active": "true",
                  "limit": 1000, "sort": "ticker", "order": "asc"}
        pages = 0
        while url and pages < 15 and len(names) < len(tickers_needed):
            try:
                r = httpx.get(url, params=params if pages == 0 else None, timeout=30)
            except Exception:
                break
            pages += 1
            if r.status_code != 200:
                break
            data = r.json()
            for row in data.get("results", []):
                t, n = row.get("ticker"), row.get("name")
                if t in tickers_needed and n:
                    names[t] = n
            url = data.get("next_url")
            if url:
                url = f"{url}&apiKey={self.api_key}"
                params = None
            if url and pages < 15 and len(names) < len(tickers_needed):
                time.sleep(1.5)  # stay well under 5 calls/minute
        return names

    def _fetch_grouped(self, day: date) -> dict[str, dict] | None:
        r = httpx.get(
            f"{BASE_URL}/v2/aggs/grouped/locale/us/market/stocks/{day.isoformat()}",
            params={"apiKey": self.api_key, "adjusted": "true"},
            timeout=30,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if not data.get("results"):
            return None
        return {row["T"]: row for row in data["results"] if "T" in row}

    def _two_most_recent_trading_days(self) -> list[tuple[str, dict[str, dict]]]:
        """Walk backward from yesterday until two days with real data are found.

        Respects the free tier's 5 calls/minute limit with a short pause between calls.
        """
        found: list[tuple[str, dict[str, dict]]] = []
        day = date.today() - timedelta(days=1)
        attempts = 0
        while len(found) < 2 and attempts < 10:
            bars = self._fetch_grouped(day)
            if bars:
                found.append((day.isoformat(), bars))
            day -= timedelta(days=1)
            attempts += 1
            if attempts < 10 and len(found) < 2:
                time.sleep(1.5)  # stay well under 5 calls/minute
        return found

    def _load(self) -> None:
        if self._quotes_cache is not None:
            return
        days = self._two_most_recent_trading_days()
        if len(days) < 2:
            self._quotes_cache = []
            return
        (latest_date, latest_bars), (prev_date, prev_bars) = days[0], days[1]
        self._dates_used = (latest_date, prev_date)

        # Filter to the price band first so the name lookup only needs to resolve the
        # (much smaller) set of tickers we're actually going to show.
        in_band = {}
        for ticker, bar in latest_bars.items():
            price = bar.get("c")
            if price is not None and self.price_min <= price <= self.price_max:
                in_band[ticker] = bar
        names = self._load_name_index(set(in_band.keys()))

        out = []
        for ticker, bar in in_band.items():
            prev_bar = prev_bars.get(ticker)
            raw_volume = bar.get("v")
            out.append(Quote(
                symbol=ticker,
                company_name=names.get(ticker),
                price=bar["c"],
                prev_close=prev_bar.get("c") if prev_bar else None,
                # Massive's grouped volume can come back as a float; Quote.volume is int.
                volume=int(round(raw_volume)) if raw_volume is not None else None,
                day_low=bar.get("l"),
                day_high=bar.get("h"),
                # avg_volume_30d / float_shares not available from this endpoint — RVOL will
                # be None for Massive-sourced quotes. See docs/MASSIVE_SETUP.md.
            ))
        self._quotes_cache = out

    def all_quotes(self) -> list[Quote]:
        self._load()
        return list(self._quotes_cache or [])

    def snapshot(self, symbol: str) -> Quote:
        for q in self.all_quotes():
            if q.symbol == symbol:
                return q
        raise KeyError(symbol)

    def universe(self) -> list[str]:
        return [q.symbol for q in self.all_quotes()]

    @property
    def as_of_dates(self) -> tuple[str, str] | None:
        """(latest_date, previous_date) actually used, for display in the UI."""
        self._load()
        return self._dates_used
