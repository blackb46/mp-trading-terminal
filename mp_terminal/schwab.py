"""Schwab market-data adapter (skeleton).

Fills in once Paul's app is approved and we have the App Key/Secret. Schwab uses OAuth 2.0 —
never a username/password. This module will:

  1. Run the OAuth 2.0 authorization-code flow (redirect to Schwab, receive `code` at the
     registered callback: https://mp-trading-terminal.streamlit.app).
  2. Exchange the code for access + refresh tokens; cache and auto-refresh them.
     (Access token ~30 min; refresh token ~7 days, then re-authorization is required.)
  3. Call the Market Data endpoints confirmed in the Schwab spec:
       GET /quotes            -> Quote (price, bid/ask, volume)
       GET /pricehistory      -> candlesticks for the detail chart (1m/5m)
       GET /movers/{index}    -> discovery feed for the scanners
       GET /instruments       -> fundamentals (float / shares outstanding)

Base URL: https://api.schwabapi.com/marketdata/v1
"""
from __future__ import annotations

from mp_terminal.models import Quote
from mp_terminal.providers import MarketDataProvider


class SchwabMarketData(MarketDataProvider):
    def __init__(self, app_key: str = "", app_secret: str = "", redirect_uri: str = ""):
        self.app_key = app_key
        self.app_secret = app_secret
        self.redirect_uri = redirect_uri
        # TODO: load cached token; if missing/expired, trigger OAuth flow.

    def snapshot(self, symbol: str) -> Quote:
        raise NotImplementedError(
            "Schwab adapter pending app approval + App Key/Secret. Use DATA_SOURCE=mock for now."
        )

    def universe(self) -> list[str]:
        # TODO: seed from a curated $2-20 symbol list and/or GET /movers.
        raise NotImplementedError(
            "Schwab adapter pending app approval + App Key/Secret. Use DATA_SOURCE=mock for now."
        )
