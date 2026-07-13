"""Schwab Trader API adapter — OAuth 2.0 + Market Data.

Schwab uses OAuth 2.0 (App Key/Secret), never a username/password. Flow for a hosted app:

  1. Send the user to the authorize URL (build_authorize_url).
  2. Schwab redirects back to the registered callback
     (https://mp-trading-terminal.streamlit.app) with `?code=...`.
  3. Exchange the code for tokens (exchange_code_for_token).
  4. Use the access token (~30 min) as a Bearer token; refresh with the refresh token
     (~7 days) via refresh_access_token. After ~7 days the user must re-authorize.

This module is Streamlit-agnostic: pure functions + a provider class. The Streamlit app
handles obtaining the `code` from the URL and persisting the token dict.

Endpoints (base https://api.schwabapi.com/marketdata/v1), confirmed from the Schwab spec:
  GET /quotes            GET /pricehistory      GET /movers/{index}     GET /instruments
"""
from __future__ import annotations

import base64
import time
from typing import Callable, Optional
from urllib.parse import urlencode

import httpx

from mp_terminal.models import Quote
from mp_terminal.providers import MarketDataProvider

AUTHORIZE_URL = "https://api.schwabapi.com/v1/oauth/authorize"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
MARKETDATA_BASE = "https://api.schwabapi.com/marketdata/v1"

# Default starter universe (a configurable list of tickers; the $2-20 price band is applied
# on top). Schwab has no whole-market screener, so scanning runs over this list. Edit via the
# SCHWAB_UNIVERSE secret (comma-separated) or replace with an imported CSV later.
DEFAULT_UNIVERSE = [
    "F", "SOFI", "PLUG", "NIO", "SNAP", "RIG", "AMCR", "KGC", "HBAN", "BTG",
    "GOLD", "VALE", "NOK", "GRAB", "LU", "CLSK", "MARA", "RIOT", "IQ", "WBD",
]


class SchwabError(Exception):
    pass


def build_authorize_url(app_key: str, redirect_uri: str) -> str:
    q = urlencode({"client_id": app_key, "redirect_uri": redirect_uri, "response_type": "code"})
    return f"{AUTHORIZE_URL}?{q}"


def _basic_auth(app_key: str, app_secret: str) -> str:
    return "Basic " + base64.b64encode(f"{app_key}:{app_secret}".encode()).decode()


def _stamp_expiry(tok: dict) -> dict:
    # Store an absolute expiry with a 60s safety margin.
    tok["expires_at"] = time.time() + int(tok.get("expires_in", 1800)) - 60
    return tok


def exchange_code_for_token(app_key: str, app_secret: str, redirect_uri: str, code: str) -> dict:
    headers = {
        "Authorization": _basic_auth(app_key, app_secret),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri}
    r = httpx.post(TOKEN_URL, headers=headers, data=data, timeout=30)
    if r.status_code != 200:
        raise SchwabError(f"Token exchange failed ({r.status_code}): {r.text}")
    return _stamp_expiry(r.json())


def refresh_access_token(app_key: str, app_secret: str, refresh_token: str) -> dict:
    headers = {
        "Authorization": _basic_auth(app_key, app_secret),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    r = httpx.post(TOKEN_URL, headers=headers, data=data, timeout=30)
    if r.status_code != 200:
        raise SchwabError(f"Token refresh failed ({r.status_code}): {r.text}")
    tok = _stamp_expiry(r.json())
    # Schwab returns a fresh refresh_token too; keep it if present.
    if "refresh_token" not in tok:
        tok["refresh_token"] = refresh_token
    return tok


class SchwabMarketData(MarketDataProvider):
    """Market-data provider backed by the Schwab Trader API.

    `token` is the dict returned by exchange/refresh. `on_token_update` (optional) is called
    whenever the token is refreshed so the caller can persist it.
    """

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        token: dict,
        universe: Optional[list[str]] = None,
        on_token_update: Optional[Callable[[dict], None]] = None,
    ):
        self.app_key = app_key
        self.app_secret = app_secret
        self.token = token
        self._universe = universe or DEFAULT_UNIVERSE
        self.on_token_update = on_token_update

    # --- auth helpers ---
    def _valid_access_token(self) -> str:
        if time.time() >= self.token.get("expires_at", 0):
            self.token = refresh_access_token(
                self.app_key, self.app_secret, self.token["refresh_token"]
            )
            if self.on_token_update:
                self.on_token_update(self.token)
        return self.token["access_token"]

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._valid_access_token()}", "Accept": "application/json"}

    # --- market data ---
    def snapshot(self, symbol: str) -> Quote:
        r = httpx.get(
            f"{MARKETDATA_BASE}/quotes",
            headers=self._headers(),
            params={"symbols": symbol, "indicative": "false"},
            timeout=30,
        )
        if r.status_code != 200:
            raise SchwabError(f"Quote fetch failed for {symbol} ({r.status_code}): {r.text}")
        return self._parse_quote(symbol, r.json().get(symbol, {}))

    def all_quotes(self) -> list[Quote]:
        symbols = ",".join(self._universe)
        r = httpx.get(
            f"{MARKETDATA_BASE}/quotes",
            headers=self._headers(),
            params={"symbols": symbols, "indicative": "false"},
            timeout=30,
        )
        if r.status_code != 200:
            raise SchwabError(f"Bulk quote fetch failed ({r.status_code}): {r.text}")
        payload = r.json()
        out = []
        for sym in self._universe:
            if sym in payload:
                try:
                    out.append(self._parse_quote(sym, payload[sym]))
                except Exception:
                    continue
        return out

    def universe(self) -> list[str]:
        return list(self._universe)

    @staticmethod
    def _parse_quote(symbol: str, node: dict) -> Quote:
        """Map a Schwab quote node to our Quote model, defensively.

        Schwab returns {symbol: {"quote": {...}, "fundamental": {...}, "reference": {...}}}.
        Field names per the Schwab Market Data schema; some (e.g. true float) aren't provided
        and are left None. Verify/adjust against a live response during the connect test.
        """
        q = node.get("quote", {}) or {}
        f = node.get("fundamental", {}) or {}
        return Quote(
            symbol=symbol,
            price=q.get("lastPrice") or q.get("mark") or 0.0,
            bid=q.get("bidPrice"),
            ask=q.get("askPrice"),
            prev_close=q.get("closePrice"),
            volume=q.get("totalVolume"),
            # Schwab exposes avg 10-day / 1-year volume, not 30-day — 10-day used as the RVOL base.
            avg_volume_30d=int(f["avg10DaysVolume"]) if f.get("avg10DaysVolume") else None,
            # True float isn't in the quote payload; sharesOutstanding is the closest proxy.
            float_shares=int(f["sharesOutstanding"]) if f.get("sharesOutstanding") else None,
            day_low=q.get("lowPrice"),
            day_high=q.get("highPrice"),
        )
