"""Scanner engine (Schwab-only scope).

Filters a configured symbol universe against each scanner's criteria. In production these run
against Schwab quotes/price-history; here they evaluate Quote snapshots so the logic is testable.
"""
from __future__ import annotations

from mp_terminal.models import Quote

PRICE_MIN = 2.00
PRICE_MAX = 20.00


def in_universe(q: Quote, price_min: float = PRICE_MIN, price_max: float = PRICE_MAX) -> bool:
    return price_min <= q.price <= price_max


def pillars_match(q: Quote) -> dict:
    """Pillars scanner: price $2-20, gain >=10%, float <=20M, RVOL >=5x.

    The original 5th pillar ("recent news catalyst") is cut in the Schwab-only scope —
    Schwab provides no news feed (see docs/SCOPE.md). Returns which pillars passed so the UI
    can flag partial matches.
    """
    change = q.daily_change_pct
    rvol = q.rvol
    return {
        "price_band": in_universe(q),
        "gain_10pct": change is not None and change >= 10,
        "low_float": q.float_shares is not None and q.float_shares <= 20_000_000,
        "rvol_5x": rvol is not None and rvol >= 5,
    }


def is_all_pillars(q: Quote) -> bool:
    return all(pillars_match(q).values())


def top_gainers(quotes: list[Quote]) -> list[Quote]:
    """Rank by daily % change. (True 1-hour ranking needs intraday history — TODO via Schwab.)"""
    ranked = [q for q in quotes if in_universe(q) and q.daily_change_pct is not None]
    return sorted(ranked, key=lambda q: q.daily_change_pct, reverse=True)


# TODO: Premarket scanner — limited to Schwab extended-hours fields (see docs/SCOPE.md).
