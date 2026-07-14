"""Data providers.

Two real providers: Finnhub (mp_terminal/finnhub_provider.py, default — free, no KYC, no
personal account) and Schwab (mp_terminal/schwab.py, optional — Paul's account, real-time,
requires his own OAuth login). Plus a Mock provider so the dashboard runs with no keys at all.
The Streamlit app lets the user toggle between Finnhub and Schwab in the sidebar.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from mp_terminal.models import Quote

# Default starter universe (a configurable list of tickers; the $2-20 price band is applied
# on top). Neither Finnhub's free tier nor Schwab has a whole-market screener, so scanning
# runs over this list. Replace with an imported CSV / expanded list later.
DEFAULT_UNIVERSE = [
    "F", "SOFI", "PLUG", "NIO", "SNAP", "RIG", "AMCR", "KGC", "HBAN", "BTG",
    "GOLD", "VALE", "NOK", "GRAB", "LU", "CLSK", "MARA", "RIOT", "IQ", "WBD",
]


class MarketDataProvider(ABC):
    @abstractmethod
    def snapshot(self, symbol: str) -> Quote:
        """Current quote for a symbol."""

    @abstractmethod
    def universe(self) -> list[str]:
        """Symbols in the configured universe (later filtered by price band)."""


# Sample data covering the $2-20 band, including a couple that pass all 4 pillars.
_SAMPLE = [
    Quote(symbol="ABCD", price=3.42, prev_close=3.01, bid=3.41, ask=3.43,
          volume=18_000_000, avg_volume_30d=3_000_000, float_shares=12_000_000,
          day_low=3.05, day_high=3.55, avg_day_high=3.40, avg_day_low=3.00, avg_5d_low=2.95),
    Quote(symbol="EFGH", price=4.78, prev_close=4.30, bid=4.77, ask=4.79,
          volume=9_500_000, avg_volume_30d=1_500_000, float_shares=8_000_000,
          day_low=4.35, day_high=4.90, avg_day_high=4.70, avg_day_low=4.25, avg_5d_low=4.10),
    Quote(symbol="WXYZ", price=12.10, prev_close=11.95, bid=12.08, ask=12.12,
          volume=2_200_000, avg_volume_30d=2_000_000, float_shares=45_000_000,
          day_low=11.90, day_high=12.30, avg_day_high=12.15, avg_day_low=11.80, avg_5d_low=11.50),
    Quote(symbol="MNOP", price=6.55, prev_close=6.40, bid=6.54, ask=6.56,
          volume=4_100_000, avg_volume_30d=2_800_000, float_shares=30_000_000,
          day_low=6.30, day_high=6.75, avg_day_high=6.50, avg_day_low=6.20, avg_5d_low=6.05),
]


class MockMarketData(MarketDataProvider):
    """Deterministic sample data so the app runs end-to-end with no keys."""

    def snapshot(self, symbol: str) -> Quote:
        for q in _SAMPLE:
            if q.symbol == symbol:
                return q
        raise KeyError(symbol)

    def universe(self) -> list[str]:
        return [q.symbol for q in _SAMPLE]

    def all_quotes(self) -> list[Quote]:
        return list(_SAMPLE)


# Note: the Schwab provider needs an OAuth token obtained at runtime, so it is constructed in
# streamlit_app.py (which manages the login flow), not here. This factory only covers mock.
def get_mock_provider() -> MarketDataProvider:
    return MockMarketData()
